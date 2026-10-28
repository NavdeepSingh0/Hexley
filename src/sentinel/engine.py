"""decide(): one action in, one Decision out. Any failure inside a protected column means BLOCK."""

from __future__ import annotations

import logging
import time
import uuid

from . import destinations, egress, rules
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
        recipients, unparseable = destinations.keys_in(
            [action.args[k] for k in entry.destination_args if k in action.args],
            entry.destination_kind) if entry.outbound else ([], [])
        results = [rules.rule_r1(action, session.contract, entry),
                   rules.rule_r1_recipient(action, entry, session.contract, recipients, unparseable),
                   rules.rule_r1_egress(action, entry, session.contract)]
        if session.column == Column.SENTINEL:  # the R1-only baseline runs R1 and nothing else
            matches = session.index.scan_args(action.args) if entry.outbound else []
            # An address that IS the recipient is not a leak of itself (you may write to a customer who is in the database).
            matches = [m for m in matches if not (m.kind == "email" and m.canonical in recipients)]
            if recipients and not unparseable and all(
                    destinations.allowed(r, session.contract.internal_destinations) for r in recipients):
                matches = []  # restricted data may go to a destination the officer named as internal (the slip says so)
            results.append(rules.rule_r2(action, entry, matches))
            results.append(rules.rule_r3(action, entry, recipients, session.untrusted_destinations,
                                         session.trusted_addresses))
            results.append(rules.rule_r4(action, entry, approved))
            results.append(rules.rule_r5(action, entry, session.contract, session.messages_out))
            if not any(r is not None and r.effect == Effect.BLOCK for r in results):
                # R7 asks only when nothing else has already said no: a block outranks a question, and the evidence of
                # the blocking rule (not a second, redundant question) is what the officer and the log should see.
                results.append(rules.rule_r7(action, entry, session.tainted_by, recipients, session.contract,
                                             session.trusted_addresses, approved))
        fired = [r for r in results if r is not None]
        verdict = rules.combine(fired)
        if verdict is not None and verdict.effect == Effect.BLOCK and session.column == Column.SENTINEL:
            freeze = rules.rule_r6(session.blocks + 1)  # this block would be the Nth
            if freeze is not None:
                fired.append(freeze)
                verdict = rules.combine(fired)
        if verdict is None:
            if approved:
                # `approved` is True only when the officer approved THIS exact call, which was asked for because R4 or R7
                # fired; every other rule has just run and found nothing.
                return finish(effect=Effect.ALLOW, reason_code=ReasonCode.ALLOWED,
                              summary_plain=f"Allowed: the officer approved this exact '{action.tool}' request.",
                              evidence=[Evidence(kind="approval", detail="the officer approved this exact action",
                                                 source_ref=action.tool)])
            if entry.egress_template is not None:
                # Record the exact message before anything is sent; the gateway re-renders at send time and
                # refuses to send if the hash differs (D-020).
                msg = egress.render(egress.find_template(session.contract, entry.egress_template),
                                    action.args, session.contract)
                return finish(effect=Effect.ALLOW, reason_code=ReasonCode.ALLOWED,
                              summary_plain=f"Allowed: Sentinel will send its fixed acknowledgement to the vendor "
                                            f"resolved for this work item ({msg.to}).",
                              evidence=[Evidence(kind="egress", detail=f"fixed message rendered for {msg.to}",
                                                 source_ref=msg.message_sha256)])
            return finish(effect=Effect.ALLOW, reason_code=ReasonCode.ALLOWED,
                          summary_plain=f"Allowed: '{action.tool}' is within this task's permission slip.")
        return finish(effect=verdict.effect, rule_ids=[r.rule_id for r in fired], reason_code=verdict.reason_code,
                      summary_plain=verdict.summary, evidence=[e for r in fired for e in r.evidence])
    except Exception:  # noqa: BLE001 - invariant 2: any error in the decision path is a BLOCK
        log.exception("decision failed; failing closed")
        return finish(effect=Effect.BLOCK, rule_ids=[RuleId.R1], reason_code=ReasonCode.FAIL_CLOSED,
                      summary_plain="Blocked: Sentinel could not evaluate this action safely, so it did not run.")
