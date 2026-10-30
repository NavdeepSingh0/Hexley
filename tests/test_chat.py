"""Sentinel Chat backend (core plan B5): the chat is a host whose model's every tool call goes through the real gateway, and
everything the page shows is built from gateway events."""

import asyncio
import json
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from sentinel import chat as chatmod
from sentinel.agent import runner
from sentinel.chat import ChatError, ScriptedModel, action_view, args_preview, latest_mascot, mascot_state, script_messages
from sentinel.models import EventEnvelope
from sentinel.runs import SCENARIOS

from .conftest import API_TOKEN


# ---- helpers ----------------------------------------------------------------------------------------------------------
async def wait_for(api, chat_id, predicate, timeout=30.0):
    t0 = asyncio.get_event_loop().time()
    while True:
        view = (await api.get(f"/api/v1/chat/{chat_id}")).json()
        if predicate(view):
            return view
        if asyncio.get_event_loop().time() - t0 > timeout:
            raise AssertionError(f"timed out; last view: {view['status']} {[(a['tool'], a['decision']) for m in view['messages'] for a in m['actions']]}")
        await asyncio.sleep(0.05)


async def start(api, preset="quotation", mode="scripted", confirm=True, **extra):
    r = await api.post("/api/v1/chat", json={"preset": preset, "mode": mode, **extra})
    assert r.status_code == 201, r.text
    view = r.json()
    if confirm:
        r = await api.post(f"/api/v1/chat/{view['chat_id']}/confirm")
        assert r.status_code == 200, r.text
        view = r.json()
    return view


def actions_of(view):
    return [a for m in view["messages"] for a in m["actions"]]


def with_model(stack, model):
    """Make the next chats use this model object (a fake) instead of the real endpoint."""
    stack.rt.chats.endpoint_factory = lambda: model


def ev(type_, payload, ts=None, session="ses_x"):
    return EventEnvelope(type=type_, session_id=session, column="sentinel", ts=ts or datetime.now(timezone.utc), payload=payload)


# ---- presets and creation -----------------------------------------------------------------------------------------------
async def test_the_presets_have_what_the_page_needs(stack):
    async with stack.api() as api:
        presets = (await api.get("/api/v1/chat/presets")).json()
    assert {p["id"] for p in presets} >= {"quotation", "own-pdf", "poisoned-web", "bank-change"}
    for p in presets:
        assert set(p) == {"id", "title", "prompt", "description"} and all(p.values())


async def test_every_chat_view_carries_the_disclosure_in_every_mode_and_state(stack):
    async with stack.api() as api:
        a = await start(api, mode="scripted", confirm=False)
        assert "SCRIPTED" in a["disclosure"] and "synthetic data" in a["disclosure"] and "Hexley Chat" in a["disclosure"]
        b = (await api.post(f"/api/v1/chat/{a['chat_id']}/confirm")).json()
        assert b["disclosure"] == a["disclosure"]
        sent = (await api.post(f"/api/v1/chat/{a['chat_id']}/messages", json={"text": "go"}))
        assert sent.status_code == 202
        done = await wait_for(api, a["chat_id"], lambda v: v["status"] == "ready")
        assert done["disclosure"] == a["disclosure"]
        # a live chat names the model
        with_model(stack, ScriptedModel([{"role": "assistant", "content": "hi"}], "fake/model-1"))
        c = await start(api, mode="live", confirm=False)
        assert "fake/model-1" in c["disclosure"] and c["model"] == "fake/model-1" and c["mode"] == "live"


