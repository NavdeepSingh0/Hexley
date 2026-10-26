"""R4: a held call needs the officer's approval of THIS exact action. Matrix row 25 (approval substitution).

The agent's call is held while the officer decides. Approval is bound to a hash of session + tool + arguments,
is one-time, and expires; silence, denial and expiry all end as a BLOCK with no side effect.
"""

import asyncio
import time

import httpx
import pytest

from sentinel import fixtures, rules
from sentinel.contracts import Session, SessionClaims, draft_contract, load_templates
from sentinel.engine import decide
from sentinel.models import AgentAction, Column, Effect, ReasonCode, RuleId, SessionStatus
from sentinel.registry import Registry, load_registry
from tests.conftest import API_TOKEN

CHANGE_111 = {"vendor": "shakti", "account_number": "111-222-333"}
CHANGE_999 = {"vendor": "shakti", "account_number": "999-888-777"}


@pytest.fixture()
async def short_wait(stack):
    saved = stack.rt.approval_wait
    stack.rt.approval_wait = 1.5
    yield
    stack.rt.approval_wait = saved


@pytest.fixture()
async def api(stack):
    async with httpx.AsyncClient(base_url=stack.api_url, headers={"Authorization": f"Bearer {API_TOKEN}"}) as c:
        yield c


def changes(stack, sid):
    return [c for c in stack.sink.bank_changes if c["session_id"] == sid]


async def pending_for(stack, sid, n=1, timeout=3.0):
    t0 = time.monotonic()
    while True:
        found = [a for a in stack.rt.approvals.pending() if a.session_id == sid]
        if len(found) >= n:
            return found
        if time.monotonic() - t0 > timeout:
            raise AssertionError(f"expected {n} pending approval(s), saw {len(found)}")
        await asyncio.sleep(0.02)


async def attempt(c, args):
    try:
        await c.call_tool("update_vendor_bank", args)
        return None
    except Exception as e:  # noqa: BLE001
        return str(e)


async def decide_via_api(api, approval, decision):
    return await api.post(f"/approvals/{approval.approval_id}", json={"decision": decision})


# ---- the basic flow ------------------------------------------------------------------------------------------
async def test_a_bank_change_is_held_until_the_officer_approves_then_runs_once(stack, api, short_wait):
    s = await stack.start_session(template="vendor_maintenance")
    async with stack.client(s["session_token"]) as c:
        task = asyncio.create_task(attempt(c, CHANGE_111))
        (a,) = await pending_for(stack, s["session_id"])
        assert changes(stack, s["session_id"]) == []  # nothing happened while it is held
        assert (await decide_via_api(api, a, "approve")).status_code == 200
        assert await task is None
    assert [x["account_number"] for x in changes(stack, s["session_id"])] == ["111-222-333"]
    decisions = [e.payload for e in stack.rt.bus.recent() if e.session_id == s["session_id"] and e.type == "decision"]
    assert [d["effect"] for d in decisions] == ["ASK", "ALLOW"]
    assert any(ev["kind"] == "approval" for ev in decisions[-1]["evidence"])
    types = [e.type for e in stack.rt.bus.recent() if e.session_id == s["session_id"]]
    assert "approval.pending" in types and "approval.resolved" in types


async def test_denial_blocks_with_no_side_effect(stack, api, short_wait):
    s = await stack.start_session(template="vendor_maintenance")
    async with stack.client(s["session_token"]) as c:
        task = asyncio.create_task(attempt(c, CHANGE_111))
        (a,) = await pending_for(stack, s["session_id"])
        await decide_via_api(api, a, "deny")
        err = await task
    assert err is not None and err.startswith("Blocked") and "did not approve" in err
    assert changes(stack, s["session_id"]) == []
    assert stack.rt.store.get(s["session_id"]).blocks == 1  # a refusal counts as a block


async def test_silence_is_a_denial(stack, short_wait):
    stack.rt.approval_wait = 0.3
    s = await stack.start_session(template="vendor_maintenance")
    async with stack.client(s["session_token"]) as c:
        err = await attempt(c, CHANGE_111)
    assert err is not None and "no approval arrived in time" in err
    assert changes(stack, s["session_id"]) == []


