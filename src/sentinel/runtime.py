"""Shared state for one Sentinel process: bus, sessions, registry, templates, signing key."""

from __future__ import annotations

from dataclasses import dataclass, field

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from .contracts import SessionStore, load_templates
from .events import EventBus
from .models import TaskContract
from .registry import Registry, load_registry


@dataclass
class Runtime:
    key: Ed25519PrivateKey
    tools_url: str
    gateway_url: str
    downstream_token: str  # secret shared only with the tool server; the agent never sees it
    api_token: str  # static bearer token for the console and REST API
    bus: EventBus = field(default_factory=EventBus)
    store: SessionStore = field(default_factory=SessionStore)
    registry: Registry = field(default_factory=load_registry)
    templates: dict = field(default_factory=load_templates)
    drafts: dict[str, TaskContract] = field(default_factory=dict)


def build_runtime(*, tools_url: str, gateway_url: str, downstream_token: str, api_token: str,
                  key: Ed25519PrivateKey | None = None) -> Runtime:
    """Refuses to build without both secrets: Sentinel never starts open."""
    if not downstream_token or not api_token:
        raise ValueError("both the downstream token and the API token are required")
    return Runtime(key=key or Ed25519PrivateKey.generate(), tools_url=tools_url, gateway_url=gateway_url,
                   downstream_token=downstream_token, api_token=api_token)