async def test_a_new_chat_waits_for_the_officer_and_shows_the_slip(stack):
    async with stack.api() as api:
        v = await start(api, mode="scripted", confirm=False)
        assert v["status"] == "awaiting_confirmation" and v["messages"] == [] and v["retry"] is None
        assert v["mascot"]["state"] == "sleeping"
        slip = v["slip"]
        assert slip["allowed_tools"] == ["read_quotation", "query_stock", "send_email"]
        assert slip["allowed_destinations"] == ["shakti.example"] and slip["max_messages"] == 1 and slip["objective"]
        r = await api.post(f"/api/v1/chat/{v['chat_id']}/messages", json={"text": "hello"})
        assert r.status_code == 409 and "confirm" in r.json()["detail"]
        ok = await api.post(f"/api/v1/chat/{v['chat_id']}/confirm")
        assert ok.json()["status"] == "ready" and ok.json()["mascot"]["state"] == "idle"
        assert (await api.post(f"/api/v1/chat/{v['chat_id']}/confirm")).status_code == 409  # not twice


async def test_bad_requests_get_plain_errors(stack):
    async with stack.api() as api:
        assert (await api.post("/api/v1/chat", json={"preset": "nope"})).status_code == 404
        assert (await api.post("/api/v1/chat", json={"preset": "quotation", "mode": "weird"})).status_code == 422
        assert (await api.get("/api/v1/chat/chat_missing")).status_code == 404
        v = await start(api, mode="scripted")
        assert (await api.post(f"/api/v1/chat/{v['chat_id']}/messages", json={"text": "   "})).status_code == 422
        assert (await api.post(f"/api/v1/chat/{v['chat_id']}/messages", json={"text": "x" * 2001})).status_code == 422


async def test_the_chat_routes_need_the_officer_token(stack):
    async with httpx.AsyncClient(base_url=stack.api_url) as anon:
        for method, path in (("get", "/api/v1/chat/presets"), ("post", "/api/v1/chat"), ("get", "/api/v1/chat/x"),
                             ("post", "/api/v1/chat/x/confirm"), ("post", "/api/v1/chat/x/messages"),
                             ("get", "/api/v1/chat/x/recording")):
            assert (await getattr(anon, method)(path)).status_code == 401, path


# ---- the real gateway decides; the page shows its events -----------------------------------------------------------------
async def test_a_poisoned_quotation_through_the_chat_is_denied_by_the_gateway_and_nothing_leaves(stack):
    before = len(stack.sink.snapshot())
    async with stack.api() as api:
        v = await start(api, mode="scripted")
        await api.post(f"/api/v1/chat/{v['chat_id']}/messages", json={"text": "Process the quotation"})
        done = await wait_for(api, v["chat_id"], lambda x: x["status"] == "ready" and len(x["messages"]) == 2)
    acts = actions_of(done)
    assert [(a["tool"], a["decision"]) for a in acts] == [
        ("read_quotation", "ALLOWED"), ("query_stock", "ALLOWED"), ("send_email", "DENIED")]
    blocked = acts[2]
    assert blocked["rules"] == ["R2"] and "restricted" in blocked["reason"].lower()
    assert blocked["label"] == "Send an e-mail" and blocked["args_preview"].startswith("to sales@shakti.example")
    assert len(stack.sink.snapshot()) == before  # nothing was delivered
    assert done["mascot"] == {"state": "denied", "message": "That would send restricted data out."}
    assert done["messages"][0]["role"] == "user" and done["messages"][1]["role"] == "assistant"


async def test_each_action_reason_is_the_gateways_own_sentence(stack):
    async with stack.api() as api:
        v = await start(api, mode="scripted")
        await api.post(f"/api/v1/chat/{v['chat_id']}/messages", json={"text": "go"})
        done = await wait_for(api, v["chat_id"], lambda x: x["status"] == "ready" and len(x["messages"]) == 2)
    chat = stack.rt.chats.chats[v["chat_id"]]
    sentences = {e.payload["action_id"]: e.payload["summary_plain"] for e in chat.events if e.type == "decision"}
    for a in actions_of(done):
        assert a["reason"] == sentences[a["action_id"]]  # the host adds no words of its own


