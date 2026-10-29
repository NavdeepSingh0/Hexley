"""Audit log wired into the gateway: ordering, failure semantics (D-020; matrix rows 26 and 28), no secrets on
disk, and the verify / tamper API. Faults are injected at the storage layer, not by mocking the gateway."""

import asyncio
import json
import re
import time

import httpx
import pytest

from sentinel import fixtures
from sentinel.audit import read_records

SECRETS = ("2400", "1150", "FSD-14", "FSD-09", "2026-11-02", "2026-11-05")
LEAK = {"to": fixtures.VENDOR, "subject": "Re", "body": "Item A: 2400 units at FSD-14, dispatch 2026-11-02"}
CLEAN = {"to": fixtures.VENDOR, "subject": "Re", "body": "Quotation Q-1042 received."}


@pytest.fixture()
async def fault(stack):
    """Make the audit storage misbehave: mode 'all' fails every write; 'results' fails only result records."""
    log = stack.rt.audit
    original, saved_deadline = log._write_line, log.deadline
    state = {"mode": None, "seen": []}

    def patched(line):
        state["seen"].append((json.loads(line)["type"], len(stack.sink.snapshot())))
        if state["mode"] == "all" or (state["mode"] == "results" and '"type":"result"' in line):
            raise OSError("disk gone")
        original(line)

    log._write_line = patched
    yield state
    log._write_line, log.deadline = original, saved_deadline
    await log.recover()


async def call(c, tool, args):
    try:
        await c.call_tool(tool, args)
        return None
    except Exception as e:  # noqa: BLE001
        return str(e)


def delivered(stack, sid):
    return [m for m in stack.sink.snapshot() if m["session_id"] == sid]


def readable_text(value) -> str:
    """All human-readable strings in a record. Hex digests are skipped: a SHA-256 contains "2400" by chance
    often enough that scanning the raw file for secrets would be a flaky test."""
    if isinstance(value, str):
        return "" if re.fullmatch(r"[0-9a-f]{32,}", value) else value
    if isinstance(value, dict):
        return " ".join(readable_text(v) for v in value.values())
    if isinstance(value, list):
        return " ".join(readable_text(v) for v in value)
    return str(value)


# ---- normal operation -----------------------------------------------------------------------------------
async def test_a_session_leaves_a_verifiable_trail_in_order(stack):
    s = await stack.start_session()
    async with stack.client(s["session_token"]) as c:
        await c.call_tool("read_quotation", {"quote_id": "Q-1043"})
        await c.call_tool("query_stock", {"item": "all"})
        assert (await call(c, "send_email", LEAK)).startswith("Blocked")
        assert await call(c, "send_email", CLEAN) is None
    recs = [r for r in read_records(stack.rt.audit.path) if r["session_id"] == s["session_id"]]
    types = [r["type"] for r in recs]
    assert types[0] == "contract.issued"
    assert types.count("decision") == 4 and types.count("result") == 3  # the blocked send has a decision, no result
    for r in recs:  # every result follows the decision for the same action
        if r["type"] == "result":
            assert any(d["type"] == "decision" and d["action_id"] == r["action_id"] and d["seq"] < r["seq"] for d in recs)
    assert stack.rt.audit.verify().ok


async def test_the_decision_is_durable_before_the_tool_runs(stack, fault):
    s = await stack.start_session()
    async with stack.client(s["session_token"]) as c:
        assert await call(c, "send_email", CLEAN) is None
    # `fault["seen"]` records (record type, number of emails delivered so far) at the moment each record was written.
    before = [n for kind, n in fault["seen"] if kind == "decision"][-1]
    after = [n for kind, n in fault["seen"] if kind == "result"][-1]
    assert after == before + 1  # the decision was written before the email existed; the result after it was sent


