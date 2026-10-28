"""Where is data going? Extract and normalise destinations: e-mail addresses, URL hosts and file paths. Pure functions
(invariant 1).

Used by R1 (is the destination inside the slip?), R2 (is it an internal destination?), R3 (did the recipient come only from
untrusted content?) and R7 (did the officer name this destination?). This is value matching on destinations, not general
provenance: an address the model assembles from fragments is not recognised (declared limit, ARCHITECTURE.md 5b).

A destination is a KEY, a normalised string whose form says what it is:
  "sales@shakti.example"      an e-mail address
  "host:collector.example"    the host of a URL (port and path ignored: the slip allows a host, not a page)
  "path:/reports/out.txt"     a file path inside the sandbox, normalised, never containing ".."
Anything ambiguous is returned as JUNK and refused by R1, never guessed at: a URL that two parsers read differently is
how data is smuggled out ("https://allowed.example\\@evil.example/").
"""

from __future__ import annotations

import posixpath
import re
from typing import Any
from urllib.parse import urlsplit

from .matcher import normalise

_EMAIL = re.compile(r"[a-z0-9._%+\-]+@[a-z0-9\-]+(?:\.[a-z0-9\-]+)+")
_URL_HOST = re.compile(r"https?://([a-z0-9\-]+(?:\.[a-z0-9\-]+)+)")  # for scanning free text, where a miss is harmless
_STRICT_NETLOC = re.compile(r"[a-z0-9](?:[a-z0-9\-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9\-]*[a-z0-9])?)*(?::\d{1,5})?")


def extract_destinations(text: str) -> set[str]:
    """Every e-mail address and URL host in `text`, after decoding URL/HTML escapes and Unicode folding."""
    t = normalise(text)
    return set(_EMAIL.findall(t)) | {f"host:{h}" for h in _URL_HOST.findall(t)}


def domain_of(address: str) -> str:
    return address.rsplit("@", 1)[-1] if "@" in address else address.removeprefix("host:")


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
    if key.startswith("path:"):
        return any(w.startswith("path:") and (key == w.rstrip("/") or key.startswith(w.rstrip("/") + "/")) for w in wanted)
    if "@" in key:
        return key in wanted or key.rsplit("@", 1)[-1] in wanted
    host = key.removeprefix("host:")
    return host in wanted or f"host:{host}" in wanted
