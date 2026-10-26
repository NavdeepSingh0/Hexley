"""decide(): one action in, one Decision out. Any failure inside a protected column means BLOCK."""

from __future__ import annotations

import logging
import time
import uuid

from . import destinations, rules
from .contracts import Session
from .models import AgentAction, Column, Decision, Effect, Evidence, ReasonCode, RuleId
from .registry import Registry

log = logging.getLogger("sentinel.engine")


def _new_id() -> str:
    return f"dec_{uuid.uuid4().hex[:12]}"


def decide(action: AgentAction, session: Session, registry: Registry, approved: bool = False) -> Decision:
    """`approved` is True only when the officer has approved this exact call (R4); every other rule still runs."""
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
        recipients, unparseable = destinations.recipients_in(
            [action.args[k] for k in entry.destination_args if k in action.args]) if entry.outbound else ([], [])
        results = [rules.rule_r1(action, session.contract, entry),
                   rules.rule_r1_recipient(action, entry, session.contract, recipients, unparseable)]
        if session.column == Column.SENTINEL:  # the R1-only baseline runs R1 and nothing else
            matches = session.index.scan_args(action.args) if entry.outbound else []
            results.append(rules.rule_r2(action, entry, matches))
            results.append(rules.rule_r3(action, entry, recipients, session.untrusted_destinations,
                                         session.trusted_addresses))
            results.append(rules.rule_r4(action, entry, approved))
            results.append(rules.rule_r5(action, entry, session.contract, session.messages_out))
        fired = [r for r in results if r is not None]
        verdict = rules.combine(fired)
        if verdict is not None and verdict.effect == Effect.BLOCK and session.column == Column.SENTINEL:
            freeze = rules.rule_r6(session.blocks + 1)  # this block would be the Nth
            if freeze is not None:
                fired.append(freeze)
                verdict = rules.combine(fired)
        if verdict is None:
            if approved and entry.requires_human_verification:
                return finish(effect=Effect.ALLOW, reason_code=ReasonCode.ALLOWED,
                              summary_plain=f"Allowed: the officer approved this exact '{action.tool}' request.",
                              evidence=[Evidence(kind="approval", detail="the officer approved this exact action",
                                                 source_ref=action.tool)])
            return finish(effect=Effect.ALLOW, reason_code=ReasonCode.ALLOWED,
                          summary_plain=f"Allowed: '{action.tool}' is within this task's permission slip.")
        return finish(effect=verdict.effect, rule_ids=[r.rule_id for r in fired], reason_code=verdict.reason_code,
                      summary_plain=verdict.summary, evidence=[e for r in fired for e in r.evidence])
    except Exception:  # noqa: BLE001 - invariant 2: any error in the decision path is a BLOCK
        log.exception("decision failed; failing closed")
        return finish(effect=Effect.BLOCK, rule_ids=[RuleId.R1], reason_code=ReasonCode.FAIL_CLOSED,
                      summary_plain="Blocked: Sentinel could not evaluate this action safely, so it did not run.")