async def test_a_multi_turn_conversation_keeps_its_history_and_the_budget(stack):
    class Model:
        model = "fake/multi"

        def __init__(self):
            self.seen = []

        async def chat(self, client, messages, tools, on_wait=None):
            self.seen.append([m["role"] for m in messages])
            if len(self.seen) == 1:
                return {"role": "assistant", "content": "", "tool_calls": [{"id": "c1", "type": "function", "function": {
                    "name": "read_quotation", "arguments": '{"quote_id": "Q-1042"}'}}]}
            return {"role": "assistant", "content": f"answer {len(self.seen)}"}

    model = Model()
    with_model(stack, model)
    async with stack.api() as api:
        v = await start(api, mode="live")
        await api.post(f"/api/v1/chat/{v['chat_id']}/messages", json={"text": "first"})
        first = await wait_for(api, v["chat_id"], lambda x: x["status"] == "ready" and len(x["messages"]) == 2)
        assert first["messages"][1]["text"] == "answer 2" and [a["tool"] for a in actions_of(first)] == ["read_quotation"]
        await api.post(f"/api/v1/chat/{v['chat_id']}/messages", json={"text": "second"})
        second = await wait_for(api, v["chat_id"], lambda x: x["status"] == "ready" and len(x["messages"]) == 4)
    assert second["messages"][3]["text"] == "answer 3"
    assert len(actions_of(second)) == 1  # the second reply made no calls; the first reply keeps its own chip
    assert second["messages"][3]["actions"] == []
    # the third model call saw: system, user, assistant(tool), tool, assistant, user
    assert model.seen[2] == ["system", "user", "assistant", "tool", "assistant", "user"]


async def test_one_message_at_a_time(stack):
    gate = asyncio.Event()

    class Slow:
        model = "fake/slow"

        async def chat(self, client, messages, tools, on_wait=None):
            await gate.wait()
            return {"role": "assistant", "content": "done"}

    with_model(stack, Slow())
    async with stack.api() as api:
        v = await start(api, mode="live")
        await api.post(f"/api/v1/chat/{v['chat_id']}/messages", json={"text": "one"})
        r = await api.post(f"/api/v1/chat/{v['chat_id']}/messages", json={"text": "two"})
        assert r.status_code == 409 and "wait" in r.json()["detail"]
        assert (await api.get(f"/api/v1/chat/{v['chat_id']}")).json()["status"] == "thinking"
        gate.set()
        await wait_for(api, v["chat_id"], lambda x: x["status"] == "ready")


# ---- approval, quarantine -----------------------------------------------------------------------------------------------
async def test_a_held_action_waits_for_the_officer_then_runs_when_approved(stack):
    async with stack.api() as api:
        v = await start(api, preset="bank-change", mode="scripted")
        await api.post(f"/api/v1/chat/{v['chat_id']}/messages", json={"text": "update it"})
        held = await wait_for(api, v["chat_id"], lambda x: any(a["decision"] == "NEEDS_APPROVAL" for a in actions_of(x)))
        a = actions_of(held)[0]
        assert held["status"] == "thinking" and a["tool"] == "update_vendor_bank" and a["approval_id"]
        assert held["mascot"]["state"] == "needs-approval"
        assert (await api.post(f"/approvals/{a['approval_id']}", json={"decision": "approve"})).status_code == 200
        done = await wait_for(api, v["chat_id"], lambda x: x["status"] == "ready")
        assert [(x["tool"], x["decision"]) for x in actions_of(done)] == [("update_vendor_bank", "ALLOWED")]
        assert actions_of(done)[0]["approval_id"] == a["approval_id"]


