"""Secrets and credentials found in tool results (PRODUCT_AUDIT §7 P2, plan phase Q2).

Every tool result is scanned, whatever the registry says about the tool: a key in a runbook, a token in a support
ticket, a password in a config file is a credential however it was reached (PocketOS, Supabase MCP, Comment and
Control, Antigravity). Found values are kept in memory for the session only and are never written to the audit log;
evidence shows a masked form.

Pure functions plus a small per-session index. No I/O, no clock, no model (invariant 1). The patterns follow the
shapes published by the issuers and by secret scanners; each one is tested with a true and a false example.
"""

from __future__ import annotations

import html
import re
import unicodedata
import urllib.parse
from dataclasses import dataclass, field
from typing import Any

# (label, pattern, group holding the secret). Order matters only for labelling: a value is indexed once.
_PATTERNS: list[tuple[str, re.Pattern[str], int]] = [
    ("private key", re.compile(r"-----BEGIN (?:[A-Z]+ )*PRIVATE KEY-----\s*([A-Za-z0-9+/=\s]{40,}?)\s*-----END"), 1),
    ("AWS access key", re.compile(r"\b((?:AKIA|ASIA)[0-9A-Z]{16})\b"), 1),
    ("AWS secret key", re.compile(r"(?i)aws_?secret_?access_?key\W{0,4}([A-Za-z0-9/+=]{40})\b"), 1),
    ("GitHub token", re.compile(r"\b(gh[pousr]_[A-Za-z0-9]{36,255}|github_pat_[A-Za-z0-9_]{22,255})\b"), 1),
    ("Slack token", re.compile(r"\b(xox[abposr]-[A-Za-z0-9-]{10,})\b"), 1),
    ("Stripe key", re.compile(r"\b((?:sk|rk)_(?:live|test)_[A-Za-z0-9]{16,})\b"), 1),
    ("Google API key", re.compile(r"\b(AIza[0-9A-Za-z_\-]{35})\b"), 1),
    ("model API key", re.compile(r"\b((?:sk-(?:proj-|ant-)?|nvapi-)[A-Za-z0-9_\-]{20,})\b"), 1),
    ("JSON web token", re.compile(r"\b(eyJ[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,})\b"), 1),
    ("bearer token", re.compile(r"(?i)\bbearer\s+([A-Za-z0-9._~+/\-]{20,}=*)"), 1),
    ("password in a connection string", re.compile(r"\b[a-z][a-z0-9+.\-]*://[^\s:/@]+:([^\s@/]{4,})@[^\s/]+"), 1),
    # KEY=value lines (.env, shell exports, YAML-ish) where the name says it is a secret
    ("secret setting", re.compile(
        r"(?im)^[ \t]*(?:export[ \t]+)?[A-Za-z0-9_.\-]*(?:secret|token|passw(?:or)?d|pwd|api[_-]?key|apikey|private[_-]?key|"
        r"access[_-]?key|client[_-]?secret|auth)[A-Za-z0-9_.\-]*[ \t]*[=:][ \t]*[\"']?([^\s\"'#]{6,})"), 1),
    # "password": "..." in JSON
    ("secret setting", re.compile(
        r"(?i)\"[A-Za-z0-9_.\-]*(?:secret|token|passw(?:or)?d|api[_-]?key|apikey|private[_-]?key|access[_-]?key)[A-Za-z0-9_.\-]*\""
        r"\s*:\s*\"([^\"]{6,})\""), 1),
]

# Values that look like settings but are not secrets: references, placeholders, booleans, empty-looking stand-ins.
_NOT_A_SECRET = re.compile(r"(?i)^(?:\$\{.*\}|\$[A-Z_]+|<[^>]*>|\{\{.*\}\}|x{4,}|\*{3,}|true|false|null|none|"
                           r"changeme-?later|your[_-].*|example|redacted|placeholder)$")

# Argument names that carry credentials: a discovered secret here is being USED, not just sent (R9).
CREDENTIAL_ARG = re.compile(r"(?i)(?:^|[._\[\]-])(token|api[_-]?key|apikey|key|secret|passw(?:or)?d|pwd|auth|authorization|"
                            r"bearer|credential|credentials|access[_-]?key|client[_-]?secret|headers?)(?:$|[._\[\]-])")


@dataclass(frozen=True)
class FoundSecret:
    label: str
    value: str


def _clean(text: str) -> str:
    """Undo URL and HTML escaping and Unicode tricks, but keep case: secrets are case-sensitive."""
    t = text
    for _ in range(3):
        decoded = html.unescape(urllib.parse.unquote(t))
        if decoded == t:
            break
        t = decoded
    t = unicodedata.normalize("NFKC", t)
    return re.sub("[­​-‏⁠﻿]", "", t)


def find_secrets(text: str) -> list[FoundSecret]:
    """Every secret-shaped value in `text`, each once."""
    t = _clean(text)
    found: dict[str, str] = {}
    for label, pattern, group in _PATTERNS:
        for m in pattern.finditer(t):
            value = re.sub(r"\s+", "", m.group(group)) if label == "private key" else m.group(group)
            value = value.strip().rstrip(",;")
            if len(value) < 6 or _NOT_A_SECRET.match(value) or len(set(value)) < 4:
                continue
            found.setdefault(value, label)
    return [FoundSecret(label, value) for value, label in found.items()]


def mask(value: str) -> str:
    """What evidence may show: never the whole secret."""
    return f"{value[:4]}...{value[-2:]}" if len(value) > 10 else "***"


@dataclass(frozen=True)
class SecretMatch:
    label: str
    masked: str
    source_ref: str
    path: str
    source_action: str | None = None


@dataclass
class SecretIndex:
    """Per-session secrets seen in tool results. In memory only; the audit log never holds a value."""

    values: dict[str, tuple[str, str, str | None]] = field(default_factory=dict)  # value -> (label, source tool, call id)

    def add(self, result_text: str, source_ref: str, action_id: str | None = None) -> list[FoundSecret]:
        new = []
        for s in find_secrets(result_text):
            if s.value not in self.values:
                self.values[s.value] = (s.label, source_ref, action_id)
                new.append(s)
        return new

    def __bool__(self) -> bool:
        return bool(self.values)

    def scan_text(self, text: str, path: str = "") -> list[SecretMatch]:
        if not self.values:
            return []
        t = _clean(text)
        squeezed = re.sub(r"\s+", "", t)  # a key re-wrapped over several lines is still the key
        out = []
        for value, (label, source, action) in self.values.items():
            if value in t or (len(value) >= 20 and value in squeezed):
                out.append(SecretMatch(label, mask(value), source, path, action))
        return out

    def scan_args(self, value: Any, path: str = "") -> list[SecretMatch]:
        if isinstance(value, str):
            return self.scan_text(value, path)
        if isinstance(value, bool) or value is None:
            return []
        if isinstance(value, dict):
            return [m for k, v in value.items() for m in self.scan_args(v, f"{path}.{k}" if path else str(k))]
        if isinstance(value, (list, tuple)):
            return [m for i, v in enumerate(value) for m in self.scan_args(v, f"{path}[{i}]" if path else f"[{i}]")]
        return self.scan_text(str(value), path)
