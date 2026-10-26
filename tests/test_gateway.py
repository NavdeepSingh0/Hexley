"""End-to-end gateway tests over real MCP/HTTP: agent client -> gateway -> mock tools -> mail sink.

Each test names the invariant (ARCHITECTURE.md section 5) it proves.
"""

import httpx
import pytest

from sentinel import fixtures
from tests.conftest import DOWNSTREAM_TOKEN
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

OUTBOX = {"to": fixtures.VENDOR, "subject": "Quotation Q-1042 acknowledged", "body": "Received."}


def text(result) -> str:
    return " ".join(getattr(p, "text", "") for p in result.content)


async def start(stack, allowed_tools=None, **kw) -> dict:
    """Start a session; optionally narrow the slip before the officer confirms (tests only)."""
    if allowed_tools is None:
        return await stack.start_session(**kw)
    async with httpx.AsyncClient(base_url=stack.api_url, headers={"Authorization": "Bearer test-api-token"}) as c:
        draft = (await c.post("/tasks", json={"template": "quotation_processing", "officer": "t"})).json()
        stack.rt.drafts[draft["contract_id"]] = stack.rt.drafts[draft["contract_id"]].model_copy(
            update={"allowed_tools": allowed_tools})
        return (await c.post(f"/tasks/{draft['contract_id']}/confirm", json={"column": kw.get("column", "sentinel")})).json()


# ---- the happy path ----------------------------------------------------------------------------
async def test_allowed_calls_flow_through_and_reach_the_sink(stack):
    s = await start(stack)
    async with stack.client(s["session_token"]) as c:
        names = sorted(t.name for t in await c.list_tools())
        assert names == ["query_stock", "read_quotation", "send_email"]  # delete_records is not offered
        assert "QUOTATION Q-1042" in text(await c.call_tool("read_quotation", {"quote_id": "Q-1042"}))
        await c.call_tool("send_email", OUTBOX)
    delivered = [m for m in stack.sink.snapshot() if m["session_id"] == s["session_id"]]
    assert len(delivered) == 1 and delivered[0]["column"] == "sentinel" and delivered[0]["to"] == fixtures.VENDOR


async def test_decisions_and_requests_are_published_as_events(stack):
    s = await start(stack)
    async with stack.client(s["session_token"]) as c:
        await c.call_tool("read_quotation", {"quote_id": "Q-1042"})
    mine = [e for e in stack.rt.bus.recent() if e.session_id == s["session_id"]]
    assert [e.type for e in mine if e.type in ("action.requested", "decision")] == ["action.requested", "decision"]
    decision = next(e for e in mine if e.type == "decision").payload
    assert decision["effect"] == "ALLOW" and decision["reason_code"] == "ALLOWED"


async def test_poisoned_quotation_is_readable_and_carries_the_injection(stack):
    s = await start(stack, column="unprotected")
    async with stack.client(s["session_token"]) as c:
        assert "ADDENDUM" in text(await c.call_tool("read_quotation", {"quote_id": "Q-1043"}))


# ---- invariant 3: R1 on every call, not only in tools/list ---------------------------------------
async def test_hidden_unregistered_tool_is_blocked_when_called_directly(stack):
    s = await start(stack)
    before = len(stack.sink.snapshot())
    async with stack.client(s["session_token"]) as c:
        with pytest.raises(Exception, match="not a registered tool"):
            await c.call_tool("delete_records", {"table": "stock"})
    assert len(stack.sink.snapshot()) == before  # nothing reached the tool


async def test_registered_tool_outside_the_slip_is_blocked_and_never_forwarded(stack):
    s = await start(stack, allowed_tools=["read_quotation"])
    before = len(stack.sink.snapshot())
    async with stack.client(s["session_token"]) as c:
        assert [t.name for t in await c.list_tools()] == ["read_quotation"]
        with pytest.raises(Exception, match="not part of this task's permission slip"):
            await c.call_tool("send_email", OUTBOX)
    assert len(stack.sink.snapshot()) == before
    decisions = [e.payload for e in stack.rt.bus.recent() if e.session_id == s["session_id"] and e.type == "decision"]
    assert decisions[-1]["effect"] == "BLOCK" and decisions[-1]["rule_ids"] == ["R1"]


async def test_r1_only_column_also_enforces_the_slip(stack):
    s = await start(stack, allowed_tools=["read_quotation"], column="r1_only")
    async with stack.client(s["session_token"]) as c:
        with pytest.raises(Exception, match="permission slip"):
            await c.call_tool("send_email", OUTBOX)


