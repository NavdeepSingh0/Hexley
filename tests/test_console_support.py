"""Backend support for the console (plan Part 3a): the view contract, run listing, honest inbox flag, safe tamper
demo, log rotation, serving the build. Own module (own stack) because the tamper test deliberately corrupts the log."""

import asyncio

import httpx
import pytest
from fastapi import FastAPI

from sentinel.api import mount_console
from sentinel.audit import AuditLog, AuditError
from sentinel.runtime import build_runtime, rotate_audit_log
from sentinel.record import record_scenario

TOP_KEYS = {"run_id", "scenario", "source", "status", "disclosure", "model", "officer", "created", "lanes",
            "audit_head", "inbox_ok"}
LANE_KEYS = {"lane_id", "column", "title", "mode", "badge", "session_id", "status", "outcome", "leaked",
             "session_status", "blocks", "steps", "freeze", "approvals", "contract", "task", "final_text", "error",
             "diverged", "inbox"}
CONTRACT_KEYS = {"objective", "allowed_tools", "allowed_recipient_domains", "work_item_id", "resolved_vendor", "mode",
                 "max_messages", "contract_hash", "egress_template"}
STEP_KEYS = {"action_id", "tool", "args", "ts", "effect", "rule_ids", "reason_code", "summary", "evidence",
             "latency_ms", "held", "approval", "completed", "rendered"}
INBOX_KEYS = {"session_id", "to", "subject", "body", "ts", "column", "oracle_leak"}


@pytest.fixture(autouse=True)
async def fast(stack, tmp_path):
    runs = stack.rt.runs
    saved = (runs.pace, stack.rt.approval_wait, stack.rt.recordings_dir)
    runs.pace, stack.rt.approval_wait, stack.rt.recordings_dir = 0.0, 3.0, tmp_path / "recordings"
    yield
    for run in runs.runs.values():
        if run.status in ("running", "awaiting_confirmation"):
            await runs.cancel(run.run_id)
    await asyncio.sleep(0.05)
    runs.pace, stack.rt.approval_wait, stack.rt.recordings_dir = saved


async def run_to_end(api, scenario, source="scripted"):
    run_id = (await api.post("/runs", json={"scenario": scenario, "source": source})).json()["run_id"]
    await api.post(f"/runs/{run_id}/confirm")
    for _ in range(300):
        v = (await api.get(f"/runs/{run_id}")).json()
        if v["status"] in ("finished", "cancelled"):
            return v
        await asyncio.sleep(0.1)
    raise AssertionError("run did not finish")


# ---- the contract the console depends on ---------------------------------------------------------------------------
async def test_the_run_view_has_exactly_the_keys_the_console_reads(stack):
    async with stack.api() as api:
        v = await run_to_end(api, "poisoned")
        h = await run_to_end(api, "hardened")
    assert set(v) == TOP_KEYS and v["inbox_ok"] is True
    for lane in v["lanes"] + h["lanes"]:
        assert set(lane) == LANE_KEYS and set(lane["contract"]) == CONTRACT_KEYS
        assert all(set(s) == STEP_KEYS for s in lane["steps"])
        assert all(set(m) == INBOX_KEYS for m in lane["inbox"])
    assert v["lanes"][2]["contract"]["egress_template"] is None  # free-text slips have no fixed message
    hardened = h["lanes"][1]["contract"]["egress_template"]
    assert hardened["body"].startswith("Quotation {quote_id} received") and "{quote_id}" in hardened["subject"]


async def test_decided_steps_carry_a_measured_latency(stack):
    async with stack.api() as api:
        v = await run_to_end(api, "clean")
    steps = [s for l in v["lanes"] for s in l["steps"]]
    assert steps and all(isinstance(s["latency_ms"], float) and s["latency_ms"] >= 0 for s in steps)


async def test_an_unreadable_mail_sink_is_flagged_not_shown_as_empty(stack):
    async with stack.api() as api:
        v = await run_to_end(api, "clean")
        good_url = stack.rt.tools_url
        stack.rt.tools_url = "http://127.0.0.1:9/mcp"  # nothing listens here
        try:
            broken = (await api.get(f"/runs/{v['run_id']}")).json()
        finally:
            stack.rt.tools_url = good_url
        assert broken["inbox_ok"] is False and all(l["inbox"] == [] for l in broken["lanes"])
        assert (await api.get(f"/runs/{v['run_id']}")).json()["inbox_ok"] is True


