"""What an action does, read from its arguments rather than from the tool's name (plan Q4, PRODUCT_AUDIT §7 P3).

Policies keyed on tool names are bypassed by switching tools: Antigravity's agent read `.env` with `cat` after the
`read_file` route was guarded. So a path is a path whichever tool carries it, a SQL statement is read or written whichever
tool runs it, and a shell command is tokenised before anyone decides about it.

Pure functions only: no I/O, no clock, no model (invariant 1). Recognisers are deliberately small and conservative;
each one has tests with true and false examples. Anything a recogniser cannot parse is reported as such, never guessed.
"""

from __future__ import annotations

import posixpath
import re
import shlex
from dataclasses import dataclass
from typing import Any

# ---- protected paths ---------------------------------------------------------------------------------------------------
# Agent and IDE configuration: writing here installs a new tool, a hook or a server that runs code (CurXecute, MCPoison,
# Kiro, Shai-Hulud hooks). Secrets: reading here reads credentials (Antigravity, s1ngularity).
_CONFIG = re.compile(r"(?:^|/)(?:\.cursor|\.claude|\.vscode|\.kiro|\.windsurf|\.idea|\.continue|\.gemini|\.codeium)(?:/|$)|"
                     r"(?:^|/)(?:mcp\.json|claude_desktop_config\.json|settings\.json|[^/]*\.code-workspace)$|"
                     r"(?:^|/)\.git/hooks(?:/|$)|(?:^|/)\.github/workflows(?:/|$)|(?:^|/)\.(?:bashrc|zshrc|profile|bash_profile)$")
_SECRET = re.compile(r"(?:^|/)\.env(?:\.[^/]*)?$|(?:^|/)\.ssh(?:/|$)|(?:^|/)id_(?:rsa|dsa|ecdsa|ed25519)(?:\.pub)?$|"
                     r"\.(?:pem|key|p12|pfx|keystore|jks)$|(?:^|/)\.aws/credentials$|(?:^|/)\.netrc$|(?:^|/)\.npmrc$|"
                     r"(?:^|/)\.pypirc$|(?:^|/)credentials(?:\.json)?$|(?:^|/)secrets?\.(?:ya?ml|json|toml)$|(?:^|/)\.kube/config$")
_PATH_ARG = re.compile(r"(?i)(?:^|_)(?:path|file|filename|dir|directory|folder|dest|destination|target)(?:$|_)")


def norm_path(p: str) -> str:
    q = p.replace("\\", "/").strip().strip("'\"")
    q = re.sub(r"^~(?=/|$)", "home", q)
    return posixpath.normpath(q).lower() if q else ""


def path_class(p: str) -> str | None:
    """'config' (agent/IDE configuration: never written), 'secret' (credential files), or None."""
    n = norm_path(p)
    if not n:
        return None
    if _CONFIG.search(n):
        return "config"
    if _SECRET.search(n):
        return "secret"
    return None


def paths_in_args(args: dict[str, Any]) -> list[tuple[str, str]]:
    """(argument name, value) for every argument whose name says it is a path."""
    out = []
    for k, v in (args or {}).items():
        if isinstance(v, str) and _PATH_ARG.search(k):
            out.append((k, v))
    return out


# ---- SQL --------------------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class SqlEffect:
    kind: str  # read | write | ddl | unknown
    tables: tuple[str, ...]
    destructive: bool
    note: str = ""


_SQL_TABLE = re.compile(r"\b(?:from|join|into|update|table|truncate)\s+(?:if\s+(?:not\s+)?exists\s+)?([a-z_][a-z0-9_.\"`\[\]]*)", re.I)


def _strip_sql(sql: str) -> str:
    s = re.sub(r"--[^\n]*", " ", sql)
    s = re.sub(r"/\*.*?\*/", " ", s, flags=re.S)
    s = re.sub(r"'(?:[^']|'')*'", "''", s)  # string literals cannot hide keywords
    return " ".join(s.split())


def sql_effect(sql: str) -> SqlEffect:
    s = _strip_sql(sql or "")
    if not s:
        return SqlEffect("unknown", (), False, "empty statement")
    if ";" in s.rstrip(";"):
        return SqlEffect("unknown", (), True, "more than one statement")
    first = s.split()[0].lower()
    tables = tuple(dict.fromkeys(t.strip('"`[]').lower() for t in _SQL_TABLE.findall(s)))
    low = s.lower()
    if first in ("select", "with", "explain", "show", "describe", "pragma") and not re.search(
            r"\b(?:insert|update|delete|drop|alter|create|truncate|replace|grant|revoke)\b", low):
        return SqlEffect("read", tables, False)
    if first in ("drop", "truncate", "alter"):
        return SqlEffect("ddl", tables, True, f"{first.upper()} cannot be undone")
    if first in ("create", "grant", "revoke"):
        return SqlEffect("ddl", tables, False)
    if first in ("delete", "update"):
        no_where = not re.search(r"\bwhere\b", low)
        return SqlEffect("write", tables, no_where, f"{first.upper()} without WHERE changes every row" if no_where else "")
    if first in ("insert", "replace", "merge", "upsert"):
        return SqlEffect("write", tables, False)
    return SqlEffect("unknown", tables, True, "statement not recognised")


