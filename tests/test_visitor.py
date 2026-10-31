"""D-062: on a public deployment someone with no token can try the demo and the chat, on synthetic data and mock tools.

What they must never reach: the officer's runs, chats and approvals, a real connector's approval, the tamper demo, uploads, or slips and
tokens. Off unless the deployment turns it on, so a laptop behaves as before.
"""

from __future__ import annotations

import asyncio
import uuid

import httpx
import pytest
import pytest_asyncio

from sentinel.agent import runner
from sentinel.oneport import MESSAGE_LIMIT, RateLimit, _visitor_limit


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def public(stack):
    stack.rt.public_demo = True
    try:
        yield stack
    finally:
        stack.rt.public_demo = False


def _visitor(stack) -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url=stack.api_url, timeout=60)


async def _until(c, path, test, what):
    for _ in range(200):
        view = (await c.get(path)).json()
        if test(view):
            return view
        await asyncio.sleep(0.1)
    raise AssertionError(f"timed out waiting for {what}")


def _finished(view) -> bool:
    return view["status"] in ("finished", "cancelled")


def _pending(view) -> list[dict]:
    return [a for lane in view["lanes"] for a in lane.get("approvals") or [] if a["status"] == "pending"]


@pytest.fixture
def no_active_run(stack):
    stack.rt.runs.active = None


pytestmark = pytest.mark.asyncio(loop_scope="module")


async def test_off_by_default_nothing_is_open_to_someone_with_no_token(stack):
    assert stack.rt.public_demo is False
    async with _visitor(stack) as c:
        for path in ("/scenarios", "/runs", "/api/v1/chat/presets", "/audit/verify"):
            assert (await c.get(path)).status_code == 401, path
        assert (await c.post("/runs", json={"scenario": "poisoned", "source": "scripted"})).status_code == 401


async def test_a_visitor_can_run_the_demo_and_it_is_decided_the_same_way(public, no_active_run):
    async with _visitor(public) as c:
        assert (await c.get("/scenarios")).status_code == 200
        run = (await c.post("/runs", json={"scenario": "poisoned", "source": "scripted"})).json()
        assert (await c.post(f"/runs/{run['run_id']}/confirm")).status_code == 200
        view = await _until(c, f"/runs/{run['run_id']}", _finished, "the run")
    assert {lane["column"]: lane["outcome"] for lane in view["lanes"]}["sentinel"] == "contained"
    assert "token" not in str(view).lower().replace("tokens", "")


async def test_an_empty_bearer_from_the_console_is_a_visitor_and_a_wrong_token_is_still_refused(public):
    async with httpx.AsyncClient(base_url=public.api_url, headers={"Authorization": "Bearer"}) as c:  # a browser trims "Bearer "
        assert (await c.get("/scenarios")).status_code == 200
    async with httpx.AsyncClient(base_url=public.api_url, headers={"Authorization": "Bearer wrong"}) as c:
        assert (await c.get("/scenarios")).status_code == 401


@pytest.mark.parametrize("method, path", [
    ("GET", "/approvals"), ("POST", "/audit/tamper"), ("POST", "/audit/restore"), ("GET", "/audit/export"), ("POST", "/api/v1/slips"),
    ("POST", "/api/v1/connect/token"), ("POST", "/killswitch"), ("GET", "/inbox"), ("GET", "/api/v1/tools"), ("POST", "/tasks"),
])
async def test_what_stays_the_officers(public, method, path):
    async with _visitor(public) as c:
        assert (await c.request(method, path, json={})).status_code == 401, path


async def test_a_visitor_can_check_the_log_but_is_not_offered_the_tamper_demo(public):
    public.rt.allow_tamper = True
    try:
        async with _visitor(public) as c:
            seen = (await c.get("/audit/verify")).json()
        async with public.api() as officer:
            assert (await officer.get("/audit/verify")).json()["tamper_enabled"] is True
    finally:
        public.rt.allow_tamper = False
    assert seen["ok"] is True and seen["tamper_enabled"] is False and seen["restorable"] is False


async def test_a_visitor_cannot_use_a_live_model_in_the_console(public):
    async with _visitor(public) as c:
        r = await c.post("/runs", json={"scenario": "poisoned", "source": "live", "model": {"model": "x"}})
    assert r.status_code == 403


