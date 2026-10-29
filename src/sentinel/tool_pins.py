"""Tool definitions are pinned by hash and their descriptions are read before the model reads them (plan Q5).

A tool's description and input schema go straight to the model, and nothing in MCP stops a server from changing them after
they were approved (a "rug pull": Invariant's WhatsApp MCP case) or from writing instructions into them (tool poisoning).
Sentinel therefore hashes each tool's full wire definition (name, description, input schema, annotations) the first time it
sees it, and from then on:
- a definition that differs from its pin is hidden from the agent and refused until the officer approves the new one;
- a description that reads like instructions to the model is never pinned in the first place: hidden and refused until the
  officer has looked at it.

Hashing the full definition, not the summary a person reviews, is deliberate: a changed schema or annotation can steer the
model as much as a changed sentence. Pure logic plus a small JSON file; no model reads the descriptions (invariant 1).
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Phrases that address the model rather than describe the tool. Each pattern is tested with a true and a false example.
_SUSPICIOUS = [
    (re.compile(r"(?i)\bignore\b.{0,40}\b(?:previous|prior|above|earlier|other|all)\b.{0,20}\b(?:instructions?|rules?|prompts?)"),
     "asks the model to ignore its instructions"),
    (re.compile(r"(?i)<\s*(?:important|system|instructions?|secret|hidden)\s*>"), "carries a hidden instruction block"),
    (re.compile(r"(?i)\b(?:do not|don't|never)\b.{0,30}\b(?:tell|mention|inform|show|reveal|notify)\b.{0,30}\b(?:user|human|operator)"),
     "tells the model to hide something from the user"),
    (re.compile(r"(?i)\b(?:before|after|whenever|every time)\b.{0,40}\b(?:using|calling|you use|you call)\b.{0,40}\b(?:you must|always|first)\b"),
     "tells the model what to do around other calls"),
    (re.compile(r"(?i)(?:~/|\$home/|%userprofile%)?\.(?:ssh|aws|env)\b|id_rsa|mcp\.json|\.cursor/|\.claude/|credentials\b|private key"),
     "names a credential or configuration file"),
    (re.compile(r"(?i)\b(?:system prompt|your instructions|as an ai|you are (?:now|an?)\b)"), "talks to the model about itself"),
    (re.compile(r"(?i)\b(?:send|forward|copy|bcc|cc|post|upload|exfiltrate)\b.{0,40}\b(?:to|into)\b.{0,40}"
                r"(?:[a-z0-9._%+\-]+@[a-z0-9.\-]+|https?://)"), "tells the model to send something to an address"),
]


def scan_description(text: str) -> list[str]:
    """Plain reasons why a tool description reads like instructions to the model, or [] if it reads like a description."""
    t = text or ""
    return [reason for pattern, reason in _SUSPICIOUS if pattern.search(t)]


def definition_hash(name: str, description: str | None, schema: dict | None, annotations: Any = None) -> str:
    if annotations is not None and hasattr(annotations, "model_dump"):
        annotations = annotations.model_dump(mode="json", exclude_none=True)
    body = {"name": name, "description": description or "", "input_schema": schema or {}, "annotations": annotations or {}}
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


@dataclass
class PinState:
    status: str  # ok | changed | suspicious
    detail: str = ""
    seen_hash: str = ""


@dataclass
class ToolPins:
    """The approved definition hash of each tool, kept in `path` (JSON) when one is given."""

    path: Path | None = None
    pins: dict[str, str] = field(default_factory=dict)
    states: dict[str, PinState] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path | None) -> "ToolPins":
        pins: dict[str, str] = {}
        if path is not None and path.exists():
            try:
                pins = {str(k): str(v) for k, v in json.loads(path.read_text(encoding="utf-8")).items()}
            except (OSError, ValueError):
                pins = {}  # an unreadable pin file is treated as no pins: every tool is checked again on first sight
        return cls(path=path, pins=pins)

    def _save(self) -> None:
        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self.pins, sort_keys=True, indent=1), encoding="utf-8")

    def observe(self, name: str, h: str, description: str | None) -> tuple[PinState, bool]:
        """Record what the tool server says this tool is now. Returns (state, changed_since_last_observation)."""
        before = self.states.get(name)
        pinned = self.pins.get(name)
        if pinned is None:
            reasons = scan_description(description or "")
            if reasons:
                state = PinState("suspicious", "; ".join(reasons), h)
            else:
                self.pins[name] = h  # trust on first use, for a description that reads like a description
                self._save()
                state = PinState("ok", "", h)
        elif pinned == h:
            state = PinState("ok", "", h)
        else:
            state = PinState("changed", "the tool's definition changed since it was approved", h)
        self.states[name] = state
        return state, before is None or before.status != state.status

    def state(self, name: str) -> PinState | None:
        return self.states.get(name)

    def blocked(self, name: str) -> PinState | None:
        s = self.states.get(name)
        return s if s is not None and s.status != "ok" else None

    def approve(self, name: str) -> str:
        """The officer approves the definition last seen for `name`. Returns the hash now pinned."""
        s = self.states.get(name)
        if s is None or not s.seen_hash:
            raise KeyError(name)
        self.pins[name] = s.seen_hash
        self.states[name] = PinState("ok", "", s.seen_hash)
        self._save()
        return s.seen_hash