async def test_runs_can_be_listed_so_a_reload_can_reattach(stack):
    async with stack.api() as api:
        run_id = (await api.post("/runs", json={"scenario": "bank_change", "source": "scripted"})).json()["run_id"]
        await api.post(f"/runs/{run_id}/confirm")
        listing = (await api.get("/runs")).json()
        assert listing["active"] == run_id
        assert {"run_id": run_id, "scenario": "bank_change", "source": "scripted", "status": "running"}.items() <= \
            next(r for r in listing["runs"] if r["run_id"] == run_id).items()
        await api.post(f"/runs/{run_id}/cancel")
        await asyncio.sleep(0.3)
        assert (await api.get("/runs")).json()["active"] is None


async def test_recordings_show_each_lanes_outcome_before_you_choose(stack):
    await record_scenario("clean", {"provider": "script", "model": "scripted-test"}, 2, stack.rt.recordings_dir,
                          source="scripted", stack=stack)
    async with stack.api() as api:
        rec = (await api.get("/recordings")).json()["recordings"]
    assert len(rec) == 2
    for r in rec:
        assert [l["column"] for l in r["lanes"]] == ["unprotected", "r1_only", "sentinel"]
        assert all({"outcome", "oracle_leak"} <= set(l) for l in r["lanes"]) and r["lanes"][0]["outcome"] == "completed"


async def test_r3_evidence_names_the_tool_whose_result_held_the_address(stack):
    async with stack.api() as api:
        v = await run_to_end(api, "redirect")
    blocked = next(s for s in v["lanes"][2]["steps"] if s["tool"] == "send_email")
    assert blocked["rule_ids"] == ["R3"]
    assert [e["source_ref"] for e in blocked["evidence"] if e["kind"] == "provenance"] == ["read_quotation"]


# ---- serving the build ------------------------------------------------------------------------------------------------
async def test_the_console_build_is_served_and_a_missing_build_is_a_404_not_a_crash(tmp_path):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<html><title>Sentinel console</title></html>", encoding="utf-8")
    present, missing = FastAPI(), FastAPI()
    mount_console(present, dist)
    mount_console(missing, tmp_path / "nothing-here")
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=present), base_url="http://t") as c:
        r = await c.get("/console/")
        assert r.status_code == 200 and "Sentinel console" in r.text
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=missing), base_url="http://t") as c:
        assert (await c.get("/console/")).status_code == 404


# ---- log rotation (a rehearsal must never stop the real demo from starting) ---------------------------------------------
def test_a_tampered_log_blocks_startup_until_it_is_rotated_aside(tmp_path):
    kw = dict(tools_url="http://x/mcp", gateway_url="http://x/mcp", downstream_token="d", api_token="a",
              audit_dir=tmp_path)
    rt = build_runtime(**kw)
    asyncio.run(rt.audit.append("decision", payload={"x": 1}))
    rt.audit.tamper(1)  # what the demo's tamper button does to the file
    with pytest.raises(AuditError):
        build_runtime(**kw)  # refused: exactly the rehearsal-then-demo-day failure
    moved = rotate_audit_log(tmp_path)
    assert moved is not None and moved.exists() and not (tmp_path / "audit.jsonl").exists()
    assert build_runtime(**kw).audit.verify().ok  # a fresh, valid chain
    assert rotate_audit_log(tmp_path / "nowhere") is None


# ---- the tamper demo (last: it corrupts this module's log on purpose) ------------------------------------------------------
async def test_tamper_with_no_seq_alters_the_blocked_decision_and_verify_names_it(stack):
    async with stack.api() as api:
        v = await run_to_end(api, "poisoned")
        blocked = next(s for s in v["lanes"][2]["steps"] if s["effect"] == "BLOCK")
        assert (await api.get("/audit/verify")).json()["tamper_enabled"] is False
        assert (await api.post("/audit/tamper")).status_code == 403
        stack.rt.allow_tamper = True
        try:
            assert (await api.get("/audit/verify")).json()["ok"] is True
            t = (await api.post("/audit/tamper")).json()  # no seq: the audience just watched this block
            assert t["action_id"] == blocked["action_id"]
            bad = (await api.get("/audit/verify")).json()
            assert bad["ok"] is False and bad["first_bad_seq"] == t["tampered_seq"] and "altered" in bad["reason"]
        finally:
            stack.rt.allow_tamper = False


async def test_tamper_with_no_block_on_record_is_a_404(tmp_path):
    from sentinel.stack import running_stack

    async with running_stack(audit_dir=tmp_path, allow_tamper=True) as s:
        async with s.api() as api:
            assert (await api.post("/audit/tamper")).status_code == 404
