"""I1 data contracts (ARCHITECTURE.md section 4). Changes need a note in docs/DECISIONS.md."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

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
    R7 = "R7"
    R8 = "R8"  # the Rule of Two: restricted + untrusted read, then sending outside, asks the officer (plan Q3)
    R9 = "R9"  # a credential found in data is never used or sent (plan Q2)


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
    TAINTED_ACTION = "TAINTED_ACTION"  # R7: a consequential action after the session read untrusted content
    RULE_OF_TWO = "RULE_OF_TWO"  # R8
    PROTECTED_PATH = "PROTECTED_PATH"  # R1: agent configuration is never written, credential files never read (plan Q4)
    WRONG_EFFECT = "WRONG_EFFECT"  # R1: a read tool asked to change data, or a statement that cannot be read safely
    TOOL_CHANGED = "TOOL_CHANGED"  # R1: the tool's definition changed or reads like instructions (plan Q5)
    DESTRUCTIVE = "DESTRUCTIVE"  # R4: an action that cannot be undone waits for the officer (plan Q4)
    DISCOVERED_CREDENTIAL = "DISCOVERED_CREDENTIAL"  # R9: a secret found in a tool result, used or sent
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
    destination_kind: Literal["email", "url", "path"] = "email"  # how those arguments are read (destinations.keys_in)
    requires_human_verification: bool = False
    egress_template: str | None = None  # a tool that sends only through this fixed template (hardened mode)
    local: bool = False  # implemented inside the gateway, not forwarded to the tool server


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
    subject: str = "Acknowledgement"
    max_messages: int = 1


class TaskContract(_Model):
    contract_id: str
    template: str
    objective: str
    officer: str
    mode: Mode = Mode.FINGERPRINT
    allowed_tools: list[str]
    resource_classes: list[str]
    # Where this task may send things: e-mail/URL domains, or "path:/prefix" entries (destinations.allowed).
    allowed_recipient_domains: list[str]
    # Inside the organisation: restricted data may go here (R2 does not apply) and an action after untrusted content
    # needs no extra approval (R7). A subset of the destinations above, named by the officer; empty means nowhere.
    internal_destinations: list[str] = Field(default_factory=list)
    max_records: int
    max_messages: int
    max_records_out: int
    egress_templates: list[EgressTemplate] = Field(default_factory=list)
    # The quotation this slip is about and the vendor resolved from trusted records (D-019). Both are part of
    # the contract hash, so a token is bound to them.
    work_item_id: str | None = None
    resolved_vendor: dict[str, str] | None = None
    # Plan Q3. strict_flows: the Rule of Two (R8): once this task has read restricted data AND untrusted content, anything
    # sent outside the internal destinations waits for the officer, even to a vendor on file, because a paraphrase of the
    # restricted data would pass value matching. freeze_after: how many refused attempts freeze the session (R6).
    strict_flows: bool = False
    freeze_after: int = 3
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
    # The exact earlier call whose result held the value or address, so the console can link to THAT call and not merely to
    # the first call that used the same tool (two documents read with read_document are two different sources).
    source_action_id: str | None = None


class Decision(_Model):
    decision_id: str
    action_id: str
    effect: Effect
    rule_ids: list[RuleId] = Field(default_factory=list)
    reason_code: ReasonCode
    summary_plain: str
    evidence: list[Evidence] = Field(default_factory=list)
    latency_ms: float = 0.0
    # What the agent is told, when it differs from what the officer reads. A refusal must not coach a compromised agent:
    # it never says how many values matched or of which kinds (plan Q3; the ARM finding on denial feedback).
    agent_summary: str | None = None


# ---- events ------------------------------------------------------------------------------------
class EventEnvelope(_Model):
    type: str
    session_id: str | None
    column: Column | None
    ts: datetime
    payload: dict[str, Any] = Field(default_factory=dict)
