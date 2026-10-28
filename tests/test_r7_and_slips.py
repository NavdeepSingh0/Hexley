"""R7 (untrusted content, then a consequential action), internal destinations, and the slip builder, end to end.

The scenario behind all of it: an officer defines THEIR OWN task, the agent reads a document nobody has vetted, and the document
tries to steer it. Sentinel never reads the document's meaning; it limits what the agent can then DO."""

import asyncio
import time

import pytest

from sentinel.contracts import SlipError, draft_custom
from sentinel.registry import load_registry

MANAGER = "manager@corp.example"
SLIP = {"objective": "Summarise the vendor's document and email the summary to my manager",
        "allowed_tools": ["read_quotation", "query_stock", "send_email"], "allowed_destinations": ["corp.example"],
        "internal_destinations": [MANAGER], "max_messages": 5, "ttl_seconds": 900}


@pytest.fixture
def short_wait(stack, monkeypatch):
    monkeypatch.setattr(stack.rt, "approval_wait", 0.5)


async def new_slip(stack, **over) -> dict:
    async with stack.api() as api:
        r = await api.post("/api/v1/slips", json={**SLIP, **over, "confirm": True})
        assert r.status_code == 201, r.text
        return r.json()


def client_for(stack, slip: dict):
    return stack.client(slip["header_value"].removeprefix("Bearer "))


def mail(to: str, body: str = "Summary: the vendor quotes two items.") -> dict:
    return {"to": to, "subject": "Summary", "body": body}


def decisions(stack, sid: str) -> list[dict]:
    return [e.payload for e in stack.rt.bus.recent() if e.session_id == sid and e.type == "decision"]


def delivered(stack, sid: str) -> list[dict]:
    return [m for m in stack.sink.snapshot() if m["session_id"] == sid]


async def attempt(c, tool: str, args: dict) -> str | None:
    try:
        await c.call_tool(tool, args)
    except Exception as e:  # noqa: BLE001
        return str(e)
    return None


async def pending_for(stack, sid: str, timeout: float = 5.0):
    t0 = time.monotonic()
    while True:
        found = [a for a in stack.rt.approvals.pending() if a.session_id == sid]
        if found:
            return found[0]
        if time.monotonic() - t0 > timeout:
            raise AssertionError("no approval was requested")
        await asyncio.sleep(0.02)


# ---- the slip builder -------------------------------------------------------------------------------------------
async def test_a_custom_slip_is_confirmed_and_gives_a_working_token(stack):
    slip = await new_slip(stack)
    assert slip["confirmed"] and slip["slip"]["internal_destinations"] == [MANAGER] and slip["header_value"].startswith("Bearer ")
    async with client_for(stack, slip) as c:
        assert {t.name for t in await c.list_tools()} == {"read_quotation", "query_stock", "send_email"}


async def test_a_custom_slip_can_be_confirmed_in_a_second_step(stack):
    async with stack.api() as api:
        draft = (await api.post("/api/v1/slips", json=SLIP)).json()
        assert draft["confirmed"] is False and "header_value" not in draft
        done = (await api.post(f"/tasks/{draft['contract_id']}/confirm", json={"column": "sentinel"})).json()
    async with stack.client(done["session_token"]) as c:
        assert len(await c.list_tools()) == 3
    assert stack.rt.store.get(done["session_id"]).contract.contract_hash == draft["contract_hash"]


@pytest.mark.parametrize("over,message", [
    ({"allowed_tools": ["read_quotation", "no_such_tool"]}, "not a classified tool"),
    ({"allowed_tools": ["send_quote_ack"]}, "hardened slip"),
    ({"allowed_tools": []}, "between 1 and 20"),
    ({"allowed_destinations": [], "internal_destinations": []}, "send data outside"),
    ({"max_messages": 0}, "message limit of at least 1"),
    ({"internal_destinations": ["boss@elsewhere.example"]}, "subset"),
    ({"allowed_destinations": ["*.corp.example"]}, "not a valid destination"),
    ({"allowed_destinations": ["https://corp.example/x"]}, "not a valid destination"),
    ({"objective": "hi"}, "5 to 500"),
    ({"ttl_seconds": 5}, "between 1 minute and 24 hours"),
    ({"max_messages": 99}, "between 0 and 50"),
])
async def test_vague_or_contradictory_slips_are_refused_with_a_plain_message(stack, over, message):
    async with stack.api() as api:
        r = await api.post("/api/v1/slips", json={**SLIP, **over})
        assert r.status_code == 422 and message in r.json()["detail"], r.text


async def test_the_slip_builder_needs_the_api_token_and_rejects_unknown_fields(stack):
    import httpx

    async with httpx.AsyncClient(base_url=stack.api_url) as anon:
        assert (await anon.post("/api/v1/slips", json=SLIP)).status_code == 401
    async with stack.api() as api:
        assert (await api.post("/api/v1/slips", json={**SLIP, "mode": "hardened"})).status_code == 422