async def test_the_held_call_does_not_block_the_rest_of_the_session(stack, api, short_wait):
    s = await stack.start_session(template="vendor_maintenance")
    async with stack.client(s["session_token"]) as c:
        task = asyncio.create_task(attempt(c, CHANGE_111))
        (a,) = await pending_for(stack, s["session_id"])
        await c.call_tool("send_email", {"to": fixtures.VENDOR, "subject": "s", "body": "hello"})  # still works
        await decide_via_api(api, a, "deny")
        await task
    assert len([m for m in stack.sink.snapshot() if m["session_id"] == s["session_id"]]) == 1


# ---- matrix row 25: approval substitution -----------------------------------------------------------------------
async def test_row_25_approving_one_payload_does_not_release_another(stack, api, short_wait):
    s = await stack.start_session(template="vendor_maintenance")
    async with stack.client(s["session_token"]) as c:
        a_task = asyncio.create_task(attempt(c, CHANGE_111))
        (a,) = await pending_for(stack, s["session_id"])
        b_task = asyncio.create_task(attempt(c, CHANGE_999))  # the agent tries a different account number
        a_b = await pending_for(stack, s["session_id"], n=2)
        b = next(x for x in a_b if x.approval_id != a.approval_id)
        assert a.action_hash != b.action_hash
        await decide_via_api(api, a, "approve")  # the officer approved the FIRST one only
        assert await a_task is None
        err_b = await b_task  # the second is still waiting for its own approval, and times out
    assert err_b is not None and err_b.startswith("Blocked")
    assert [x["account_number"] for x in changes(stack, s["session_id"])] == ["111-222-333"]  # never 999


async def test_an_approval_is_one_time_the_same_call_again_needs_a_new_one(stack, api, short_wait):
    s = await stack.start_session(template="vendor_maintenance")
    async with stack.client(s["session_token"]) as c:
        first = asyncio.create_task(attempt(c, CHANGE_111))
        (a,) = await pending_for(stack, s["session_id"])
        await decide_via_api(api, a, "approve")
        assert await first is None
        again = asyncio.create_task(attempt(c, CHANGE_111))  # identical call
        (b,) = [x for x in await pending_for(stack, s["session_id"]) if x.approval_id != a.approval_id]
        await decide_via_api(api, b, "deny")
        assert (await again) is not None
    assert len(changes(stack, s["session_id"])) == 1


async def test_an_approval_does_not_carry_over_to_another_session(stack, api, short_wait):
    one = await stack.start_session(template="vendor_maintenance")
    two = await stack.start_session(template="vendor_maintenance")
    async with stack.client(one["session_token"]) as c1, stack.client(two["session_token"]) as c2:
        t1 = asyncio.create_task(attempt(c1, CHANGE_111))
        (a1,) = await pending_for(stack, one["session_id"])
        await decide_via_api(api, a1, "approve")
        assert await t1 is None
        t2 = asyncio.create_task(attempt(c2, CHANGE_111))  # the same call in another session
        (a2,) = await pending_for(stack, two["session_id"])
        assert a2.approval_id != a1.approval_id
        await decide_via_api(api, a2, "deny")
        await t2
    assert changes(stack, two["session_id"]) == []


async def test_an_expired_approval_cannot_be_used(stack, api, short_wait):
    s = await stack.start_session(template="vendor_maintenance")
    async with stack.client(s["session_token"]) as c:
        task = asyncio.create_task(attempt(c, CHANGE_111))
        (a,) = await pending_for(stack, s["session_id"])
        await decide_via_api(api, a, "approve")
        await task
        a.expires = time.time() - 1  # the approval has since expired
        assert stack.rt.approvals.peek_granted(a.action_hash) is None


