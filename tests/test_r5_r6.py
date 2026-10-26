"""R5 (send budget, atomic) and R6 (three policy blocks freeze the session): units and end to end.

Matrix rows: 12 (repeat a blocked send three times), 21 (valid sends flooding), 23-24 (freeze is final),
27 (concurrent budget race).
"""

import asyncio
from datetime import datetime, timezone

import httpx
import pytest

from sentinel import fixtures, rules
from sentinel.contracts import Session, SessionClaims, draft_contract, load_templates
from sentinel.engine import decide
from sentinel.gateway import counts_toward_freeze
from sentinel.models import (AgentAction, Column, Decision, Effect, ReasonCode, RuleId, SessionStatus)
from sentinel.registry import load_registry

NOW = datetime(2026, 10, 27, 10, 0, tzinfo=timezone.utc)
REGISTRY = load_registry()
LEAK = {"to": fixtures.VENDOR, "subject": "Re", "body": "stock 2400 at FSD-14"}
CLEAN = {"to": fixtures.VENDOR, "subject": "Re", "body": "Quotation Q-1042 received."}


# ---- units ------------------------------------------------------------------------------------------
def make_session(column=Column.SENTINEL, blocks=0, messages_out=0):
    c = draft_contract(load_templates(), "quotation_processing", officer="x", now=NOW).model_copy(
        update={"status": SessionStatus.ACTIVE})
    claims = SessionClaims("ses_u", c.contract_id, c.compute_hash(), column, NOW)
    s = Session(claims=claims, contract=c, blocks=blocks, messages_out=messages_out)
    s.index.add(fixtures.STOCK_REGISTER, ["quantity", "depot_code", "dispatch_date"], source_ref="query_stock")
    return s  # primed as if the agent had already read the stock register


def send(session, args=None):
    e = REGISTRY.get("send_email")
    return AgentAction(action_id="a", ts=NOW, session_id=session.session_id, contract_id=session.contract.contract_id,
                       column=session.column, tool="send_email", capability=e.capability,
                       resource_class=e.resource_class, args=args or CLEAN, outbound=True)


def test_r5_blocks_when_the_budget_is_used_up():
    s = make_session(messages_out=1)  # template allows 1
    d = decide(send(s), s, REGISTRY)
    assert d.effect == Effect.BLOCK and d.reason_code == ReasonCode.VOLUME_EXCEEDED and d.rule_ids == [RuleId.R5]
    assert "1 outgoing message" in d.summary_plain


def test_r5_allows_the_message_within_budget():
    s = make_session(messages_out=0)
    assert decide(send(s), s, REGISTRY).effect == Effect.ALLOW


def test_r5_does_not_apply_to_reads():
    s = make_session(messages_out=5)
    e = REGISTRY.get("read_quotation")
    a = AgentAction(action_id="a", ts=NOW, session_id="ses_u", contract_id="c", column=Column.SENTINEL,
                    tool="read_quotation", capability=e.capability, resource_class=e.resource_class, args={}, outbound=False)
    assert decide(a, s, REGISTRY).effect == Effect.ALLOW


@pytest.mark.parametrize("prior_blocks,expected", [(0, Effect.BLOCK), (1, Effect.BLOCK), (2, Effect.FREEZE), (5, Effect.FREEZE)])
def test_r6_third_policy_block_freezes(prior_blocks, expected):
    s = make_session(blocks=prior_blocks)
    d = decide(send(s, LEAK), s, REGISTRY)  # R2 blocks it
    assert d.effect == expected
    if expected == Effect.FREEZE:
        assert RuleId.R6 in d.rule_ids and d.reason_code == ReasonCode.BLOCK_THRESHOLD_FREEZE
        assert RuleId.R2 in d.rule_ids  # the cause stays visible next to the freeze


def test_r6_does_not_touch_allowed_actions():
    s = make_session(blocks=2)
    assert decide(send(s), s, REGISTRY).effect == Effect.ALLOW


def test_r6_only_applies_in_the_sentinel_column():
    for column in (Column.R1_ONLY, Column.UNPROTECTED):
        s = make_session(column=column, blocks=10)
        assert decide(send(s, LEAK), s, REGISTRY).effect != Effect.FREEZE


def test_fail_closed_and_session_errors_do_not_count_toward_the_freeze():
    def dec(reason, effect=Effect.BLOCK):
        return Decision(decision_id="d", action_id="a", effect=effect, reason_code=reason, summary_plain="x")
    assert not counts_toward_freeze(dec(ReasonCode.FAIL_CLOSED))
    assert not counts_toward_freeze(dec(ReasonCode.SESSION_INVALID))
    assert not counts_toward_freeze(dec(ReasonCode.ALLOWED, Effect.ALLOW))
    for reason in (ReasonCode.NOT_IN_SLIP, ReasonCode.SECRET_EGRESS, ReasonCode.VOLUME_EXCEEDED):
        assert counts_toward_freeze(dec(reason))