def test_what_the_officer_chose_is_part_of_the_contract_hash():
    reg = load_registry()
    kw = dict(objective="Summarise and send to my manager", allowed_tools=["read_quotation", "send_email"],
              allowed_destinations=["corp.example"], officer="x")
    a = draft_custom(reg, internal_destinations=[MANAGER], **kw)
    b = draft_custom(reg, internal_destinations=[], **kw)
    c = draft_custom(reg, internal_destinations=[MANAGER], **{**kw, "allowed_destinations": ["corp.example", "other.example"]})
    assert len({a.contract_hash, b.contract_hash, c.contract_hash}) == 3
    with pytest.raises(SlipError):
        draft_custom(reg, internal_destinations=["x@elsewhere.example"], **kw)


# ---- R7 and internal destinations ---------------------------------------------------------------------------------
async def test_after_reading_untrusted_content_a_send_to_a_named_internal_destination_needs_no_question(stack):
    slip = await new_slip(stack)
    async with client_for(stack, slip) as c:
        await c.call_tool("read_quotation", {"quote_id": "Q-1043"})  # the poisoned quotation: untrusted content
        assert await attempt(c, "send_email", mail(MANAGER)) is None
    sid = stack.rt.store.sessions and [s for s in stack.rt.store.sessions if stack.rt.store.sessions[s].contract.contract_hash == slip["contract_hash"]][0]
    assert len(delivered(stack, sid)) == 1 and {d["effect"] for d in decisions(stack, sid)} == {"ALLOW"}


async def test_after_untrusted_content_another_address_on_the_allowed_domain_waits_for_the_officer(stack):
    """The agent was steered towards accounts@corp.example. It is inside the allowed domain, so R1 lets it through and R3
    never saw the address in a document: only R7 stops it, and only a human can say yes."""
    slip = await new_slip(stack)
    sid = slip["session_id"]
    async with client_for(stack, slip) as c:
        await c.call_tool("read_quotation", {"quote_id": "Q-1043"})
        task = asyncio.create_task(attempt(c, "send_email", mail("accounts@corp.example")))
        approval = await pending_for(stack, sid)
        assert delivered(stack, sid) == []  # nothing left while it is held
        stack.rt.approvals.resolve(approval.approval_id, True)
        assert await task is None
        # the approval was for exactly that call and is used up: the same call asks again
        again = asyncio.create_task(attempt(c, "send_email", mail("accounts@corp.example")))
        second = await pending_for(stack, sid)
        assert second.approval_id != approval.approval_id
        stack.rt.approvals.resolve(second.approval_id, False)
        assert "did not approve" in (await again)
    asked = [d for d in decisions(stack, sid) if d["effect"] == "ASK"]
    assert [d["rule_ids"] for d in asked] == [["R7"], ["R7"]] and asked[0]["reason_code"] == "TAINTED_ACTION"
    assert len(delivered(stack, sid)) == 1  # only the approved one


async def test_without_reading_anything_untrusted_no_question_is_asked(stack):
    slip = await new_slip(stack)
    async with client_for(stack, slip) as c:
        assert await attempt(c, "send_email", mail("accounts@corp.example")) is None
    assert {d["effect"] for d in decisions(stack, slip["session_id"])} == {"ALLOW"}


async def test_a_read_only_tool_after_untrusted_content_never_asks(stack):
    slip = await new_slip(stack)
    async with client_for(stack, slip) as c:
        await c.call_tool("read_quotation", {"quote_id": "Q-1043"})
        await c.call_tool("query_stock", {"item": "all"})
    assert {d["effect"] for d in decisions(stack, slip["session_id"])} == {"ALLOW"}


async def test_a_destination_outside_the_slip_is_blocked_by_r1_and_r7_stays_quiet(stack):
    slip = await new_slip(stack)
    async with client_for(stack, slip) as c:
        await c.call_tool("read_quotation", {"quote_id": "Q-1043"})
        err = await attempt(c, "send_email", mail("attacker@evil.example"))
    assert err is not None and err.startswith("Blocked")
    last = decisions(stack, slip["session_id"])[-1]
    assert last["effect"] == "BLOCK" and last["rule_ids"] == ["R1"]  # a block outranks a question: R7 does not pile on


async def test_restricted_data_may_go_to_an_internal_destination_but_nowhere_else(stack, short_wait):
    slip = await new_slip(stack, internal_destinations=[MANAGER])
    sid = slip["session_id"]
    body = "Stock: 2,400 units at depot FSD-14, next dispatch 2 November 2026."
    async with client_for(stack, slip) as c:
        await c.call_tool("query_stock", {"item": "all"})  # restricted data enters the session
        assert await attempt(c, "send_email", mail(MANAGER, body)) is None  # named as internal: R2 does not apply
        err = await attempt(c, "send_email", mail("someone-else@corp.example", body))  # allowed domain, not internal
    assert err is not None and err.startswith("Blocked")
    last = decisions(stack, sid)[-1]
    assert last["effect"] == "BLOCK" and last["rule_ids"] == ["R2"]
    assert [m["to"] for m in delivered(stack, sid)] == [MANAGER]


