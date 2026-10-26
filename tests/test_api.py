"""REST and WebSocket API tests: auth, officer confirmation, inbox, live events."""

import asyncio
import json

import httpx
import pytest
import websockets

from tests.conftest import API_TOKEN


@pytest.fixture()
async def api(stack):
    async with httpx.AsyncClient(base_url=stack.api_url, headers={"Authorization": f"Bearer {API_TOKEN}"}) as c:
        yield c


async def test_unauthenticated_requests_are_rejected_except_health(stack):
    async with httpx.AsyncClient(base_url=stack.api_url) as c:
        assert (await c.get("/health")).status_code == 200
        for method, path in (("post", "/tasks"), ("get", "/inbox"), ("post", "/killswitch"), ("get", "/sessions/x")):
            assert (await getattr(c, method)(path)).status_code in (401, 422)
        r = await c.post("/tasks", json={"template": "quotation_processing", "officer": "x"},
                         headers={"Authorization": "Bearer wrong"})
        assert r.status_code == 401


async def test_task_must_be_confirmed_once_and_only_then_a_token_exists(api, stack):
    draft = (await api.post("/tasks", json={"template": "quotation_processing", "officer": "Col. R. Menon"})).json()
    assert draft["status"] == "pending" and "session_token" not in draft
    confirmed = await api.post(f"/tasks/{draft['contract_id']}/confirm", json={"column": "sentinel"})
    assert confirmed.status_code == 200
    body = confirmed.json()
    assert body["contract_hash"] == draft["contract_hash"] and body["mcp_url"] == stack.gateway_url
    assert (await api.post(f"/tasks/{draft['contract_id']}/confirm", json={})).status_code == 404  # no second token
    assert (await api.get(f"/sessions/{body['session_id']}")).json()["status"] == "active"


async def test_unknown_template_and_unknown_contract(api):
    assert (await api.post("/tasks", json={"template": "nope", "officer": "x"})).status_code == 404
    assert (await api.post("/tasks/tc_missing/confirm", json={})).status_code == 404


async def test_inbox_reports_what_was_delivered(api, stack):
    s = await stack.start_session(column="unprotected")
    async with stack.client(s["session_token"]) as c:
        await c.call_tool("send_email", {"to": "x@y.example", "subject": "s", "body": "hello"})
    rows = (await api.get("/inbox", params={"column": "unprotected"})).json()["delivered"]
    assert any(r["session_id"] == s["session_id"] and r["body"] == "hello" for r in rows)


async def test_websocket_requires_the_token(stack):
    ws_url = stack.api_url.replace("http", "ws") + "/ws"
    async with websockets.connect(ws_url) as ws:
        await ws.send(json.dumps({"type": "auth", "token": "wrong"}))
        with pytest.raises(websockets.exceptions.ConnectionClosed):
            await asyncio.wait_for(ws.recv(), timeout=5)


async def test_websocket_streams_live_events(stack):
    ws_url = stack.api_url.replace("http", "ws") + "/ws"
    async with websockets.connect(ws_url) as ws:
        await ws.send(json.dumps({"type": "auth", "token": API_TOKEN}))
        assert json.loads(await asyncio.wait_for(ws.recv(), 5))["type"] == "auth.ok"
        s = await stack.start_session()
        async with stack.client(s["session_token"]) as c:
            await c.call_tool("read_quotation", {"quote_id": "Q-1042"})
        seen = []
        while not {"contract.issued", "session.started", "action.requested", "decision"} <= {e["type"] for e in seen
                                                                                            if e.get("session_id") == s["session_id"]}:
            seen.append(json.loads(await asyncio.wait_for(ws.recv(), 5)))
    mine = [e for e in seen if e.get("session_id") == s["session_id"]]
    assert next(e for e in mine if e["type"] == "decision")["payload"]["effect"] == "ALLOW"