async def test_unprotected_baseline_runs_no_rules_and_the_tool_really_runs(stack):
    s = await start(stack, column="unprotected")
    async with stack.client(s["session_token"]) as c:
        assert "delete_records" in [t.name for t in await c.list_tools()]
        await c.call_tool("delete_records", {"table": "stock"})
    assert any(m["subject"] == "DELETE" for m in stack.sink.snapshot("unprotected"))


# ---- authentication, freeze (invariant 7) --------------------------------------------------------
async def test_no_token_and_garbage_token_are_rejected(stack):
    for headers in ({}, {"Authorization": "Bearer not-a-token"}, {"Authorization": "Basic abc"}):
        async with Client(StreamableHttpTransport(stack.gateway_url, headers=headers)) as c:
            # tools/list failures reach the client as a generic protocol error (known limitation, see
            # DECISIONS D-016); what matters is that the listing is refused. tools/call keeps our message.
            with pytest.raises(Exception):
                await c.list_tools()
            with pytest.raises(Exception, match="Blocked"):
                await c.call_tool("read_quotation", {"quote_id": "Q-1042"})


async def test_frozen_session_cannot_call_or_list_and_token_stays_dead(stack):
    s = await start(stack)
    async with httpx.AsyncClient(base_url=stack.api_url, headers={"Authorization": "Bearer test-api-token"}) as api:
        async with stack.client(s["session_token"]) as c:
            await c.call_tool("read_quotation", {"quote_id": "Q-1042"})
        assert (await api.post("/killswitch", json={"session_id": s["session_id"]})).json()["status"] == "frozen"
    for _ in range(2):  # reconnect with the same token
        async with stack.client(s["session_token"]) as c:
            with pytest.raises(Exception, match="not valid|frozen"):
                await c.call_tool("read_quotation", {"quote_id": "Q-1042"})
            with pytest.raises(Exception):  # generic protocol error for tools/list (D-016)
                await c.list_tools()
    assert any(e.type == "freeze" and e.session_id == s["session_id"] for e in stack.rt.bus.recent())


async def test_a_token_from_another_gateway_key_is_rejected(stack):
    from datetime import datetime, timezone

    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from sentinel.contracts import draft_contract, load_templates, mint_session_token
    from sentinel.models import Column, SessionStatus

    c0 = draft_contract(load_templates(), "quotation_processing", "x").model_copy(update={"status": SessionStatus.ACTIVE})
    forged, _ = mint_session_token(c0, Column.SENTINEL, Ed25519PrivateKey.generate(), now=datetime.now(timezone.utc))
    async with stack.client(forged) as c:
        with pytest.raises(Exception, match="not valid"):
            await c.call_tool("read_quotation", {"quote_id": "Q-1042"})


# ---- invariants 4 and 5: headers and credentials -------------------------------------------------
async def test_agent_supplied_headers_do_not_reach_the_tools(stack):
    s = await start(stack)
    forged = {"X-Sentinel-Session": "ses_forged", "X-Sentinel-Column": "unprotected", "X-Sentinel-Token": "x"}
    async with stack.client(s["session_token"], headers=forged) as c:
        await c.call_tool("send_email", OUTBOX)
    row = [m for m in stack.sink.snapshot() if m["session_id"] == s["session_id"]]
    assert len(row) == 1 and row[0]["column"] == "sentinel"  # the real labels, set by Sentinel only
    assert not any(m["session_id"] == "ses_forged" for m in stack.sink.snapshot())


async def test_tools_reject_direct_calls_without_the_sentinel_token(stack):
    for headers in ({}, {"x-sentinel-token": "guess"}, {"Authorization": "Bearer anything"}):
        with pytest.raises(Exception):
            async with Client(StreamableHttpTransport(stack.tools_url, headers=headers)) as c:
                await c.call_tool("send_email", OUTBOX)
    async with httpx.AsyncClient() as h:
        base = stack.tools_url.removesuffix("/mcp")
        assert (await h.get(f"{base}/inbox")).status_code == 401
        assert (await h.get(f"{base}/inbox", headers={"x-sentinel-token": DOWNSTREAM_TOKEN})).status_code == 200


def test_tool_server_refuses_to_build_without_a_token():
    from sentinel.tools.server import build_tools_server

    with pytest.raises(ValueError):
        build_tools_server("")
