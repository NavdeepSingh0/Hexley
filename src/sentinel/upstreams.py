"""Several tool servers behind one gateway (roadmap W1.1, W1.2; plan F2).

The agent connects to Sentinel only. Each upstream (GitHub, Notion, Slack, mail, ...) is an MCP server that Sentinel
starts (stdio) or calls (HTTP), and its tools are offered as `<upstream>__<tool>`: `github__create_issue`. A double
underscore, not a dot, because model APIs accept only letters, digits, `_` and `-` in a tool name.

Sentinel holds every upstream's credential. The config names an environment variable (`${GITHUB_TOKEN}`), never a value;
the values come from a git-ignored `.env.connectors` file or the process environment (a hosting platform's secret
settings). A stdio upstream is started with a minimal environment holding only its own variables; an HTTP upstream gets
its header from Sentinel. The agent's own headers are never forwarded, so the agent has no route to a credential.

An upstream whose credential is missing is not started; `sentinel connectors check` says which and why, and never
prints a value.
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import yaml
from fastmcp.client.transports import StdioTransport, StreamableHttpTransport
from fastmcp.server.providers.proxy import ProxyClient
from fastmcp.server.transforms import Namespace
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SEP = "__"
DEFAULT_CONFIG = Path(__file__).parent / "config" / "upstreams.yaml"
DEFAULT_ENV_FILE = Path(".env.connectors")

_NAME = re.compile(r"[a-z][a-z0-9]{1,19}")
_VAR = re.compile(r"\$\{([A-Z][A-Z0-9_]*)\}")
_RESERVED = {"sentinel", "mcp", "builtin"}
# What a child process needs to start at all (a shell, npx or docker finding its own files). Nothing else of Sentinel's
# environment is passed on: not the officer's token, not the model keys, not another upstream's credential.
_BASE_ENV = ("PATH", "PATHEXT", "SYSTEMROOT", "SYSTEMDRIVE", "WINDIR", "COMSPEC", "TEMP", "TMP", "HOME", "USERPROFILE",
             "APPDATA", "LOCALAPPDATA", "PROGRAMDATA", "PROGRAMFILES", "PROGRAMFILES(X86)", "LANG", "LC_ALL")

log = logging.getLogger("sentinel.upstreams")


class Upstream(BaseModel):
    """One tool server behind the gateway, as written in `upstreams.yaml`. Holds variable names, never values."""

    model_config = ConfigDict(extra="forbid")

    name: str
    transport: Literal["stdio", "http"]
    description: str = ""
    command: str | None = None  # stdio
    args: list[str] = Field(default_factory=list)  # stdio
    url: str | None = None  # http
    env: dict[str, str] = Field(default_factory=dict)  # stdio: child variable -> "${VAR}" or a literal setting
    headers: dict[str, str] = Field(default_factory=dict)  # http: header -> "Bearer ${VAR}"
    # The tool-name prefix. Empty means the tools keep their own names, which is how one server can try to shadow another's
    # tool (send_email offered twice): allowed so that the refusal can be shown and tested, never the default.
    namespace: str | None = None
    # How the connection starts. "legacy" is the classic initialize handshake that published servers speak; "auto" first
    # probes the newer discovery request, and GitHub's server (v2.0.3, stdio) then refuses the handshake as a duplicate.
    protocol: Literal["legacy", "auto"] = "legacy"
    # Variables that are settings, not secrets (an account's own address appears in every mail, so treating it as a held
    # credential would withhold every result). They still come from the credentials file and never appear in this config.
    public_vars: list[str] = Field(default_factory=list)
    enabled: bool = True

    @field_validator("name")
    @classmethod
    def _name(cls, v: str) -> str:
        if not _NAME.fullmatch(v) or v in _RESERVED:
            raise ValueError(f"upstream name {v!r} must be 2-20 lowercase letters or digits, starting with a letter, "
                             f"and not one of {sorted(_RESERVED)}")
        return v

    @model_validator(mode="after")
    def _shape(self) -> Upstream:
        if self.transport == "stdio" and not self.command:
            raise ValueError(f"upstream {self.name!r}: a stdio upstream needs a command")
        if self.transport == "http" and not (self.url or "").startswith(("https://", "http://127.0.0.1", "http://localhost")):
            raise ValueError(f"upstream {self.name!r}: an http upstream needs an https url (plain http only on this computer)")
        if self.namespace is None:
            self.namespace = self.name
        if self.namespace and not _NAME.fullmatch(self.namespace):
            raise ValueError(f"upstream {self.name!r}: namespace {self.namespace!r} is not a valid prefix")
        return self

    def variables(self) -> list[str]:
        """The credential variables this upstream needs (names only)."""
        return sorted({m for v in [*self.env.values(), *self.headers.values(), *self.args, self.url or ""]
                       for m in _VAR.findall(v)})

    def prefixed(self, tool: str) -> str:
        return f"{self.namespace}{SEP}{tool}" if self.namespace else tool


class UpstreamConfigError(ValueError):
    pass


def load_upstreams(path: Path | None = None) -> list[Upstream]:
    """Read and validate the upstream list. Names and prefixes must be unique, so two upstreams can never be
    configured to answer to the same prefix."""
    path = Path(path or DEFAULT_CONFIG)
    if not path.exists():
        return []
    doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    try:
        ups = [Upstream(**u) for u in doc.get("upstreams") or []]
    except Exception as e:  # pydantic's message names the field; it never holds a credential (the file has only names)
        raise UpstreamConfigError(f"{path}: {e}") from e
    names = [u.name for u in ups]
    prefixes = [u.namespace for u in ups if u.namespace]
    for label, items in (("name", names), ("prefix", prefixes)):
        dup = sorted({x for x in items if items.count(x) > 1})
        if dup:
            raise UpstreamConfigError(f"{path}: upstream {label} used twice: {', '.join(dup)}")
    return ups


def read_env_file(path: Path) -> dict[str, str]:
    """KEY=VALUE lines from a git-ignored credentials file. Values are returned, never logged or printed."""
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip().removeprefix("export ").strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if re.fullmatch(r"[A-Z][A-Z0-9_]*", key):
            out[key] = value
    return out


@dataclass
class Credentials:
    """The values Sentinel holds for its upstreams. `repr` never shows a value."""

    values: dict[str, str] = field(default_factory=dict, repr=False)
    public: frozenset[str] = frozenset()  # variables that are settings, not secrets (Upstream.public_vars)

    @classmethod
    def load(cls, env_file: Path | None = None, environ: dict[str, str] | None = None,
             wanted: list[str] | None = None) -> Credentials:
        """From the file first, then the process environment (how a hosting platform passes secrets). Only the variables an
        upstream names are kept."""
        environ = dict(os.environ) if environ is None else environ
        file_values = read_env_file(Path(env_file or DEFAULT_ENV_FILE))
        names = set(file_values) if wanted is None else set(wanted)
        return cls({n: file_values.get(n) or environ.get(n, "") for n in names if file_values.get(n) or environ.get(n)})

    def missing(self, upstream: Upstream) -> list[str]:
        return [v for v in upstream.variables() if not self.values.get(v)]

    def fill(self, template: str) -> str:
        return _VAR.sub(lambda m: self.values.get(m.group(1), ""), template)

    def secret_values(self) -> list[str]:
        """Every held value long enough to be a credential, for withholding results and scrubbing logs."""
        return [v for k, v in self.values.items() if k not in self.public and len(v) >= 8]


def child_env(upstream: Upstream, creds: Credentials, environ: dict[str, str] | None = None) -> dict[str, str]:
    """The whole environment a stdio upstream starts with: what a process needs to run, plus its own settings."""
    environ = dict(os.environ) if environ is None else environ
    upper = {k.upper(): v for k, v in environ.items()}
    base = {k: upper[k] for k in _BASE_ENV if k in upper}
    return {**base, **{k: creds.fill(v) for k, v in upstream.env.items()}}


def client_factory(upstream: Upstream, creds: Credentials):
    """A factory for the gateway's client to this upstream. A stdio server is started once and kept alive (one transport
    instance, reused); an HTTP server gets Sentinel's header on every request. Agent headers are never forwarded."""
    if upstream.transport == "stdio":
        command = upstream.command or ""
        if command == "python":
            command = sys.executable  # the same interpreter as Sentinel, so a server in this repo finds its packages
        else:
            command = shutil.which(command) or command  # npx is npx.cmd on Windows; a process start needs the full name
        transport = StdioTransport(command=command, args=[creds.fill(a) for a in upstream.args],
                                   env=child_env(upstream, creds), keep_alive=True)
        return lambda: ProxyClient(transport, forward_incoming_headers=False, mode=upstream.protocol)
    url = creds.fill(upstream.url or "")
    headers = {k: creds.fill(v) for k, v in upstream.headers.items()}
    return lambda: ProxyClient(StreamableHttpTransport(url, headers=headers), forward_incoming_headers=False,
                               mode=upstream.protocol)