# ---- shell ------------------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class ShellEffect:
    programs: tuple[str, ...]
    reads_secret: tuple[str, ...]  # protected secret paths the command reads
    writes_config: tuple[str, ...]  # protected config paths the command writes
    urls: tuple[str, ...]  # destinations the command contacts
    destructive: bool
    parsed: bool
    note: str = ""


_READERS = {"cat", "type", "less", "more", "head", "tail", "grep", "awk", "sed", "strings", "base64", "xxd", "od", "nl",
            "get-content", "gc", "copy", "cp", "scp", "rsync", "tar", "zip"}
_NET = {"curl", "wget", "nc", "ncat", "netcat", "invoke-webrequest", "iwr", "invoke-restmethod", "irm", "ssh", "scp", "rsync",
        "ftp", "sftp", "telnet", "nslookup", "dig", "host", "ping"}
_DESTRUCTIVE_PROGRAMS = {"mkfs", "dd", "shred", "format", "diskpart", "remove-item", "rd", "rmdir", "del", "erase"}
_URL = re.compile(r"\b(?:https?|ftp|wss?)://[^\s'\"<>]+", re.I)
_CLOUD_DELETE = re.compile(r"\b(?:aws|gcloud|az|kubectl|terraform|railway|heroku|vercel|fly|doctl)\b.*\b(?:delete|destroy|"
                           r"rm|remove|terminate|drop|purge)\b", re.I)


def shell_effect(command: str) -> ShellEffect:
    cmd = command or ""
    try:
        tokens = shlex.split(cmd, posix=True)
        parsed = True
    except ValueError:
        tokens, parsed = cmd.split(), False
    # split on command separators so "a; cat .env | curl x" sees every program
    programs, reads, writes = [], [], []
    current: list[str] = []
    segments: list[list[str]] = []
    for t in tokens:
        if t in ("|", "||", "&&", ";", "&"):
            segments.append(current)
            current = []
        else:
            current.append(t)
    segments.append(current)
    destructive = False
    for seg in segments:
        if not seg:
            continue
        prog = posixpath.basename(seg[0].replace("\\", "/")).lower().removesuffix(".exe")
        if prog in ("sudo", "env", "nohup", "time") and len(seg) > 1:
            prog = posixpath.basename(seg[1].replace("\\", "/")).lower()
        programs.append(prog)
        rest = seg[1:]
        if prog in _READERS:
            reads += [a for a in rest if path_class(a) == "secret"]
        if prog in ("env", "printenv", "set", "export") and len(seg) == 1:
            reads.append("environment variables")
        if prog == "rm" and any(re.fullmatch(r"-[a-z]*[rf][a-z]*", a) for a in rest):
            destructive = True
        if prog in _DESTRUCTIVE_PROGRAMS:
            destructive = True
        if prog in ("git",) and any(a in ("push", "reset", "clean") for a in rest) and any(a in ("--force", "-f", "--hard", "-fd", "-fdx") for a in rest):
            destructive = True
    for i, t in enumerate(tokens):  # redirections that write: "> file", ">> file", "tee file"
        if t in (">", ">>") and i + 1 < len(tokens) and path_class(tokens[i + 1]) == "config":
            writes.append(tokens[i + 1])
        m = re.fullmatch(r">>?(.+)", t)
        if m and path_class(m.group(1)) == "config":
            writes.append(m.group(1))
    for i, p in enumerate(programs):
        if p == "tee":
            seg_args = [a for a in tokens if path_class(a) == "config"]
            writes += seg_args
    if _CLOUD_DELETE.search(cmd) or re.search(r"(?i)(?:^|\s)(?:-X\s*|--request[\s=]+)DELETE\b", cmd):
        destructive = True
    if re.search(r"(?i)\bdrop\s+(?:table|database|schema)\b|\btruncate\s+table\b", cmd):
        destructive = True
    urls = tuple(dict.fromkeys(_URL.findall(cmd)))
    note = "" if parsed else "the command could not be parsed exactly"
    return ShellEffect(tuple(programs), tuple(dict.fromkeys(reads)), tuple(dict.fromkeys(writes)), urls, destructive, parsed, note)


# ---- destinations named by argument -----------------------------------------------------------------------------------
# Real e-mail and messaging tools carry more than one recipient field. A recipient in `cc` or `bcc` that the registry did
# not list would be an unchecked exit (postmark-mcp's BCC is the extreme case), so these names are always destinations.
DESTINATION_ARG_NAMES = re.compile(r"(?i)^(?:to|cc|bcc|reply_?to|recipients?|recipient_list|forward_to|send_to|"
                                   r"url|uri|endpoint|webhook|webhook_url|callback_url|host|hostname|channel)$")


def extra_destination_args(args: dict[str, Any], listed: list[str]) -> list[str]:
    """Argument names that carry a destination but were not listed in the registry for this tool."""
    return [k for k in (args or {}) if k not in listed and DESTINATION_ARG_NAMES.match(k)]
