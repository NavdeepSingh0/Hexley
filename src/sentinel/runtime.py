"""Shared state for one Sentinel process: bus, sessions, registry, templates, signing keys, audit log."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from . import fixtures
from .approvals import ApprovalStore
from .audit import AuditLog
from .contracts import SessionStore, load_templates
from .events import EventBus
from .models import TaskContract
from .registry import Registry, load_registry


def rotate_audit_log(directory: Path) -> Path | None:
    """Move an existing audit log aside and return where it went (None if there was none).

    Used by `up --demo`: a log that was tampered with during a rehearsal is refused on the next start, which
    would stop the demo from starting at all. Rotating keeps the old file for inspection and starts a fresh,
    valid chain."""
    log = Path(directory) / "audit.jsonl"
    if not log.exists() or log.stat().st_size == 0:
        return None
    moved = log.with_name(f"audit.{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}.jsonl.bak")
    log.rename(moved)
    return moved


def load_or_create_audit_key(directory: Path) -> Ed25519PrivateKey:
    """The audit signing key lives next to the log (git-ignored). A log is only valid for its own key."""
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "audit_key.pem"
    if path.exists():
        key = serialization.load_pem_private_key(path.read_bytes(), password=None)
        if not isinstance(key, Ed25519PrivateKey):
            raise ValueError("audit_key.pem is not an Ed25519 key")
        return key
    key = Ed25519PrivateKey.generate()
    path.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                       serialization.NoEncryption()))
    return key


@dataclass
class Runtime:
    key: Ed25519PrivateKey  # signs session tokens
    tools_url: str
    gateway_url: str
    downstream_token: str  # secret shared only with the tool server; the agent never sees it
    api_token: str  # static bearer token for the console and REST API (demo-grade)
    audit: AuditLog
    allow_tamper: bool = False  # demo switch for POST /audit/tamper; off unless explicitly enabled
    approval_wait: float = 90.0  # seconds a held call waits for the officer; silence is a denial
    approvals: ApprovalStore = field(default_factory=ApprovalStore)
    trusted_addresses: frozenset[str] = frozenset(v["email"] for v in fixtures.VENDOR_MASTER.values())
    recordings_dir: Path = Path("recordings")  # committed recorded runs (synthetic data) used for replay
    runs: object | None = None  # the RunManager, attached by create_api
    bus: EventBus = field(default_factory=lambda: EventBus(history=5000))  # a whole run stays in history
    store: SessionStore = field(default_factory=SessionStore)
    registry: Registry = field(default_factory=load_registry)
    templates: dict = field(default_factory=load_templates)
    drafts: dict[str, TaskContract] = field(default_factory=dict)


def build_runtime(*, tools_url: str, gateway_url: str, downstream_token: str, api_token: str, audit_dir: Path,
                  key: Ed25519PrivateKey | None = None, allow_tamper: bool = False,
                  audit_deadline: float = 2.0, approval_wait: float = 90.0) -> Runtime:
    """Refuses to build without both secrets: Sentinel never starts open."""
    if not downstream_token or not api_token:
        raise ValueError("both the downstream token and the API token are required")
    audit = AuditLog(Path(audit_dir) / "audit.jsonl", load_or_create_audit_key(Path(audit_dir)), deadline=audit_deadline)
    return Runtime(key=key or Ed25519PrivateKey.generate(), tools_url=tools_url, gateway_url=gateway_url,
                   downstream_token=downstream_token, api_token=api_token, audit=audit, allow_tamper=allow_tamper,
                   approval_wait=approval_wait)