async def test_no_secret_value_is_ever_written_to_the_log(stack):
    s = await stack.start_session()
    async with stack.client(s["session_token"]) as c:
        await c.call_tool("read_quotation", {"quote_id": "Q-1043"})
        await c.call_tool("query_stock", {"item": "all"})
        await call(c, "send_email", LEAK)
    records = read_records(stack.rt.audit.path)
    text = " ".join(readable_text(r) for r in records)
    for secret in SECRETS + (fixtures.VENDOR,):
        assert secret not in text, f"{secret!r} was written to the audit log"
    raw = stack.rt.audit.path.read_text(encoding="utf-8")
    assert "result_hash" in raw and "args_hash" in raw  # hashes only


async def test_the_officers_confirmation_is_the_first_record(stack):
    s = await stack.start_session()
    first = [r for r in read_records(stack.rt.audit.path) if r["session_id"] == s["session_id"]][0]
    assert first["type"] == "contract.issued" and first["payload"]["contract_hash"] == s["contract_hash"]


# ---- failure semantics ------------------------------------------------------------------------------------
async def test_row_26_audit_down_blocks_the_leak_and_the_inbox_stays_empty(stack, fault):
    s = await stack.start_session(column="sentinel")
    fault["mode"] = "all"
    async with stack.client(s["session_token"]) as c:
        for args in (LEAK, CLEAN):  # even a clean consequential send must not run without a record
            err = await call(c, "send_email", args)
            assert err is not None and err.startswith("Blocked")
    assert delivered(stack, s["session_id"]) == []


async def test_audit_outage_blocks_everything_in_sentinel_but_never_freezes_the_session(stack, fault):
    s = await stack.start_session(column="sentinel")
    fault["mode"] = "all"
    async with stack.client(s["session_token"]) as c:
        for _ in range(5):  # more than the freeze threshold
            assert "audit log" in (await call(c, "read_quotation", {"quote_id": "Q-1042"}))
    async with httpx.AsyncClient(base_url=stack.api_url, headers={"Authorization": "Bearer test-api-token"}) as api:
        assert (await api.get(f"/sessions/{s['session_id']}")).json()["status"] == "active"  # not the agent's fault
    fault["mode"] = None
    await stack.rt.audit.recover()
    async with stack.client(s["session_token"]) as c:
        await c.call_tool("read_quotation", {"quote_id": "Q-1042"})  # works again once the log is back


async def test_baseline_columns_keep_working_when_audit_is_down(stack, fault):
    s = await stack.start_session(column="r1_only")
    fault["mode"] = "all"
    async with stack.client(s["session_token"]) as c:
        assert await call(c, "send_email", CLEAN) is None  # the control column is not enforcement
    assert len(delivered(stack, s["session_id"])) == 1


async def test_a_restricted_result_is_withheld_when_its_record_cannot_be_written(stack, fault):
    s = await stack.start_session(column="sentinel")
    fault["mode"] = "results"
    async with stack.client(s["session_token"]) as c:
        err = await call(c, "query_stock", {"item": "all"})
    assert err is not None and "withheld" in err
    assert not stack.rt.store.get(s["session_id"]).index.entries  # the agent never saw it, so nothing is indexed


async def test_row_28_audit_failure_after_a_send_freezes_and_never_retries(stack, fault):
    s = await stack.start_session(column="sentinel")
    fault["mode"] = "results"  # the decision is recorded, the send runs, then the record of the result fails
    async with stack.client(s["session_token"]) as c:
        # The send runs. Afterwards the session is frozen, so the client's follow-up request is refused and
        # the agent may see an error for an action that did execute (documented, D-026): what matters is
        # that it happened once and cannot be repeated.
        await call(c, "send_email", CLEAN)
    assert len(delivered(stack, s["session_id"])) == 1
    assert stack.rt.store.get(s["session_id"]).status.value == "frozen"
    events = [e for e in stack.rt.bus.recent() if e.session_id == s["session_id"]]
    assert any(e.type == "audit.failure" for e in events) and any(e.type == "freeze" for e in events)
    fault["mode"] = None
    await stack.rt.audit.recover()
    async with stack.client(s["session_token"]) as c:
        assert await call(c, "send_email", CLEAN) is not None  # frozen: no second attempt, no duplicate email
    assert len(delivered(stack, s["session_id"])) == 1