async def test_with_no_internal_destinations_restricted_data_goes_nowhere(stack):
    slip = await new_slip(stack, internal_destinations=[])
    async with client_for(stack, slip) as c:
        await c.call_tool("query_stock", {"item": "all"})
        err = await attempt(c, "send_email", mail(MANAGER, "We hold 2,400 units at FSD-14."))
    assert err is not None and err.startswith("Blocked") and delivered(stack, slip["session_id"]) == []


async def test_a_consequential_tool_with_no_destination_asks_after_untrusted_content_on_top_of_r4(stack, short_wait):
    slip = await new_slip(stack, allowed_tools=["read_quotation", "update_vendor_bank"], allowed_destinations=[],
                          internal_destinations=[], max_messages=0)
    sid = slip["session_id"]
    change = {"vendor": "shakti", "account_number": "111-222-333"}
    async with client_for(stack, slip) as c:
        # before anything untrusted was read, only R4 (the bank-detail rule) asks
        first = asyncio.create_task(attempt(c, "update_vendor_bank", change))
        a1 = await pending_for(stack, sid)
        stack.rt.approvals.resolve(a1.approval_id, False)
        await first
        await c.call_tool("read_quotation", {"quote_id": "Q-1043"})
        second = asyncio.create_task(attempt(c, "update_vendor_bank", {**change, "account_number": "999-888-777"}))
        a2 = await pending_for(stack, sid)
        stack.rt.approvals.resolve(a2.approval_id, False)
        await second
    asks = [d for d in decisions(stack, sid) if d["effect"] == "ASK"]
    assert asks[0]["rule_ids"] == ["R4"] and sorted(asks[1]["rule_ids"]) == ["R4", "R7"]


def test_an_address_that_is_the_recipient_is_not_a_leak_of_itself_but_other_confidential_values_still_are():
    """Confidential data containing e-mail addresses (a customer list): writing TO a customer must work, while repeating
    that customer's private details to anyone is still caught."""
    from datetime import datetime, timezone

    from sentinel.contracts import Session, SessionClaims
    from sentinel.engine import decide
    from sentinel.models import AgentAction, Column, Effect, SessionStatus

    reg = load_registry()
    now = datetime(2026, 10, 27, 10, 0, tzinfo=timezone.utc)
    contract = draft_custom(reg, objective="Reply to customers about their accounts", allowed_tools=["send_email"],
                            allowed_destinations=["client.example"], max_messages=5, officer="x", now=now)
    contract = contract.model_copy(update={"status": SessionStatus.ACTIVE})
    session = Session(claims=SessionClaims("ses_t", contract.contract_id, contract.compute_hash(), Column.SENTINEL, now),
                      contract=contract)
    session.index.add("Customer priya.nair@client.example, phone +91 98765 43210, owes 48,500 rupees", ["all"], "query_customers")

    def send(to, body):
        entry = reg.get("send_email")
        return decide(AgentAction(action_id="a", ts=now, session_id="ses_t", contract_id=contract.contract_id,
                                  column=Column.SENTINEL, tool="send_email", capability=entry.capability,
                                  resource_class=entry.resource_class, args={"to": to, "subject": "s", "body": body},
                                  outbound=True), session, reg)

    assert send("priya.nair@client.example", "Hello Priya, thanks for getting in touch.").effect == Effect.ALLOW
    leak = send("priya.nair@client.example", "Hello Priya, you owe 48,500 rupees and your phone is 9876543210.")
    assert leak.effect == Effect.BLOCK and leak.rule_ids == ["R2"]
    assert send("rahul@client.example", "Please write to priya.nair@client.example about her account.").effect == Effect.BLOCK


async def test_the_quotation_flow_is_not_disturbed_by_r7(stack):
    """The reply to the vendor on file, after reading the (untrusted) quotation, must still go straight through."""
    s = await stack.start_session(column="sentinel")
    async with stack.client(s["session_token"]) as c:
        await c.call_tool("read_quotation", {"quote_id": "Q-1042"})
        assert await attempt(c, "send_email", {"to": "sales@shakti.example", "subject": "Re", "body": "Quotation received."}) is None
    assert {d["effect"] for d in decisions(stack, s["session_id"])} == {"ALLOW"}


async def test_the_r1_only_and_unprotected_columns_run_no_r7(stack):
    for column in ("r1_only", "unprotected"):
        s = await stack.start_session(column=column)
        async with stack.client(s["session_token"]) as c:
            await c.call_tool("read_quotation", {"quote_id": "Q-1044"})
            assert await attempt(c, "send_email", {"to": "audit-desk@shakti.example", "subject": "s", "body": "b"}) is None
        assert not any(d["effect"] == "ASK" for d in decisions(stack, s["session_id"]))
