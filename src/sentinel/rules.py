"""Rules R1-R6 as pure functions: no I/O, no clock, no randomness, no LLM (invariant 1).

Only R1 exists in M1. R2-R6 arrive in M2 together with the matcher and egress validation.
"""

from __future__ import annotations

from dataclasses import dataclass, field

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


def combine(results: list[RuleResult]) -> RuleResult | None:
    """Pick the strongest verdict by precedence FREEZE > BLOCK > ASK > ALLOW. None when nothing fired."""
    for effect in EFFECT_PRECEDENCE:
        for r in results:
            if r.effect == effect:
                return r
    return None