async def test_a_refused_approval_shows_denied_and_says_so(stack):
    async with stack.api() as api:
        v = await start(api, preset="bank-change", mode="scripted")
        await api.post(f"/api/v1/chat/{v['chat_id']}/messages", json={"text": "update it"})
        held = await wait_for(api, v["chat_id"], lambda x: any(a["decision"] == "NEEDS_APPROVAL" for a in actions_of(x)))
        await api.post(f"/approvals/{actions_of(held)[0]['approval_id']}", json={"decision": "deny"})
        done = await wait_for(api, v["chat_id"], lambda x: x["status"] == "ready")
    assert actions_of(done)[0]["decision"] == "DENIED"
    assert done["mascot"] == {"state": "denied", "message": "The officer did not approve it."}


async def test_three_denials_quarantine_the_chat_and_the_composer_closes(stack):
    steps = SCENARIOS["freeze"].scripts[2]
    with_model(stack, ScriptedModel(script_messages(steps), "fake/freeze"))
    async with stack.api() as api:
        v = await start(api, mode="live")
        await api.post(f"/api/v1/chat/{v['chat_id']}/messages", json={"text": "go"})
        done = await wait_for(api, v["chat_id"], lambda x: x["status"] == "quarantined")
        assert done["mascot"]["state"] == "quarantined"
        assert "QUARANTINED" in [a["decision"] for a in actions_of(done)]
        r = await api.post(f"/api/v1/chat/{v['chat_id']}/messages", json={"text": "again"})
        assert r.status_code == 409 and "quarantined" in r.json()["detail"]


# ---- the model: waiting, failing --------------------------------------------------------------------------------------
async def test_a_wait_for_the_model_shows_as_model_busy_with_the_attempt(stack):
    release = asyncio.Event()

    class Busy:
        model = "fake/busy"

        async def chat(self, client, messages, tools, on_wait=None):
            await on_wait(2, 8.0)  # what ModelEndpoint does while a key rests
            await release.wait()
            return {"role": "assistant", "content": "back"}

    with_model(stack, Busy())
    async with stack.api() as api:
        v = await start(api, mode="live")
        await api.post(f"/api/v1/chat/{v['chat_id']}/messages", json={"text": "hi"})
        busy = await wait_for(api, v["chat_id"], lambda x: x["status"] == "model_busy")
        assert busy["retry"]["attempt"] == 2 and 0 < busy["retry"]["waiting_s"] <= 8.0
        assert busy["mascot"]["state"] == "idle" and "busy" in busy["mascot"]["message"]
        release.set()
        done = await wait_for(api, v["chat_id"], lambda x: x["status"] == "ready")
    assert done["retry"] is None and done["messages"][1]["text"] == "back"


async def test_a_model_that_cannot_be_reached_is_reported_plainly_and_the_chat_survives(stack):
    class Down:
        model = "fake/down"

        async def chat(self, client, messages, tools, on_wait=None):
            raise RuntimeError("the model provider failed 6 times in a row (last: HTTP 429)")

    with_model(stack, Down())
    async with stack.api() as api:
        v = await start(api, mode="live")
        await api.post(f"/api/v1/chat/{v['chat_id']}/messages", json={"text": "hi"})
        done = await wait_for(api, v["chat_id"], lambda x: x["status"] == "ready" and len(x["messages"]) == 2)
        reply = done["messages"][1]
        assert reply["role"] == "system" and "could not be reached" in reply["text"] and "HTTP 429" in reply["text"]
        assert reply["actions"] == []
        # the officer can try again
        assert (await api.post(f"/api/v1/chat/{v['chat_id']}/messages", json={"text": "again"})).status_code == 202


async def test_live_mode_without_a_key_is_a_plain_400_and_auto_falls_back_to_the_script(stack):
    def no_key():
        raise RuntimeError("NVIDIA_API_KEY is not set (add it to .env, never to chat or git)")

    stack.rt.chats.endpoint_factory = no_key
    async with stack.api() as api:
        r = await api.post("/api/v1/chat", json={"preset": "quotation", "mode": "live"})
        assert r.status_code == 400 and "NVIDIA_API_KEY" in r.json()["detail"]
        auto = (await api.post("/api/v1/chat", json={"preset": "quotation", "mode": "auto"})).json()
        assert auto["mode"] == "scripted" and "no model" in auto["disclosure"]


