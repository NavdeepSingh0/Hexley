"""I1 data contracts (ARCHITECTURE.md section 4). Changes need a note in docs/DECISIONS.md."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Effect(StrEnum):
    """Verdict names from MVP.md. Precedence: FREEZE > BLOCK > ASK > ALLOW."""

    ALLOW = "ALLOW"
    ASK = "ASK"
    BLOCK = "BLOCK"
    FREEZE = "FREEZE"


EFFECT_PRECEDENCE = [Effect.FREEZE, Effect.BLOCK, Effect.ASK, Effect.ALLOW]


class Column(StrEnum):
    UNPROTECTED = "unprotected"  # "No policy enforcement - instrumented baseline"
    R1_ONLY = "r1_only"  # "R1-only access control"
    SENTINEL = "sentinel"


class Mode(StrEnum):
    FINGERPRINT = "fingerprint"
    HARDENED = "hardened"


class RuleId(StrEnum):
    R1 = "R1"
    R2 = "R2"
    R3 = "R3"
    R4 = "R4"
    R5 = "R5"
    R6 = "R6"


class ReasonCode(StrEnum):
    ALLOWED = "ALLOWED"
    NOT_ENFORCED = "NOT_ENFORCED"  # unprotected baseline: no rules run
    NOT_IN_SLIP = "NOT_IN_SLIP"  # R1
    EGRESS_TEMPLATE_INVALID = "EGRESS_TEMPLATE_INVALID"  # R1
    NOT_IN_REGISTRY = "NOT_IN_REGISTRY"  # R1
    SECRET_EGRESS = "SECRET_EGRESS"  # R2
    DEST_FROM_UNTRUSTED = "DEST_FROM_UNTRUSTED"  # R3
    HUMAN_VERIFICATION = "HUMAN_VERIFICATION"  # R4
    VOLUME_EXCEEDED = "VOLUME_EXCEEDED"  # R5
    BLOCK_THRESHOLD_FREEZE = "BLOCK_THRESHOLD_FREEZE"  # R6
    SESSION_INVALID = "SESSION_INVALID"
    AUDIT_UNAVAILABLE = "AUDIT_UNAVAILABLE"  # no durable audit record, so the action was not run
    FAIL_CLOSED = "FAIL_CLOSED"


class Capability(StrEnum):
    READ = "read"
    WRITE = "write"
    SEND = "send"


class Integrity(StrEnum):
    TRUSTED = "trusted"
    UNTRUSTED = "untrusted"


class Confidentiality(StrEnum):
    PUBLIC = "public"
    INTERNAL = "internal"
    RESTRICTED = "restricted"  # shown as SECRET in the console


class SessionStatus(StrEnum):
    PENDING = "pending"
    ACTIVE = "active"
    FROZEN = "frozen"
    REVOKED = "revoked"


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ---- tool registry -----------------------------------------------------------------------------
class ToolEntry(_Model):
    name: str
    known: bool = True
    capability: Capability
    resource_class: str
    outbound: bool
    consequential: bool
    output_integrity: Integrity
    output_confidentiality: Confidentiality
    fingerprint_fields: list[str] = Field(default_factory=list)
    destination_args: list[str] = Field(default_factory=list)  # arguments that name where data is going
    requires_human_verification: bool = False


# ---- task contract (permission slip) -----------------------------------------------------------
class EgressSlot(_Model):
    pattern: str | None = None
    enum: list[str] | None = None
    equals_session: str | None = None


class EgressTemplate(_Model):
    template_id: str
    recipient_from: str
    slots: dict[str, EgressSlot]
    body: str
    max_messages: int = 1


class TaskContract(_Model):
    contract_id: str
    template: str
    objective: str
    officer: str
    mode: Mode = Mode.FINGERPRINT
    allowed_tools: list[str]
    resource_classes: list[str]
    allowed_recipient_domains: list[str]
    max_records: int
    max_messages: int
    max_records_out: int
    egress_templates: list[EgressTemplate] = Field(default_factory=list)
    issued_at: datetime
    expires_at: datetime
    status: SessionStatus = SessionStatus.PENDING
    contract_hash: str = ""

    def compute_hash(self) -> str:
        """SHA-256 over canonical JSON of everything the officer confirmed (status and hash excluded)."""
        body = self.model_dump(mode="json", exclude={"status", "contract_hash"})
        canonical = json.dumps(body, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode()).hexdigest()


# ---- actions and decisions ---------------------------------------------------------------------
class AgentAction(_Model):
    action_id: str
    ts: datetime
    session_id: str
    contract_id: str
    column: Column
    tool: str
    capability: Capability
    resource_class: str
    args: dict[str, Any] = Field(default_factory=dict)
    outbound: bool = False


class Evidence(_Model):
    kind: str
    detail: str
    matched_tokens: list[str] = Field(default_factory=list)
    source_ref: str | None = None


class Decision(_Model):
    decision_id: str
    action_id: str
    effect: Effect
    rule_ids: list[RuleId] = Field(default_factory=list)
    reason_code: ReasonCode
    summary_plain: str
    evidence: list[Evidence] = Field(default_factory=list)
    latency_ms: float = 0.0


# ---- events ------------------------------------------------------------------------------------
class EventEnvelope(_Model):
    type: str
    session_id: str | None
    column: Column | None
    ts: datetime
    payload: dict[str, Any] = Field(default_factory=dict)
