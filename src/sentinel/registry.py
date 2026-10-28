"""Tool registry loader. Labels come only from here; unknown means untrusted + restricted (invariant 6).

Two sources: the built-in `config/registry.yaml`, and an OVERLAY file (`registry.local.yaml`, next to the audit log) holding
tools the officer has classified through the console or API. The overlay can only ADD tools. It can never replace or weaken
a built-in entry, and it cannot make a tool gateway-local or give it an egress template: the officer labels a tool's risk,
nothing more. A tool nobody has classified keeps the conservative default: R1 refuses it and the agent never sees it.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml

from .models import ToolEntry

CONFIG_DIR = Path(__file__).parent / "config"


class RegistryError(Exception):
    """The registry file is missing, malformed, or invalid. Sentinel refuses to start."""


class Registry:
    def __init__(self, tools: dict[str, ToolEntry], default: dict, base_names: frozenset[str] | None = None):
        self._tools = dict(tools)
        self._default = default
        self._base = frozenset(base_names if base_names is not None else tools)

    def get(self, name: str) -> ToolEntry:
        """Return the entry for `name`; an unregistered tool gets the conservative default (known=False)."""
        entry = self._tools.get(name)
        if entry is not None:
            return entry
        return ToolEntry(name=name, known=False, **self._default)

    def is_known(self, name: str) -> bool:
        return name in self._tools

    def is_builtin(self, name: str) -> bool:
        return name in self._base

    def names(self) -> list[str]:
        return sorted(self._tools)

    def add(self, entry: ToolEntry) -> None:
        """Add or update an officer-classified tool. Built-in entries are never touched."""
        if entry.name in self._base:
            raise RegistryError(f"'{entry.name}' is a built-in registry entry and cannot be changed")
        if entry.local or entry.egress_template is not None:
            raise RegistryError("a classification cannot make a tool gateway-local or give it an egress template")
        self._tools[entry.name] = entry

    def overlay_entries(self) -> dict[str, ToolEntry]:
        return {n: e for n, e in self._tools.items() if n not in self._base}


def load_registry(path: Path | None = None, overlay: Path | None = None) -> Registry:
    path = path or CONFIG_DIR / "registry.yaml"
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        default = raw["default"]
        tools = {name: ToolEntry(name=name, **spec) for name, spec in raw["tools"].items()}
        ToolEntry(name="__default__", known=False, **default)  # validate the default too
    except Exception as e:  # noqa: BLE001 - any failure to load must stop startup
        raise RegistryError(f"invalid registry {path}: {e}") from e
    registry = Registry(tools, default)
    if overlay is not None and Path(overlay).exists():
        try:
            extra = yaml.safe_load(Path(overlay).read_text(encoding="utf-8")) or {}
            for name, spec in (extra.get("tools") or {}).items():
                registry.add(ToolEntry(name=name, **spec))  # a clash with a built-in entry raises here: refuse to start
        except Exception as e:  # noqa: BLE001 - a damaged or tampered overlay must stop startup, not be half-applied
            raise RegistryError(f"invalid registry overlay {overlay}: {e}") from e
    return registry


def save_overlay(registry: Registry, overlay: Path) -> None:
    """Write the officer-classified entries atomically (a crash never leaves half a file)."""
    body = {"registry_overlay_version": 1,
            "tools": {n: e.model_dump(mode="json", exclude={"name", "known", "local", "egress_template"}, exclude_defaults=False)
                      for n, e in sorted(registry.overlay_entries().items())}}
    tmp = Path(str(overlay) + ".tmp")
    tmp.write_text(yaml.safe_dump(body, sort_keys=False), encoding="utf-8")
    os.replace(tmp, overlay)


# ---- suggestions for tools nobody has classified yet ---------------------------------------------------------------
_SEND = ("send", "email", "mail", "post", "upload", "publish", "webhook", "notify", "message", "share", "tweet", "slack",
         "sms", "forward", "reply", "transfer", "pay")
_WRITE = ("write", "save", "create", "update", "delete", "remove", "drop", "exec", "execute", "run", "shell", "command",
          "insert", "modify", "put", "patch", "move", "rename", "commit", "push", "set")
_FETCH = ("fetch", "http", "url", "browse", "download", "curl", "scrape", "crawl", "page")
_UNTRUSTED_SOURCE = ("read", "fetch", "browse", "web", "page", "mail", "inbox", "document", "doc", "pdf", "file", "ticket",
                     "comment", "issue", "message", "scrape", "download", "search")
_CONFIDENTIAL = ("customer", "salary", "payroll", "employee", "finance", "stock", "inventory", "secret", "password",
                 "credential", "patient", "medical", "account", "bank", "invoice", "contract", "private", "database", "db",
                 "sql", "record")
_FREE_FORM = ("command", "cmd", "script", "code", "shell")  # an argument that is itself a program
_URL_ARGS = ("url", "uri", "endpoint", "webhook", "link")
_PATH_ARGS = ("path", "file", "filename", "filepath", "directory", "folder")
_DEST_ARGS = ("to", "recipient", "recipients", "email", "address", "cc", "bcc", "destination", "target", *_URL_ARGS, *_PATH_ARGS)


def suggest_classification(name: str, description: str = "", input_schema: dict[str, Any] | None = None) -> dict[str, Any]:
    """A first guess for an unclassified tool, from its name, description and argument names. It is only a suggestion:
    it is never applied, the officer decides, and it errs towards caution (unknown content is untrusted, unknown data is
    confidential, unknown writes are consequential)."""
    name_words = set(re.findall(r"[a-z]+", name.lower().replace("_", " ")))
    all_words = name_words | set(re.findall(r"[a-z]+", description.lower()))
    props = [p.lower() for p in ((input_schema or {}).get("properties") or {})]
    reasons: list[str] = []

    def named(group: tuple[str, ...]) -> bool:
        return bool(name_words & set(group))

    def singular(words: set[str]) -> set[str]:
        return {w[:-1] if len(w) > 3 and w.endswith("s") else w for w in words}

    # The NAME leads. The description is consulted for "sends/fetches" only when the name says nothing about what the tool
    # does, and never makes a tool a writer: "Run a SQL query" must not turn a read-only query tool into a writer.
    name_has_verb = bool(name_words & set(_SEND + _WRITE + _FETCH))
    sends = named(_SEND) or (not name_has_verb and bool(all_words & set(_SEND)))
    fetches = named(_FETCH) or (not name_has_verb and bool(all_words & set(_FETCH)))
    writes = named(_WRITE) or any(p in _FREE_FORM for p in props)
    dest_args = [p for p in props if p in _DEST_ARGS]
    kind = "url" if any(p in _URL_ARGS for p in dest_args) else "path" if any(p in _PATH_ARGS for p in dest_args) else "email"
    outbound = sends or (fetches and any(p in _URL_ARGS for p in props))
    capability = "send" if sends else "write" if writes else "read"
    if sends:
        reasons.append("the name or description suggests it sends something outside")
    if writes and not sends:
        reasons.append("the name or description suggests it changes something")
    if fetches and outbound and not sends:
        reasons.append("it takes a web address, so what it asks for can carry data out")
    if outbound and not dest_args:
        reasons.append("it looks outbound but no argument clearly names the destination: choose one before saving")
    confidential = bool(singular(all_words) & set(_CONFIDENTIAL))
    if confidential:
        reasons.append("it mentions data that is usually confidential")
    if any(p in ("sql", "query") for p in props) and not writes:
        reasons.append("it takes free-form SQL: if it can change data, mark it consequential")
    if any(p in _FREE_FORM for p in props):
        reasons.append("it takes a free-form command or script, so it can do more than its name says")
    untrusted_source = bool(singular(all_words) & set(_UNTRUSTED_SOURCE))
    return {
        "capability": capability,
        "resource_class": name,
        "outbound": bool(outbound),
        "consequential": bool(sends or writes or outbound),
        "output_integrity": "untrusted" if (untrusted_source or not (sends or writes)) else "trusted",
        "output_confidentiality": "restricted" if confidential else "internal",
        "fingerprint_fields": ["all"] if confidential else [],
        "destination_args": dest_args if outbound else [],
        "destination_kind": kind,
        "requires_human_verification": False,
        "reasons": reasons or ["no strong signal: treated as a read of content that may be untrusted"],
    }