# ---- record and replay --------------------------------------------------------------------------------------------------
async def test_a_chat_can_be_exported_and_replayed_with_decisions_computed_live(stack):
    async with stack.api() as api:
        v = await start(api, mode="scripted")
        await api.post(f"/api/v1/chat/{v['chat_id']}/messages", json={"text": "go"})
        first = await wait_for(api, v["chat_id"], lambda x: x["status"] == "ready" and len(x["messages"]) == 2)
        rec = (await api.get(f"/api/v1/chat/{v['chat_id']}/recording")).json()
        assert rec["schema"] == "sentinel.chat-recording/1" and len(rec["messages"]) >= 3
        rv = await start(api, mode="replay", recording=rec)
        assert "REPLAY" in rv["disclosure"] and "computed live" in rv["disclosure"]
        await api.post(f"/api/v1/chat/{rv['chat_id']}/messages", json={"text": "go"})
        second = await wait_for(api, rv["chat_id"], lambda x: x["status"] == "ready" and len(x["messages"]) == 2)
    assert [(a["tool"], a["decision"]) for a in actions_of(second)] == [(a["tool"], a["decision"]) for a in actions_of(first)]


async def test_a_recording_from_a_real_model_with_null_content_is_accepted(stack):
    """Found by the live smoke chat: real models send "content": null beside their tool calls."""
    rec = {"schema": "sentinel.chat-recording/1", "model": "real/model", "recorded_at": "2026-10-29T10:00:00+00:00", "messages": [
        {"role": "assistant", "content": None, "tool_calls": [{"id": "c1", "type": "function", "function": {
            "name": "read_quotation", "arguments": '{"quote_id":"Q-1042"}'}}]},
        {"role": "assistant", "content": "Done."}]}
    async with stack.api() as api:
        v = await start(api, mode="replay", recording=rec)
        await api.post(f"/api/v1/chat/{v['chat_id']}/messages", json={"text": "go"})
        done = await wait_for(api, v["chat_id"], lambda x: x["status"] == "ready" and len(x["messages"]) == 2)
    assert [(a["tool"], a["decision"]) for a in actions_of(done)] == [("read_quotation", "ALLOWED")]
    assert done["messages"][1]["text"] == "Done." and "real/model" in done["disclosure"]


async def test_replay_without_a_body_uses_the_committed_recording_for_that_preset(stack, tmp_path, monkeypatch):
    folder = tmp_path / "chat"
    folder.mkdir()
    rec = {"schema": "sentinel.chat-recording/1", "model": "committed/model", "recorded_at": "2026-10-29T10:00:00+00:00",
           "messages": [{"role": "assistant", "content": "Hello from the file."}]}
    (folder / "quotation-20261029.json").write_text(json.dumps(rec), encoding="utf-8")
    monkeypatch.setattr(stack.rt, "recordings_dir", tmp_path)
    async with stack.api() as api:
        v = await start(api, mode="replay")
        assert "committed/model" in v["disclosure"] and "REPLAY" in v["disclosure"]
        await api.post(f"/api/v1/chat/{v['chat_id']}/messages", json={"text": "hi"})
        done = await wait_for(api, v["chat_id"], lambda x: x["status"] == "ready" and len(x["messages"]) == 2)
        assert done["messages"][1]["text"] == "Hello from the file."
        r = await api.post("/api/v1/chat", json={"preset": "own-pdf", "mode": "replay"})  # no file for this preset
        assert r.status_code == 404 and "no recorded chat" in r.json()["detail"]