async def test_a_visitor_cannot_see_or_touch_the_officers_run_or_be_attached_to_it(public, no_active_run):
    async with public.api() as officer:
        run = (await officer.post("/runs", json={"scenario": "bank_change", "source": "scripted"})).json()
        assert (await officer.post(f"/runs/{run['run_id']}/confirm")).status_code == 200
        path = f"/runs/{run['run_id']}"
        view = await _until(officer, path, _pending, "the officer's approval")
        approval = _pending(view)[0]["approval_id"]
        async with _visitor(public) as c:
            assert (await c.get("/runs")).json() == {"active": None, "runs": []}
            assert (await c.get(path)).status_code == 404
            assert (await c.post(f"{path}/cancel")).status_code == 404
            assert (await c.post(f"{path}/confirm")).status_code == 404
            assert (await c.post(f"/approvals/{approval}", json={"decision": "approve"})).status_code == 404
            second = (await c.post("/runs", json={"scenario": "poisoned", "source": "scripted"})).json()
            busy = await c.post(f"/runs/{second['run_id']}/confirm")
            assert busy.status_code == 409 and "Someone else" in busy.json()["detail"]
        assert (await officer.get(path)).json()["status"] == "running"  # the officer's demo was not disturbed
        await officer.post(f"{path}/cancel")


async def test_a_visitor_decides_their_own_approval_and_it_never_reaches_the_officers_list(public, no_active_run):
    async with _visitor(public) as c, public.api() as officer:
        run = (await c.post("/runs", json={"scenario": "bank_change", "source": "scripted"})).json()
        await c.post(f"/runs/{run['run_id']}/confirm")
        path = f"/runs/{run['run_id']}"
        view = await _until(c, path, _pending, "the visitor's approval")
        approval = _pending(view)[0]["approval_id"]
        ids = [a["approval_id"] for a in (await officer.get("/approvals")).json()["pending"]]
        assert approval not in ids
        assert (await c.post(f"/approvals/{approval}", json={"decision": "deny"})).status_code == 200
        await _until(c, path, _finished, "the run")


async def test_a_visitor_cannot_decide_a_held_call_from_a_real_client(public):
    """The officer's approval of a connector's call is the whole point: a visitor must never be able to say yes to it."""
    async with public.api() as officer:
        slip = (await officer.post("/api/v1/slips", json={
            "objective": "Check approvals", "confirm": True, "allowed_tools": ["gmail.get_thread", "gmail.send_message"],
            "allowed_destinations": ["ops@team.example"], "max_messages": 5, "unseen_context": True, "strict_flows": True})).json()
        session = slip["header_value"]
        async with httpx.AsyncClient(base_url=public.api_url, headers={"Authorization": session}, timeout=30) as client:
            held = (await client.post("/api/v1/check/call", json={
                "tool_name": "mcp__claude_ai_Gmail__send_message", "wait_s": 0.1,
                "tool_input": {"to": ["ops@team.example"], "subject": "Status", "body": f"On track {uuid.uuid4().hex}"}})).json()
        assert held["effect"] == "ASK"
        pending = [a["approval_id"] for a in (await officer.get("/approvals")).json()["pending"]]
        assert held["approval_id"] in pending  # the officer still sees it
        async with _visitor(public) as c:
            assert (await c.post(f"/approvals/{held['approval_id']}", json={"decision": "approve"})).status_code == 404
        assert (await officer.post(f"/approvals/{held['approval_id']}", json={"decision": "deny"})).status_code == 200


async def test_the_officer_always_takes_over_from_a_visitors_run(public, no_active_run):
    async with _visitor(public) as c, public.api() as officer:
        waiting = (await c.post("/runs", json={"scenario": "bank_change", "source": "scripted"})).json()
        await c.post(f"/runs/{waiting['run_id']}/confirm")
        await _until(c, f"/runs/{waiting['run_id']}", _pending, "the visitor's approval")
        mine = (await officer.post("/runs", json={"scenario": "poisoned", "source": "scripted"})).json()
        assert (await officer.post(f"/runs/{mine['run_id']}/confirm")).status_code == 200
        assert (await c.get(f"/runs/{waiting['run_id']}")).json()["status"] == "cancelled"
        await _until(officer, f"/runs/{mine['run_id']}", _finished, "the officer's run")


async def test_another_visitor_can_end_a_run_left_waiting_but_not_one_still_going(public, no_active_run, monkeypatch):
    async with _visitor(public) as c:
        left = (await c.post("/runs", json={"scenario": "bank_change", "source": "scripted"})).json()
        await c.post(f"/runs/{left['run_id']}/confirm")
        await _until(c, f"/runs/{left['run_id']}", _pending, "the approval")
        next_up = (await c.post("/runs", json={"scenario": "poisoned", "source": "scripted"})).json()
        assert (await c.post(f"/runs/{next_up['run_id']}/confirm")).status_code == 409
        public.rt.runs.runs[left["run_id"]].confirmed_at -= 1000
        assert (await c.post(f"/runs/{next_up['run_id']}/confirm")).status_code == 200
        await _until(c, f"/runs/{next_up['run_id']}", _finished, "the run")


