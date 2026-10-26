"""Rules R1-R6 as pure functions: no I/O, no clock, no randomness, no LLM (invariant 1).

R1 (M1) and R2 (M2) exist so far; R3-R6 and structured egress follow in M2.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .matcher import Match
from .models import EFFECT_PRECEDENCE, AgentAction, Effect, Evidence, ReasonCode, RuleId, TaskContract, ToolEntry


@dataclass(frozen=True)
class RuleResult:
    rule_id: RuleId
    effect: Effect
    reason_code: ReasonCode
    summary: str
    evidence: list[Evidence] = field(default_factory=list)


def rule_r1(action: AgentAction, contract: TaskContract, entry: ToolEntry) -> RuleResult | None:
    """R1: the action must be inside the permission slip, and its tool must be in the registry."""
    if not entry.known:
        return RuleResult(
            RuleId.R1, Effect.BLOCK, ReasonCode.NOT_IN_REGISTRY,
            f"Blocked: '{action.tool}' is not a registered tool, so Sentinel will not run it. "
            "Unknown tools are treated as untrusted.",
            [Evidence(kind="registry", detail=f"tool '{action.tool}' is not in the tool registry")])
    if action.tool not in contract.allowed_tools:
        allowed = ", ".join(contract.allowed_tools) or "nothing"
        return RuleResult(
            RuleId.R1, Effect.BLOCK, ReasonCode.NOT_IN_SLIP,
            f"Blocked: '{action.tool}' is not part of this task's permission slip. "
            f"The slip for \"{contract.objective}\" allows: {allowed}.",
            [Evidence(kind="slip", detail=f"'{action.tool}' is not in allowed_tools",
                      source_ref=contract.contract_id)])
    return None


_KIND_LABEL = {"number": "quantity", "code": "depot code", "date": "date"}


def rule_r2(action: AgentAction, entry: ToolEntry, matches: list[Match]) -> RuleResult | None:
    """R2: restricted values this session has read must not appear in anything leaving the building.

    The agent-facing summary never repeats the values (the agent would simply re-send them in another
    form); the evidence, which goes to the console and the audit log, does."""
    if not entry.outbound or not matches:
        return None
    labels = sorted({_KIND_LABEL.get(m.kind, m.kind) for m in matches})
    sources = sorted({m.source_ref for m in matches})
    evidence = [Evidence(kind="fingerprint",
                         detail=f"{_KIND_LABEL.get(m.kind, m.kind)} from {m.source_ref} found in argument '{m.path or action.tool}'",
                         matched_tokens=[m.snippet], source_ref=m.source_ref) for m in matches]
    return RuleResult(
        RuleId.R2, Effect.BLOCK, ReasonCode.SECRET_EGRESS,
        f"Blocked: this {action.tool} would send {len(matches)} restricted value(s) "
        f"({', '.join(labels)}) read from {', '.join(sources)} outside the building. "
        "This task's permission slip does not allow restricted data to leave. "
        "Send an acknowledgement without that information.",
        evidence)


FREEZE_AFTER_BLOCKS = 3


def rule_r5(action: AgentAction, entry: ToolEntry, contract: TaskContract, messages_out: int) -> RuleResult | None:
    """R5: outgoing messages stay within the slip's send budget. `messages_out` counts messages already
    allowed (reserved) in this session; a blocked attempt does not use any of the budget."""
    if not entry.outbound or messages_out < contract.max_messages:
        return None
    n = contract.max_messages
    return RuleResult(
        RuleId.R5, Effect.BLOCK, ReasonCode.VOLUME_EXCEEDED,
        f"Blocked: this task's permission slip allows {n} outgoing message{'s' if n != 1 else ''} and "
        f"{'that limit' if n == 1 else 'the limit'} has already been used.",
        [Evidence(kind="budget", detail=f"{messages_out} of {n} outgoing messages already used",
                  source_ref=contract.contract_id)])


def rule_r6(blocks_including_this: int, threshold: int = FREEZE_AFTER_BLOCKS) -> RuleResult | None:
    """R6: the third policy block in one session freezes it. Evaluated only when another rule already blocked."""
    if blocks_including_this < threshold:
        return None
    return RuleResult(
        RuleId.R6, Effect.FREEZE, ReasonCode.BLOCK_THRESHOLD_FREEZE,
        f"Frozen: this session made {blocks_including_this} blocked attempts and has been quarantined. "
        "No further actions are possible until the officer confirms a new permission slip.",
        [Evidence(kind="counter", detail=f"{blocks_including_this} policy blocks in this session")])


def combine(results: list[RuleResult]) -> RuleResult | None:
    """Pick the strongest verdict by precedence FREEZE > BLOCK > ASK > ALLOW. None when nothing fired."""
    for effect in EFFECT_PRECEDENCE:
        for r in results:
            if r.effect == effect:
                return r
    return None