# ---- approval never excuses another rule -------------------------------------------------------------------------
def test_an_approved_action_still_has_to_pass_every_other_rule():
    """Engine level: even with the officer's approval, a leak is blocked by R2."""
    reg = load_registry()
    tools = dict(reg._tools)
    tools["send_email"] = tools["send_email"].model_copy(update={"requires_human_verification": True})
    strict = Registry(tools, reg._default)
    c = draft_contract(load_templates(), "quotation_processing", "x").model_copy(update={"status": SessionStatus.ACTIVE})
    s = Session(claims=SessionClaims("ses_x", c.contract_id, c.compute_hash(), Column.SENTINEL, c.expires_at), contract=c)
    s.index.add(fixtures.STOCK_REGISTER, ["quantity", "depot_code", "dispatch_date"], source_ref="query_stock")
    e = strict.get("send_email")
    leak = AgentAction(action_id="a", ts=c.issued_at, session_id="ses_x", contract_id=c.contract_id, column=Column.SENTINEL,
                       tool="send_email", capability=e.capability, resource_class=e.resource_class, outbound=True,
                       args={"to": fixtures.VENDOR, "subject": "s", "body": "stock 2400 at FSD-14"})
    asked = decide(leak, s, strict, approved=False)
    approved = decide(leak, s, strict, approved=True)
    assert asked.effect == Effect.BLOCK and RuleId.R2 in asked.rule_ids  # BLOCK outranks ASK: a human is not asked
    assert approved.effect == Effect.BLOCK and approved.reason_code == ReasonCode.SECRET_EGRESS


def test_rule_r4_is_silent_once_approved_and_for_unmarked_tools():
    reg = load_registry()
    e = reg.get("update_vendor_bank")
    a = AgentAction(action_id="a", ts=draft_contract(load_templates(), "vendor_maintenance", "x").issued_at,
                    session_id="s", contract_id="c", column=Column.SENTINEL, tool="update_vendor_bank",
                    capability=e.capability, resource_class=e.resource_class, args={})
    assert rules.rule_r4(a, e, approved=False).effect == Effect.ASK
    assert rules.rule_r4(a, e, approved=True) is None
    assert rules.rule_r4(a, reg.get("read_quotation"), approved=False) is None


async def test_the_baseline_columns_make_the_bank_change_with_no_approval(stack):
    for column in ("unprotected", "r1_only"):
        s = await stack.start_session(column=column, template="vendor_maintenance")
        async with stack.client(s["session_token"]) as c:
            assert await attempt(c, CHANGE_999) is None
        assert len(changes(stack, s["session_id"])) == 1


# ---- the approval API ---------------------------------------------------------------------------------------------
async def test_approval_endpoints_need_the_token_and_report_errors(stack, api, short_wait):
    async with httpx.AsyncClient(base_url=stack.api_url) as anon:
        assert (await anon.get("/approvals")).status_code == 401
        assert (await anon.post("/approvals/apr_x", json={"decision": "approve"})).status_code == 401
    assert (await api.get("/approvals/apr_missing")).status_code == 404
    assert (await api.post("/approvals/apr_missing", json={"decision": "approve"})).status_code == 404
    s = await stack.start_session(template="vendor_maintenance")
    async with stack.client(s["session_token"]) as c:
        task = asyncio.create_task(attempt(c, CHANGE_111))
        (a,) = await pending_for(stack, s["session_id"])
        card = (await api.get(f"/approvals/{a.approval_id}")).json()
        assert card["tool"] == "update_vendor_bank" and card["args"]["account_number"] == "111-222-333"
        assert any(p["approval_id"] == a.approval_id for p in (await api.get("/approvals")).json()["pending"])
        assert (await api.post(f"/approvals/{a.approval_id}", json={"decision": "maybe"})).status_code == 422
        assert (await decide_via_api(api, a, "deny")).status_code == 200
        assert (await decide_via_api(api, a, "approve")).status_code == 409  # cannot flip a decision
        await task


async def test_an_approval_cannot_take_effect_unless_it_is_recorded(stack, api, short_wait):
    s = await stack.start_session(template="vendor_maintenance")
    async with stack.client(s["session_token"]) as c:
        task = asyncio.create_task(attempt(c, CHANGE_111))
        (a,) = await pending_for(stack, s["session_id"])
        log = stack.rt.audit
        original = log._write_line
        log._write_line = lambda line: (_ for _ in ()).throw(OSError("disk gone"))
        try:
            assert (await decide_via_api(api, a, "approve")).status_code == 503  # the approval did not take effect
        finally:
            log._write_line = original
            await log.recover()
        assert stack.rt.approvals.get(a.approval_id).status.value == "pending"
        await decide_via_api(api, a, "deny")
        await task
    assert changes(stack, s["session_id"]) == []