def test_the_committed_chat_recordings_are_valid_and_synthetic():
    from pathlib import Path
    folder = Path(__file__).resolve().parents[1] / "recordings" / "chat"
    files = sorted(folder.glob("*.json")) if folder.is_dir() else []
    assert files, "there should be at least one committed chat recording for the offline fallback"
    for f in files:
        rec = json.loads(f.read_text(encoding="utf-8"))
        chatmod.check_recording(rec)
        assert rec["preset"] in chatmod.PRESETS and f.name.startswith(rec["preset"] + "-")
        text = json.dumps(rec)
        assert "nvapi-" not in text and "Bearer " not in text  # no credential can be in a recording


async def test_a_malformed_recording_is_refused(stack):
    async with stack.api() as api:
        for bad in ({}, {"schema": "x"}, {"schema": "sentinel.chat-recording/1", "messages": []},
                    {"schema": "sentinel.chat-recording/1", "messages": ["not a dict"]},
                    {"schema": "sentinel.chat-recording/1", "messages": [{"content": 5}]},
                    {"schema": "sentinel.chat-recording/1", "messages": [{"content": "", "tool_calls": [{"function": 1}]}]}):
            r = await api.post("/api/v1/chat", json={"preset": "quotation", "mode": "replay", "recording": bad})
            assert r.status_code == 422, bad


# ---- pure functions ----------------------------------------------------------------------------------------------------
T0 = datetime(2026, 10, 29, 12, 0, 0, tzinfo=timezone.utc)


def seq(*items):
    return [ev(t, p, T0 + timedelta(seconds=i)) for i, (t, p) in enumerate(items)]


def decision(effect, rules):
    return ("decision", {"effect": effect, "rule_ids": rules, "action_id": "a1"})


def test_the_mascot_is_asleep_without_a_session():
    assert mascot_state([]) == {"state": "sleeping", "message": ""}


def test_the_mascot_follows_the_event_table():
    now = T0 + timedelta(seconds=30)
    assert mascot_state(seq(("session.started", {})), now)["state"] == "idle"
    assert mascot_state(seq(("session.started", {}), ("action.requested", {})), now)["state"] == "checking"
    d = lambda effect, rules: mascot_state(seq(("session.started", {}), ("action.requested", {}), decision(effect, rules)), T0 + timedelta(seconds=2.5))  # noqa: E731
    assert d("ALLOW", []) == {"state": "allowed", "message": "Checked: allowed."}
    assert d("BLOCK", ["R1"]) == {"state": "denied", "message": "That's not on the permission slip."}
    assert d("BLOCK", ["R2"])["message"] == "That would send restricted data out."
    assert d("BLOCK", ["R3"])["message"] == "That address came from an untrusted document."
    assert d("BLOCK", ["R5"])["message"] == "Message limit reached."
    assert d("BLOCK", ["R4"]) == {"state": "denied", "message": "The officer did not approve it."}
    assert d("ASK", ["R4"]) == {"state": "needs-approval", "message": "This needs the officer's approval."}
    assert d("ASK", ["R7"])["message"] == "After an untrusted document, sending outside needs approval."
    assert d("FREEZE", ["R6"]) == {"state": "quarantined", "message": "Too many denied attempts: quarantined."}


def test_allowed_settles_to_idle_after_a_moment_but_denied_stays():
    base = [("session.started", {}), ("action.requested", {})]
    allowed = seq(*base, decision("ALLOW", []))
    t_allowed = T0 + timedelta(seconds=2)
    assert mascot_state(allowed, t_allowed + timedelta(seconds=1))["state"] == "allowed"
    assert mascot_state(allowed, t_allowed + timedelta(seconds=2))["state"] == "idle"
    denied = seq(*base, decision("BLOCK", ["R2"]))
    assert mascot_state(denied, T0 + timedelta(hours=1))["state"] == "denied"