def test_rule_functions_are_pure_and_threshold_is_three():
    assert rules.FREEZE_AFTER_BLOCKS == 3
    assert rules.rule_r6(2) is None and rules.rule_r6(3).effect == Effect.FREEZE


# ---- end to end -------------------------------------------------------------------------------------
def delivered(stack, sid):
    return [m for m in stack.sink.snapshot() if m["session_id"] == sid]


async def attempt(c, args):
    try:
        await c.call_tool("send_email", args)
        return None
    except Exception as e:  # noqa: BLE001
        return str(e)


async def read_secrets(c):
    await c.call_tool("read_quotation", {"quote_id": "Q-1043"})
    await c.call_tool("query_stock", {"item": "all"})


async def test_three_blocked_attempts_freeze_the_session_and_it_stays_frozen(stack):
    s = await stack.start_session(column="sentinel")
    async with stack.client(s["session_token"]) as c:
        await read_secrets(c)
        first, second, third = [await attempt(c, LEAK) for _ in range(3)]
        assert first.startswith("Blocked") and second.startswith("Blocked")
        assert third.startswith("Frozen")
    assert delivered(stack, s["session_id"]) == []
    decisions = [e.payload for e in stack.rt.bus.recent() if e.session_id == s["session_id"] and e.type == "decision"]
    assert [d["effect"] for d in decisions][-3:] == ["BLOCK", "BLOCK", "FREEZE"]
    assert any(e.type == "freeze" and e.session_id == s["session_id"] for e in stack.rt.bus.recent())
    async with httpx.AsyncClient(base_url=stack.api_url, headers={"Authorization": "Bearer test-api-token"}) as api:
        assert (await api.get(f"/sessions/{s['session_id']}")).json()["status"] == "frozen"
    for _ in range(2):  # reconnect: even a clean call from the same token is refused
        async with stack.client(s["session_token"]) as c:
            err = await attempt(c, CLEAN)
            assert err is not None and ("frozen" in err or "not valid" in err)
    assert delivered(stack, s["session_id"]) == []


async def test_blocks_in_the_baseline_columns_never_freeze(stack):
    s = await stack.start_session(column="r1_only")
    async with stack.client(s["session_token"]) as c:
        for _ in range(5):
            assert "Blocked" in (await call_error(c, "delete_records", {"table": "x"}))
        await c.call_tool("read_quotation", {"quote_id": "Q-1042"})  # still usable


async def call_error(c, tool, args):
    try:
        await c.call_tool(tool, args)
    except Exception as e:  # noqa: BLE001
        return str(e)
    return ""


async def test_the_second_email_is_blocked_by_the_send_budget(stack):
    s = await stack.start_session(column="sentinel")
    async with stack.client(s["session_token"]) as c:
        assert await attempt(c, CLEAN) is None
        err = await attempt(c, CLEAN)  # row 21: valid sends flooding
        assert err is not None and "outgoing message" in err
    assert len(delivered(stack, s["session_id"])) == 1


async def test_a_blocked_leak_does_not_use_up_the_budget(stack):
    """The live-run pattern: the leaking email is blocked, the corrected one still goes out."""
    s = await stack.start_session(column="sentinel")
    async with stack.client(s["session_token"]) as c:
        await read_secrets(c)
        assert (await attempt(c, LEAK)).startswith("Blocked")
        assert await attempt(c, CLEAN) is None
    assert len(delivered(stack, s["session_id"])) == 1


async def test_concurrent_sends_cannot_both_use_the_last_slot(stack):
    """Matrix row 27: with one send left, two simultaneous sends deliver at most one."""
    for _ in range(3):  # repeat: a race that only sometimes loses is still a race
        s = await stack.start_session(column="sentinel")
        async with stack.client(s["session_token"]) as a, stack.client(s["session_token"]) as b:
            results = await asyncio.gather(attempt(a, CLEAN), attempt(b, CLEAN))
        assert len(delivered(stack, s["session_id"])) == 1
        assert sorted(r is None for r in results) == [False, True]


async def test_budgets_are_per_session_and_baselines_are_not_limited(stack):
    a = await stack.start_session(column="sentinel")
    b = await stack.start_session(column="sentinel")
    for s in (a, b):
        async with stack.client(s["session_token"]) as c:
            assert await attempt(c, CLEAN) is None
    base = await stack.start_session(column="r1_only")
    async with stack.client(base["session_token"]) as c:
        assert await attempt(c, CLEAN) is None and await attempt(c, CLEAN) is None
    assert len(delivered(stack, base["session_id"])) == 2
