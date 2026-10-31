"""The chat page shows what really happened (D-063): each tool call's real request and output, and a title from the first message. A real connector is
offered only to the officer, and only when it is running.
"""

from __future__ import annotations

import asyncio

import httpx
import pytest

from sentinel.chat import MAX_OUTPUT_SHOWN, PRESETS
from sentinel.upstreams import Upstream


async def _until_ready(api, chat_id: str) -> dict:
    for _ in range(200):
        view = (await api.get(f"/api/v1/chat/{chat_id}")).json()
        if view["status"] != "thinking":
            return view
        await asyncio.sleep(0.1)
    raise AssertionError("the chat did not answer")


async def _scripted(api, preset: str = "quotation", text: str = "Please process the quotation Q-1043.") -> dict:
    chat = (await api.post("/api/v1/chat", json={"preset": preset, "mode": "scripted"})).json()
    assert (await api.post(f"/api/v1/chat/{chat['chat_id']}/confirm")).status_code == 200
    assert (await api.post(f"/api/v1/chat/{chat['chat_id']}/messages", json={"text": text})).status_code == 202
    return await _until_ready(api, chat["chat_id"])


async def test_every_tool_call_shows_its_real_request_and_its_real_output(stack):
    async with stack.api() as api:
        view = await _scripted(api)
    actions = [a for m in view["messages"] for a in m["actions"]]
    assert actions
    first = actions[0]
    assert first["tool"] == "read_quotation" and first["args"] and "Q-1043" in (first["output"] or "")
    refused = next(a for a in actions if a["decision"] == "DENIED")
    assert refused["args"]["to"] and "Blocked" in (refused["output"] or "")  # what the agent tried to send, and what it was told


async def test_outputs_stay_paired_with_their_calls_when_one_tool_runs_twice(stack):
    from sentinel.chat import ChatManager

    class Fake:
        model_messages = [
            {"role": "assistant", "tool_calls": [{"id": "a", "function": {"name": "t"}}]}, {"role": "tool", "tool_call_id": "a", "content": "first"},
            {"role": "assistant", "tool_calls": [{"id": "b", "function": {"name": "t"}}, {"id": "c", "function": {"name": "u"}}]},
            {"role": "tool", "tool_call_id": "c", "content": "other"}, {"role": "tool", "tool_call_id": "b", "content": "second"},
        ]
    steps = [{"tool": "t", "action_id": "1"}, {"tool": "t", "action_id": "2"}, {"tool": "u", "action_id": "3"}, {"tool": "t", "action_id": "4"}]
    assert ChatManager._outputs(Fake, steps) == {"1": "first", "2": "second", "3": "other"}


def test_a_very_long_output_is_cut_for_the_page_and_says_how_much_was_cut():
    from sentinel.chat import ChatManager

    class Fake:
        model_messages = [{"role": "assistant", "tool_calls": [{"id": "a", "function": {"name": "t"}}]},
                          {"role": "tool", "tool_call_id": "a", "content": "x" * (MAX_OUTPUT_SHOWN + 5)}]
    out = ChatManager._outputs(Fake, [{"tool": "t", "action_id": "1"}])["1"]
    assert out.endswith("(5 more characters)") and len(out) < MAX_OUTPUT_SHOWN + 40


async def test_a_chat_is_titled_by_its_first_message_and_by_its_task_until_then(stack):
    async with stack.api() as api:
        chat = (await api.post("/api/v1/chat", json={"preset": "quotation", "mode": "scripted"})).json()
        assert chat["title"] == PRESETS["quotation"].title
        view = await _scripted(api, text="Please process the quotation Q-1043 today.")
    assert view["title"] == "Please process the quotation Q-1043 today."


async def test_a_real_connector_is_not_offered_when_it_is_not_running(stack):
    async with stack.api() as api:
        assert "real-github" not in {p["id"] for p in (await api.get("/api/v1/chat/presets")).json()}
        r = await api.post("/api/v1/chat", json={"preset": "real-github", "mode": "auto"})
    assert r.status_code == 404 and "not set up" in r.json()["detail"]


@pytest.fixture
def github_named(stack, monkeypatch):
    monkeypatch.setenv("SENTINEL_CHAT_REPOS", "repo:acme/test")
    monkeypatch.setattr(stack.rt.upstreams, "upstreams", [Upstream(name="github", transport="http", url="https://example.invalid/mcp")])


async def test_a_real_connector_is_offered_only_to_the_officer_and_its_slip_names_only_those_repositories(stack, github_named):
    stack.rt.public_demo = True
    try:
        async with stack.api() as api:
            assert "real-github" in {p["id"] for p in (await api.get("/api/v1/chat/presets")).json()}
            assert (await api.post("/api/v1/chat", json={"preset": "real-github", "mode": "scripted"})).status_code == 422
        async with httpx.AsyncClient(base_url=stack.api_url, timeout=30) as visitor:
            assert "real-github" not in {p["id"] for p in (await visitor.get("/api/v1/chat/presets")).json()}
            assert (await visitor.post("/api/v1/chat", json={"preset": "real-github", "mode": "auto"})).status_code == 403
    finally:
        stack.rt.public_demo = False


def test_the_real_connector_slip_template_allows_no_tool_that_can_change_a_repository_beyond_a_comment(stack):
    allowed = stack.rt.templates["chat_github"]["allowed_tools"]
    assert "github__add_issue_comment" in allowed and all(stack.rt.registry.is_known(t) for t in allowed)
    assert not {"github__create_or_update_file", "github__delete_file", "github__create_branch", "github__issue_write"} & set(allowed)