def test_a_resolved_approval_returns_to_checking_and_quarantine_is_final():
    held = seq(("session.started", {}), ("action.requested", {}), decision("ASK", ["R4"]), ("approval.pending", {}), ("approval.resolved", {"status": "approved"}))
    assert mascot_state(held, T0 + timedelta(seconds=9))["state"] == "checking"
    frozen = seq(("session.started", {}), decision("FREEZE", ["R6"]), ("action.requested", {}), decision("ALLOW", []))
    assert mascot_state(frozen, T0 + timedelta(hours=1))["state"] == "quarantined"


def test_the_extension_mascot_follows_the_latest_sentinel_session_and_ignores_the_comparison_lanes():
    assert latest_mascot([]) == {"state": "sleeping", "message": "", "session_id": None}
    old = seq(("session.started", {}), decision("BLOCK", ["R2"]))
    new = [ev("session.started", {}, T0 + timedelta(seconds=5), session="ses_new")]
    lane = [EventEnvelope(type="decision", session_id="ses_lane", column="unprotected", ts=T0 + timedelta(seconds=6),
                          payload={"effect": "BLOCK", "rule_ids": ["R1"]})]
    assert latest_mascot(old, T0 + timedelta(seconds=9)) == {"state": "denied", "message": "That would send restricted data out.", "session_id": "ses_x"}
    assert latest_mascot(old + new + lane, T0 + timedelta(seconds=9)) == {"state": "idle", "message": "", "session_id": "ses_new"}


async def test_the_extension_mascot_endpoint_needs_the_token_and_shows_a_real_denial(stack):
    async with stack.api() as api:
        v = await start(api, mode="scripted")
        await api.post(f"/api/v1/chat/{v['chat_id']}/messages", json={"text": "Process the quotation"})
        await wait_for(api, v["chat_id"], lambda x: x["status"] == "ready" and len(x["messages"]) == 2)
        now = (await api.get("/api/v1/mascot/state")).json()
        assert now["state"] == "denied" and now["message"] == "That would send restricted data out."
        api.headers.pop("Authorization")
        assert (await api.get("/api/v1/mascot/state")).status_code == 401


def test_action_chips_use_the_decision_words_and_short_previews():
    base = {"action_id": "a1", "tool": "send_email", "args": {"to": "x@y.example", "body": "hello " * 50},
            "rule_ids": ["R2"], "summary": "Blocked: restricted.", "approval": None, "effect": "BLOCK"}
    assert action_view(base)["decision"] == "DENIED" and len(action_view(base)["args_preview"]) < 120
    assert action_view({**base, "effect": None, "summary": ""})["decision"] == "PENDING"
    assert action_view({**base, "effect": "ALLOW", "summary": "", "rule_ids": []})["reason"] == "Checked: allowed."
    assert action_view({**base, "effect": "FREEZE"})["decision"] == "QUARANTINED"
    held = {**base, "effect": "ASK", "approval": {"approval_id": "apr_1", "status": "pending", "summary": "s"}}
    assert action_view(held)["decision"] == "NEEDS_APPROVAL" and action_view(held)["approval_id"] == "apr_1"
    assert args_preview("query_db", {"sql": "SELECT 1"}) == "SELECT 1"
    assert chatmod.label_for("some_new_tool") == "Some new tool"


# ---- the model client: several keys, failover, no secrets in view ----------------------------------------------------
KEYS = ("key-one-AAAA", "key-two-BBBB", "key-three-CCCC")
OK = {"choices": [{"message": {"role": "assistant", "content": "done"}}]}


@pytest.fixture
def three_keys(monkeypatch):
    monkeypatch.setenv("NVIDIA_API_KEY", KEYS[0])
    monkeypatch.setenv("NVIDIA_API_KEY_2", KEYS[1])
    monkeypatch.setenv("NVIDIA_API_KEY_3", KEYS[2])
    monkeypatch.setenv("NVIDIA_BASE_URL", "http://nvidia.test/v1")
    monkeypatch.setenv("NVIDIA_MAX_RPM", "60000")  # a 1 ms gap: these tests are about keys, not pacing
    monkeypatch.setattr(runner, "RETRY_BASE_S", 0.0)