async def test_old_visitor_runs_are_forgotten_so_they_cannot_fill_the_server(public, monkeypatch):
    monkeypatch.setattr("sentinel.runs.MAX_VISITOR_RUNS", 2)
    async with _visitor(public) as c:
        ids = [(await c.post("/runs", json={"scenario": "poisoned", "source": "scripted"})).json()["run_id"] for _ in range(4)]
    assert ids[0] not in public.rt.runs.runs and ids[-1] in public.rt.runs.runs


async def _chat(c, mode="scripted", preset="quotation"):
    chat = (await c.post("/api/v1/chat", json={"preset": preset, "mode": mode})).json()
    assert (await c.post(f"/api/v1/chat/{chat['chat_id']}/confirm")).status_code == 200
    return chat


async def test_a_visitor_can_chat_and_the_rules_still_decide(public):
    async with _visitor(public) as c:
        presets = (await c.get("/api/v1/chat/presets")).json()
        assert {"quotation", "own-doc"} <= {p["id"] for p in presets} and "real-github" not in {p["id"] for p in presets}
        chat = await _chat(c)
        assert chat["can_upload"] is False
        assert (await c.post(f"/api/v1/chat/{chat['chat_id']}/messages", json={"text": "Process the quotation"})).status_code == 202
        view = await _until(c, f"/api/v1/chat/{chat['chat_id']}", lambda v: v["status"] == "ready", "the answer")
    assert "token" not in view and view["messages"]


@pytest.mark.parametrize("body", [
    {"preset": "real-github", "mode": "auto"}, {"preset": "quotation", "mode": "local"}, {"preset": "quotation", "mode": "replay", "recording": {"x": 1}},
])
async def test_what_a_visitors_chat_may_not_ask_for(public, body):
    async with _visitor(public) as c:
        assert (await c.post("/api/v1/chat", json=body)).status_code == 403


async def test_a_visitor_cannot_upload_or_reach_the_officers_chat(public):
    async with public.api() as officer, _visitor(public) as c:
        mine = (await officer.post("/api/v1/chat", json={"preset": "quotation", "mode": "scripted"})).json()
        path = f"/api/v1/chat/{mine['chat_id']}"
        assert (await c.get(path)).status_code == 404
        assert (await c.post(f"{path}/confirm")).status_code == 404
        assert (await c.post(f"{path}/messages", json={"text": "hi"})).status_code == 404
        assert (await c.get(f"{path}/recording")).status_code == 404
        theirs = await _chat(c)
        up = await c.post(f"/api/v1/chat/{theirs['chat_id']}/documents", files={"file": ("a.pdf", b"%PDF-1.4", "application/pdf")})
        assert up.status_code == 401


async def test_the_visitors_share_of_the_model_runs_out_before_the_officers(public, monkeypatch):
    monkeypatch.setenv("SENTINEL_VISITOR_MODEL_CAP", "5")
    monkeypatch.setattr(runner, "_LIVE_REQUESTS", 5)
    assert runner.visitor_model_share_left() is False
    async with _visitor(public) as c:
        chat = await _chat(c)
        public.rt.chats.chats[chat["chat_id"]].mode = "live"
        r = await c.post(f"/api/v1/chat/{chat['chat_id']}/messages", json={"text": "hello"})
    assert r.status_code == 429 and "Scripted" in r.json()["detail"]
    monkeypatch.setattr(runner, "_LIVE_REQUESTS", 4)
    assert runner.visitor_model_share_left() is True


async def test_a_visitors_messages_are_limited_harder_than_anything_else_and_the_officer_is_not():
    no_token = {"method": "POST", "path": "/api/v1/chat/chat_1/messages", "headers": []}
    assert _visitor_limit(no_token) == ("message", MESSAGE_LIMIT)
    assert _visitor_limit({**no_token, "headers": [(b"authorization", b"Bearer ")]}) == ("message", MESSAGE_LIMIT)
    assert _visitor_limit({**no_token, "headers": [(b"authorization", b"Bearer abc")]}) is None
    assert _visitor_limit({**no_token, "method": "GET"}) is None
    assert _visitor_limit({"method": "POST", "path": "/runs", "headers": []})[0] == "demo"
    assert _visitor_limit({"method": "POST", "path": "/mcp", "headers": []}) is None
    limit = RateLimit(clock=lambda: 0.0)
    assert all(limit.allow("a", "message", MESSAGE_LIMIT) for _ in range(MESSAGE_LIMIT)) and not limit.allow("a", "message", MESSAGE_LIMIT)
