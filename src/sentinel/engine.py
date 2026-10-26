"""decide(): one action in, one Decision out. Any failure inside a protected column means BLOCK."""

from __future__ import annotations

import logging
import time
import uuid

from . import rules
from .contracts import Session
from .models import AgentAction, Column, Decision, Effect, ReasonCode, RuleId
from .registry import Registry

log = logging.getLogger("sentinel.engine")


def _new_id() -> str:
    return f"dec_{uuid.uuid4().hex[:12]}"


def decide(action: AgentAction, session: Session, registry: Registry) -> Decision:
    t0 = time.perf_counter()

    def finish(**kw) -> Decision:
        return Decision(decision_id=_new_id(), action_id=action.action_id,
                        latency_ms=round((time.perf_counter() - t0) * 1000, 3), **kw)

    if session.column == Column.UNPROTECTED:
        # The baseline column runs no rules at all. It is labelled as such on screen.
        return finish(effect=Effect.ALLOW, reason_code=ReasonCode.NOT_ENFORCED,
                      summary_plain="Allowed: no policy enforcement in this column (instrumented baseline).")
    try:
        entry = registry.get(action.tool)
        fired = [r for r in (rules.rule_r1(action, session.contract, entry),) if r is not None]
        verdict = rules.combine(fired)
        if verdict is None:
            return finish(effect=Effect.ALLOW, reason_code=ReasonCode.ALLOWED,
                          summary_plain=f"Allowed: '{action.tool}' is within this task's permission slip.")
        return finish(effect=verdict.effect, rule_ids=[verdict.rule_id], reason_code=verdict.reason_code,
                      summary_plain=verdict.summary, evidence=verdict.evidence)
    except Exception:  # noqa: BLE001 - invariant 2: any error in the decision path is a BLOCK
        log.exception("decision failed; failing closed")
        return finish(effect=Effect.BLOCK, rule_ids=[RuleId.R1], reason_code=ReasonCode.FAIL_CLOSED,
                      summary_plain="Blocked: Sentinel could not evaluate this action safely, so it did not run.")