async def drive(handler, on_wait=None):
    ep = runner.ModelEndpoint(provider="nvidia", model="m")
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        return ep, await ep.chat(client, [{"role": "user", "content": "hi"}], [], on_wait=on_wait)


async def test_all_configured_keys_are_found_and_duplicates_collapse(three_keys, monkeypatch):
    assert runner.ModelEndpoint(provider="nvidia", model="m").key_count == 3
    monkeypatch.setenv("NVIDIA_API_KEY_2", KEYS[0])
    assert runner.ModelEndpoint(provider="nvidia", model="m").key_count == 2


async def test_a_429_moves_the_next_call_to_another_key_without_waiting(three_keys):
    used = []

    def handler(request):
        used.append(request.headers["authorization"].removeprefix("Bearer "))
        return httpx.Response(429, headers={"retry-after": "30"}, json={}) if len(used) == 1 else httpx.Response(200, json=OK)

    waited = []

    async def on_wait(attempt, seconds):
        waited.append(seconds)

    t0 = asyncio.get_event_loop().time()
    _, msg = await drive(handler, on_wait)
    assert msg["content"] == "done" and len(used) == 2 and used[0] != used[1]
    assert asyncio.get_event_loop().time() - t0 < 1.0 and not waited  # it did not sit out the 30 s on the resting key


async def test_when_every_key_is_resting_it_waits_for_the_soonest_and_says_so(three_keys):
    used, waited = [], []

    def handler(request):
        used.append(request.headers["authorization"])
        return httpx.Response(429, headers={"retry-after": "0.6"}, json={}) if len(used) <= 3 else httpx.Response(200, json=OK)

    async def on_wait(attempt, seconds):
        waited.append((attempt, seconds))

    _, msg = await drive(handler, on_wait)
    assert msg["content"] == "done" and len(set(used[:3])) == 3  # one try on each key first
    assert waited and waited[0][1] >= 0.4  # then it waited for the soonest key and reported the wait


async def test_a_rate_limited_key_is_not_used_again_until_it_has_rested(three_keys):
    ep = runner.ModelEndpoint(provider="nvidia", model="m")
    calls = []

    def handler(request):
        key = request.headers["authorization"].removeprefix("Bearer ")
        calls.append(key)
        return httpx.Response(429, headers={"retry-after": "60"}, json={}) if key == KEYS[0] and len(calls) == 1 else httpx.Response(200, json=OK)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        for _ in range(4):
            await ep.chat(client, [{"role": "user", "content": "hi"}], [])
    assert calls.count(KEYS[0]) == 1  # tried once, 429, then left alone


async def test_keys_never_appear_in_a_repr_or_in_the_error_that_gives_up(three_keys):
    ep = runner.ModelEndpoint(provider="nvidia", model="m")
    assert not any(k in repr(ep) for k in KEYS) and not any(k in str(ep._keys) for k in KEYS)

    def handler(request):
        return httpx.Response(429, headers={"retry-after": "0"}, json={})

    with pytest.raises(RuntimeError) as err:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            await ep.chat(client, [{"role": "user", "content": "hi"}], [])
    assert "6 times" in str(err.value) and not any(k in str(err.value) for k in KEYS)


async def test_no_key_at_all_is_a_clear_error(monkeypatch):
    for n in ("NVIDIA_API_KEY", "NVIDIA_API_KEY_2", "NVIDIA_API_KEY_3"):
        monkeypatch.setenv(n, "")
    monkeypatch.setattr(runner, "load_env", lambda root=None: None)  # a developer's own .env must not decide this test
    with pytest.raises(RuntimeError, match="NVIDIA_API_KEY is not set"):
        runner.ModelEndpoint(provider="nvidia", model="m")


def test_the_chat_error_carries_a_status():
    e = ChatError(409, "plain words")
    assert e.status == 409 and e.detail == "plain words"
