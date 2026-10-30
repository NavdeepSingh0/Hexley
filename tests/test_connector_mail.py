"""Plan F2d: the mail connector's preset and its attack, offline.

Offline means the server is `tests/fakes/fake_mail.py`, with the tool names and arguments of mcp-mail-server 2.1.2. Its tool
list was captured with dummy settings (tests/fixtures/mail_tools_v2.1.2.json); it has not yet touched a real mailbox.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
import pytest_asyncio

from sentinel.models import Capability, ToolEntry
from sentinel.registry import load_registry
from sentinel.stack import running_stack
from sentinel.upstreams import UpstreamSet, load_upstreams
from tests.fakes import fake_mail as fm

APP_PASSWORD = "abcd-efgh-ijkl-mnop-test"  # a test value, not a credential
TOOLS = ["gmail__get_message", "gmail__check_connection", "gmail__send_email"]


@pytest_asyncio.fixture(scope="module")
async def mail(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("mail")
    sink = tmp / "sent.jsonl"
    config = tmp / "upstreams.yaml"
    config.write_text(json.dumps({"upstreams": [{
        "name": "gmail", "transport": "stdio", "command": "python", "args": [str(Path(fm.__file__)), str(sink)],
        "env": {"EMAIL_USER": "${GMAIL_ADDRESS}", "EMAIL_PASS": "${GMAIL_APP_PASSWORD}"},
        "public_vars": ["GMAIL_ADDRESS"]}]}), encoding="utf-8")
    ups = UpstreamSet.load(config, tmp / "none", environ={"GMAIL_ADDRESS": fm.ACCOUNT, "GMAIL_APP_PASSWORD": APP_PASSWORD})
    async with running_stack(upstreams=ups, approval_wait=20.0) as s:
        s.rt.registry.add(ToolEntry(name="gmail__debug_config", capability="read", resource_class="test", outbound=False,
                                    consequential=False, output_integrity="trusted", output_confidentiality="internal"))
        yield s, sink


async def _slip(stack, tools=TOOLS, **over) -> dict:
    body = {"objective": "Process the inbox for the team", "confirm": True, "allowed_tools": tools,
            "allowed_destinations": [fm.BOSS, "team.example"], "internal_destinations": [fm.BOSS], "max_messages": 5, **over}
    async with stack.api() as api:
        r = await api.post("/api/v1/slips", json=body)
        assert r.status_code == 201, r.text
        return r.json()


def _sent(sink: Path) -> list[dict]:
    return [json.loads(x) for x in sink.read_text(encoding="utf-8").splitlines()] if sink.exists() else []


def _token(slip: dict) -> str:
    return slip["header_value"].removeprefix("Bearer ")


async def _read_poison(c) -> None:
    result = await c.call_tool("gmail__get_message", {"mailbox": "INBOX", "uid": 1})
    assert fm.ATTACKER in result.content[0].text  # the hidden instruction reached the agent


# ---- the attack: a hidden instruction in a mail -----------------------------------------------------------------------
async def test_the_attackers_address_is_refused(mail):
    stack, sink = mail
    before = _sent(sink)
    async with stack.client(_token(await _slip(stack))) as c:
        await _read_poison(c)
        with pytest.raises(Exception, match="Blocked"):
            await c.call_tool("gmail__send_email", {"to": fm.ATTACKER, "subject": "x", "text": "payroll"})
    assert _sent(sink) == before


async def test_a_blind_copy_to_the_attacker_is_refused(mail):
    stack, sink = mail
    before = _sent(sink)
    async with stack.client(_token(await _slip(stack))) as c:
        with pytest.raises(Exception, match="Blocked"):
            await c.call_tool("gmail__send_email", {"to": fm.BOSS, "subject": "x", "text": "hello", "bcc": fm.ATTACKER})
    assert _sent(sink) == before


async def test_payroll_values_to_an_allowed_domain_that_is_not_internal_are_refused(mail):
    stack, sink = mail
    before = _sent(sink)
    async with stack.client(_token(await _slip(stack))) as c:
        await c.call_tool("gmail__get_message", {"mailbox": "INBOX", "uid": 2})
        with pytest.raises(Exception, match="restricted data"):
            await c.call_tool("gmail__send_email", {"to": "ops@team.example", "subject": "x", "text": "A. Rao 1840500"})
    assert _sent(sink) == before


async def test_an_address_found_only_in_a_mail_is_refused_even_inside_an_allowed_domain(mail):
    stack, sink = mail
    before = _sent(sink)
    async with stack.client(_token(await _slip(stack))) as c:
        await _read_poison(c)
        with pytest.raises(Exception, match="appears only inside"):
            await c.call_tool("gmail__send_email", {"to": fm.COLLEAGUE, "subject": "x", "text": "hello"})
    assert _sent(sink) == before


async def test_a_reply_tool_with_no_recipient_cannot_be_put_on_a_slip_or_called(mail):
    stack, sink = mail
    before = _sent(sink)
    async with stack.api() as api:
        r = await api.post("/api/v1/slips", json={"objective": "Answer the mail", "allowed_tools": ["gmail__reply_to_email"],
                                                  "allowed_destinations": ["team.example"], "max_messages": 1})
        assert r.status_code == 422 and "not a classified tool" in r.text
    async with stack.client(_token(await _slip(stack))) as c:
        assert "gmail__reply_to_email" not in {t.name for t in await c.list_tools()}
        with pytest.raises(Exception, match="Blocked"):
            await c.call_tool("gmail__reply_to_email", {"mailbox": "INBOX", "originalUid": 1, "text": "payroll"})
    assert _sent(sink) == before


# ---- the honest task still runs ---------------------------------------------------------------------------------------
async def test_an_address_the_officer_wrote_out_is_usable_even_though_the_mail_mentions_it(mail):
    stack, sink = mail
    note = {"to": fm.BOSS, "subject": "Quote 1042", "text": "A quote arrived from a supplier."}
    async with stack.client(_token(await _slip(stack))) as c:
        await _read_poison(c)  # its Cc line names the boss
        await c.call_tool("gmail__send_email", note)
    assert {"tool": "send", "cc": "", "bcc": "", **note} in _sent(sink)


async def test_after_a_mail_an_outside_send_on_the_slip_waits_for_the_officer(mail):
    stack, sink = mail
    args = {"to": fm.BOSS, "subject": "Quote", "text": "Reviewed."}
    slip = await _slip(stack, internal_destinations=[])
    async with stack.client(_token(slip)) as c:
        await _read_poison(c)
        call = asyncio.create_task(c.call_tool("gmail__send_email", args))
        for _ in range(300):
            found = [a for a in stack.rt.approvals.pending() if a.session_id == slip["session_id"]]
            if found:
                break
            await asyncio.sleep(0.02)
        assert found
        stack.rt.approvals.resolve(found[0].approval_id, True)
        await call
    assert any(x.get("subject") == "Quote" for x in _sent(sink))


# ---- credentials ------------------------------------------------------------------------------------------------------
async def test_results_naming_the_accounts_address_are_not_withheld(mail):
    stack, _ = mail
    async with stack.client(_token(await _slip(stack))) as c:
        result = await c.call_tool("gmail__check_connection", {})
    assert fm.ACCOUNT in result.content[0].text


async def test_a_result_printing_the_app_password_is_withheld(mail):
    stack, _ = mail
    async with stack.client(_token(await _slip(stack, tools=["gmail__debug_config"], allowed_destinations=[], internal_destinations=[]))) as c:
        with pytest.raises(Exception, match="credential Sentinel holds"):
            await c.call_tool("gmail__debug_config", {})
    assert APP_PASSWORD not in stack.rt.audit.export_lines()


# ---- the preset -------------------------------------------------------------------------------------------------------
_REG = load_registry()
# Captured from the real package with dummy settings.
REAL = {t["name"]: t for t in json.loads((Path(__file__).parent / "fixtures" / "mail_tools_v2.1.2.json").read_text(encoding="utf-8"))}
LEFT_OUT = {"reply_to_email", "continue_email_thread", "move_message", "move_messages", "delete_message", "delete_messages",
            "save_attachment"}


def test_the_preset_covers_only_real_tools_and_leaves_out_the_unsafe_ones():
    preset = {n.removeprefix("gmail__") for n in _REG.names() if n.startswith("gmail__")}
    assert preset == set(REAL) - LEFT_OUT


def test_the_reply_tools_really_have_no_recipient_and_send_email_really_has_one():
    for name in ("reply_to_email", "continue_email_thread"):
        assert "to" not in REAL[name]["input_schema"]["properties"]
    props = REAL["send_email"]["input_schema"]["properties"]
    assert {"to", "cc", "bcc"} <= set(props) and "to" in REAL["send_email"]["input_schema"]["required"]


def test_every_mailbox_read_is_untrusted_and_restricted():
    for name in ("search_messages", "find_unreplied_messages", "get_message", "get_messages"):
        entry = _REG.get(f"gmail__{name}")
        assert entry.capability == Capability.READ and entry.output_integrity == "untrusted"
        assert entry.output_confidentiality == "restricted" and entry.fingerprint_fields == ["all"]


def test_the_shipped_mail_connector_is_pinned_and_keeps_its_file_access_off():
    gmail = next(u for u in load_upstreams() if u.name == "gmail")
    assert "mcp-mail-server@2.1.2" in gmail.args and "MAIL_ALLOWED_ROOTS" not in gmail.env
    assert gmail.public_vars == ["GMAIL_ADDRESS"] and "GMAIL_APP_PASSWORD" in gmail.variables()
