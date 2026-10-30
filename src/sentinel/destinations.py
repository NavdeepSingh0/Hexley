"""Where is data going? Extract and normalise destinations: e-mail addresses, URL hosts and file paths. Pure functions
(invariant 1).

Used by R1 (is the destination inside the slip?), R2 (is it an internal destination?), R3 (did the recipient come only from
untrusted content?) and R7 (did the officer name this destination?). This is value matching on destinations, not general
provenance: an address the model assembles from fragments is not recognised (declared limit, ARCHITECTURE.md 5b).

A destination is a KEY, a normalised string whose form says what it is:
  "sales@shakti.example"      an e-mail address
  "host:collector.example"    the host of a URL (port and path ignored: the slip allows a host, not a page)
  "path:/reports/out.txt"     a file path inside the sandbox, normalised, never containing ".."
  "repo:acme/website"         a code repository (owner/name), from a connector such as GitHub (plan F2)
  "channel:c0123abc"          a chat channel, by id or name without '#'
  "page:1a2b3c..."            a document page or database, by id with the dashes removed
Anything ambiguous is returned as JUNK and refused by R1, never guessed at: a URL that two parsers read differently is
how data is smuggled out ("https://allowed.example\\@evil.example/").
"""

from __future__ import annotations

import json
import posixpath
import re
from typing import Any
from urllib.parse import urlsplit

from .matcher import normalise

_EMAIL = re.compile(r"[a-z0-9._%+\-]+@[a-z0-9\-]+(?:\.[a-z0-9\-]+)+")
_URL_HOST = re.compile(r"https?://([a-z0-9\-]+(?:\.[a-z0-9\-]+)+)")  # for scanning free text, where a miss is harmless
_STRICT_NETLOC = re.compile(r"[a-z0-9](?:[a-z0-9\-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9\-]*[a-z0-9])?)*(?::\d{1,5})?")
_REPO_PART = re.compile(r"[a-z0-9](?:[a-z0-9._\-]{0,99})")
_CHANNEL = re.compile(r"[a-z0-9][a-z0-9._\-]{0,79}")
_PAGE = re.compile(r"[a-z0-9]{8,64}")
# Kinds whose key is built from one or more arguments and compared exactly (no domain or prefix logic).
NAMED_KINDS = ("repo", "channel", "page")


def extract_destinations(text: str) -> set[str]:
    """Every e-mail address and URL host in `text`, after decoding URL/HTML escapes and Unicode folding."""
    t = normalise(text)
    return set(_EMAIL.findall(t)) | {f"host:{h}" for h in _URL_HOST.findall(t)}


def domain_of(address: str) -> str:
    if address.split(":", 1)[0] in NAMED_KINDS:
        return address
    return address.rsplit("@", 1)[-1] if "@" in address else address.removeprefix("host:")


def _get(args: dict[str, Any], path: str) -> Any:
    """An argument by dotted path (`parent.page_id`); None when any step is missing. A step may be an object written as a
    JSON string (Notion's server accepts `parent` either way), and it is read the way the server would read it."""
    value: Any = args
    for part in path.split("."):
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except ValueError:
                return None
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value


def _ambiguous_target(args: dict[str, Any], path: str) -> bool:
    """`{"page_id": <allowed>, "database_id": <elsewhere>}`: the object names two targets, the check would read one and the
    service might use the other. Such a call is refused rather than guessed at."""
    head, dot, leaf = path.rpartition(".")
    holder = _get(args, head) if dot else None
    if isinstance(holder, str):
        holder = json.loads(holder)  # it parsed already: the target was read from it
    return isinstance(holder, dict) and any(k != leaf and k.endswith("_id") and v for k, v in holder.items())


def named_key(kind: str, values: list[Any]) -> str | None:
    """The key for a repository, channel or page, or None when the values do not make a plain one. A repository needs
    owner and name (two arguments, or one "owner/name"); anything with odd characters is refused, not cleaned."""
    if not values or any(not isinstance(v, (str, int)) or isinstance(v, bool) for v in values):
        return None
    parts = [normalise(str(v)).strip() for v in values]
    if kind == "repo":
        if len(parts) == 1 and parts[0].count("/") == 1:
            parts = parts[0].split("/")
        if len(parts) != 2 or not all(_REPO_PART.fullmatch(p) for p in parts) or ".." in parts[1]:
            return None
        return f"repo:{parts[0]}/{parts[1].removesuffix('.git')}"
    if len(parts) != 1:
        return None
    if kind == "channel":
        name = parts[0].removeprefix("#")
        return f"channel:{name}" if _CHANNEL.fullmatch(name) else None
    page = parts[0].replace("-", "")
    return f"page:{page}" if _PAGE.fullmatch(page) else None