class Prefix(Namespace):
    """FastMCP's namespace with Sentinel's separator: `github__create_issue`, not `github_create_issue`."""

    def __init__(self, prefix: str) -> None:
        super().__init__(prefix)
        self._name_prefix = f"{prefix}{SEP}"


def split_name(tool: str) -> tuple[str | None, str]:
    """`github__create_issue` -> ("github", "create_issue"); a bare name has no upstream."""
    head, sep, rest = tool.partition(SEP)
    return (head, rest) if sep and _NAME.fullmatch(head) else (None, tool)


@dataclass
class UpstreamSet:
    """The upstreams that are configured, which of them run, and why the others do not."""

    upstreams: list[Upstream] = field(default_factory=list)
    creds: Credentials = field(default_factory=Credentials)
    skipped: dict[str, str] = field(default_factory=dict)  # name -> reason (no value ever)

    @classmethod
    def load(cls, config: Path | None = None, env_file: Path | None = None,
             environ: dict[str, str] | None = None) -> UpstreamSet:
        ups = load_upstreams(config)
        creds = Credentials.load(env_file, environ, wanted=[v for u in ups for v in u.variables()])
        creds.public = frozenset(v for u in ups for v in u.public_vars)
        running, skipped = [], {}
        for u in ups:
            if not u.enabled:
                skipped[u.name] = "disabled in the config"
            elif missing := creds.missing(u):
                skipped[u.name] = "credential not set: " + ", ".join(missing)
            else:
                running.append(u)
        for name, why in skipped.items():
            log.info("upstream %s not started: %s", name, why)
        return cls(running, creds, skipped)

    def source_of(self, tool: str) -> str | None:
        """Which configured upstream a tool name belongs to, by its prefix."""
        head, _ = split_name(tool)
        return next((u.name for u in self.upstreams if u.namespace and u.namespace == head), None)