async def test_a_slow_audit_write_blocks_within_the_deadline(stack, fault):
    s = await stack.start_session(column="sentinel")  # created while storage is still healthy
    stack.rt.audit.deadline = 0.2
    healthy = stack.rt.audit._write_line  # the `fault` fixture's wrapper; calls through to the real write

    def slow(line):
        time.sleep(0.8)
        healthy(line)

    stack.rt.audit._write_line = slow
    async with stack.client(s["session_token"]) as c:
        t0 = time.perf_counter()
        err = await call(c, "send_email", CLEAN)
        elapsed = time.perf_counter() - t0
    assert err is not None and err.startswith("Blocked") and elapsed < 1.5
    assert delivered(stack, s["session_id"]) == []
    await asyncio.sleep(0.9)  # let the late write finish before the fixture recovers the log
    stack.rt.audit._write_line = healthy


async def test_confirming_a_slip_fails_with_503_when_it_cannot_be_recorded_then_works_later(stack, fault):
    async with httpx.AsyncClient(base_url=stack.api_url, headers={"Authorization": "Bearer test-api-token"}) as api:
        draft = (await api.post("/tasks", json={"template": "quotation_processing", "officer": "x"})).json()
        fault["mode"] = "all"
        assert (await api.post(f"/tasks/{draft['contract_id']}/confirm", json={})).status_code == 503
        fault["mode"] = None
        await stack.rt.audit.recover()
        assert (await api.post(f"/tasks/{draft['contract_id']}/confirm", json={})).status_code == 200  # same draft


async def test_the_kill_switch_works_even_when_the_audit_log_is_down(stack, fault):
    s = await stack.start_session()
    fault["mode"] = "all"
    async with httpx.AsyncClient(base_url=stack.api_url, headers={"Authorization": "Bearer test-api-token"}) as api:
        assert (await api.post("/killswitch", json={"session_id": s["session_id"]})).json()["status"] == "frozen"


# ---- verify, export, tamper ---------------------------------------------------------------------------------
async def test_verify_export_and_the_tamper_demo(stack):
    async with httpx.AsyncClient(base_url=stack.api_url, headers={"Authorization": "Bearer test-api-token"}) as api:
        s = await stack.start_session()
        async with stack.client(s["session_token"]) as c:
            await c.call_tool("read_quotation", {"quote_id": "Q-1042"})
        ok = (await api.get("/audit/verify")).json()
        assert ok["ok"] and ok["checked"] > 3
        exported = (await api.get("/audit/export")).text.splitlines()
        assert len(exported) == ok["checked"] and json.loads(exported[0])["type"] == "log.genesis"

        assert (await api.post("/audit/tamper", json={"seq": 2})).status_code == 403  # off by default
        stack.rt.allow_tamper = True
        try:
            assert (await api.post("/audit/tamper", json={"seq": 2})).json()["tampered_seq"] == 2
            bad = (await api.get("/audit/verify")).json()
            assert not bad["ok"] and bad["first_bad_seq"] == 2 and "altered" in bad["reason"]
            assert (await api.post("/audit/tamper", json={"seq": 9999})).status_code == 404
            assert bad["restorable"] is True
            # D-045: the demo can put the record back and go on
            restored = await api.post("/audit/restore")
            assert restored.status_code == 200 and restored.json() == {"restored_seqs": [2]}
            good = (await api.get("/audit/verify")).json()
            assert good["ok"] and good["restorable"] is False
            assert (await api.post("/audit/restore")).status_code == 404  # nothing left to put back
        finally:
            stack.rt.allow_tamper = False
        assert (await api.post("/audit/restore")).status_code == 403  # off again: the same switch as tamper