def destination_keys(args: dict[str, Any], destination_args: list[str], kind: str) -> tuple[list[str], list[str]]:
    """The destination keys of a call, from the tool's registry entry: keys plus the values that made none (junk, refused
    by R1). For a repository, channel or page the listed arguments together make ONE key, and a missing one is junk: an
    outbound call must say where it goes."""
    if kind in NAMED_KINDS:
        values = [_get(args, a) for a in destination_args]
        key = named_key(kind, values) if all(v is not None for v in values) else None
        shown = "/".join(str(v) for v in values if v is not None) or "(no destination given)"
        if key and any(_ambiguous_target(args, a) for a in destination_args):
            return [], [f"{shown} (the call names more than one target)"]
        return ([key], []) if key else ([], [shown])
    values = [v for a in destination_args if (v := _get(args, a)) is not None]
    if destination_args and not values:
        return [], ["(no destination given)"]  # Gmail's send_message and reply run without `to`: where it goes would go unchecked
    return keys_in(values, kind)


def recipients_in(value: Any) -> tuple[list[str], list[str]]:
    """Addresses in a destination argument (a string, or a list of strings), plus any strings that held none.

    `Shakti Sales <Sales@Shakti.example>` yields `sales@shakti.example`. A string with no address in it
    ("vendor email") is returned in the second list so R1 can refuse it."""
    if isinstance(value, (list, tuple)):
        emails: list[str] = []
        junk: list[str] = []
        for v in value:
            e, j = recipients_in(v)
            emails += e
            junk += j
        return emails, junk
    text = str(value)
    found = list(dict.fromkeys(_EMAIL.findall(normalise(text))))
    return (found, []) if found else ([], [text])


def _url_key(text: str) -> str | None:
    """The host key of ONE url string, or None when it is anything but a plain http(s) URL with a plain host."""
    raw = text.strip()
    if not raw or any(ord(c) < 33 or ord(c) == 127 for c in raw) or "\\" in raw:
        return None  # whitespace, control characters or backslashes: parsers disagree about these
    try:
        parts = urlsplit(normalise(raw))
    except ValueError:
        return None
    if parts.scheme not in ("http", "https") or "@" in parts.netloc or not _STRICT_NETLOC.fullmatch(parts.netloc):
        return None  # userinfo, odd ports, brackets, unicode hosts: refused rather than interpreted
    host = parts.netloc.split(":")[0].rstrip(".")
    return f"host:{host}" if "." in host else None


def _path_key(text: str) -> str | None:
    """A normalised absolute sandbox path, or None if it tries to climb out ("..") or holds odd characters."""
    raw = text.strip().replace("\\", "/")
    if not raw or "\x00" in raw or any(ord(c) < 32 for c in raw):
        return None
    if ".." in [p for p in raw.split("/") if p]:
        return None  # a traversal attempt is refused outright, not resolved
    return "path:" + posixpath.normpath("/" + raw.lstrip("/"))


def keys_in(value: Any, kind: str = "email") -> tuple[list[str], list[str]]:
    """The destination keys in a destination argument, plus the strings that held none (junk, refused by R1)."""
    if kind == "email":
        return recipients_in(value)
    if isinstance(value, (list, tuple)):
        keys: list[str] = []
        junk: list[str] = []
        for v in value:
            k, j = keys_in(v, kind)
            keys += k
            junk += j
        return keys, junk
    text = str(value)
    key = _url_key(text) if kind == "url" else _path_key(text)
    return ([key], []) if key else ([], [text])


def allowed(key: str, entries: list[str]) -> bool:
    """Is this destination covered by a slip list? Entries are written by the officer:
    a domain ("shakti.example") covers its e-mail addresses and its URL host (exactly, subdomains are NOT included);
    a full address ("boss@corp.example") covers only that address; "path:/prefix" covers that folder and below."""
    wanted = {e.strip().lower() for e in entries if e and e.strip()}
    if key.split(":", 1)[0] in NAMED_KINDS:
        if key.startswith("page:"):
            wanted = {w.replace("-", "") for w in wanted}
        return key in wanted  # a repository, channel or page is allowed by name only, never by a pattern
    if key.startswith("path:"):
        return any(w.startswith("path:") and (key == w.rstrip("/") or key.startswith(w.rstrip("/") + "/")) for w in wanted)
    if "@" in key:
        return key in wanted or key.rsplit("@", 1)[-1] in wanted
    host = key.removeprefix("host:")
    return host in wanted or f"host:{host}" in wanted