async def check(ups: UpstreamSet, all_configured: list[Upstream], live: bool, timeout: float = 90.0) -> list[dict]:
    """One row per configured upstream: is its credential set, and (live) does it answer with a tool list. A row names
    variables and counts tools; it never holds a credential value, and an error message is scrubbed before it is shown."""
    import asyncio

    secrets = ups.creds.secret_values()

    def scrub(text: str) -> str:
        for v in secrets:
            text = text.replace(v, "***")
        return text[:300]

    rows = []
    for u in all_configured:
        row = {"name": u.name, "transport": u.transport, "prefix": u.namespace or "(none)", "variables": u.variables()}
        if u.name in ups.skipped:
            row.update(status="not started", detail=ups.skipped[u.name])
        elif not live:
            row.update(status="ready", detail="credential set (not contacted; add --live to connect)")
        else:
            try:
                async with client_factory(u, ups.creds)() as c:
                    tools = await asyncio.wait_for(c.list_tools(), timeout)
                row.update(status="ok", detail=f"{len(tools)} tools offered", tools=sorted(u.prefixed(t.name) for t in tools))
            except Exception as e:  # noqa: BLE001 - reported per connector, scrubbed
                row.update(status="failed", detail=scrub(f"{type(e).__name__}: {e}"))
        rows.append(row)
    return rows


class RedactCredentials(logging.Filter):
    """Replaces any held credential value in a log record with ***, whatever logger wrote it."""

    def __init__(self, values: list[str]):
        super().__init__()
        self.values = [v for v in values if v]

    def filter(self, record: logging.LogRecord) -> bool:
        if not self.values:
            return True
        msg = record.getMessage()
        if any(v in msg for v in self.values):
            for v in self.values:
                msg = msg.replace(v, "***")
            record.msg, record.args = msg, None
        return True


def install_log_redaction(values: list[str]) -> RedactCredentials:
    """Attach the filter to every handler of the root logger (filters on a logger do not see records from its children)."""
    f = RedactCredentials(values)
    root = logging.getLogger()
    for h in root.handlers:
        h.addFilter(f)
    root.addFilter(f)
    return f
