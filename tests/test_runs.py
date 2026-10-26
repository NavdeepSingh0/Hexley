"""Runs: scripted, replayed and (shape-only) live runs across the comparison lanes, through the real gateway.

Every number the console will show comes from these views, so these tests are the evidence that the screen cannot
show anything the gateway and mail sink did not do.
"""

import asyncio
import copy
import json
from pathlib import Path

import pytest

from sentinel import fixtures
from sentinel.record import record_scenario
from tests.conftest import API_TOKEN


@pytest.fixture(autouse=True)
async def fast(stack, tmp_path):
    runs = stack.rt.runs
    saved = (runs.pace, stack.rt.approval_wait, stack.rt.recordings_dir)
    runs.pace, stack.rt.approval_wait, stack.rt.recordings_dir = 0.0, 3.0, tmp_path / "recordings"
    yield
    for run in runs.runs.values():  # never leave a run active for the next test
        if run.status in ("running", "awaiting_confirmation"):
            await runs.cancel(run.run_id)
    await asyncio.sleep(0.05)
    runs.pace, stack.rt.approval_wait, stack.rt.recordings_dir = saved


async def finish(api, run_id, timeout=30.0):
    for _ in range(int(timeout / 0.1)):
        v = (await api.get(f"/runs/{run_id}")).json()
        if v["status"] in ("finished", "cancelled"):
            return v
        await asyncio.sleep(0.1)
    raise AssertionError("run did not finish")


async def start(api, scenario="poisoned", source="scripted", **extra):
    r = await api.post("/runs", json={"scenario": scenario, "source": source, **extra})
    assert r.status_code == 201, r.text
    run_id = r.json()["run_id"]
    c = await api.post(f"/runs/{run_id}/confirm")
    assert c.status_code == 200, c.text
    return run_id


def lane(view, column):
    return next(l for l in view["lanes"] if l["column"] == column)


# ---- the officer's step ---------------------------------------------------------------------------------------
async def test_a_run_does_nothing_until_the_officer_confirms(stack):
    async with stack.api() as api:
        v = (await api.post("/runs", json={"scenario": "poisoned", "source": "scripted"})).json()
        assert v["status"] == "awaiting_confirmation"
        assert all(l["session_id"] is None and l["status"] == "awaiting_confirmation" for l in v["lanes"])
        assert all(l["steps"] == [] and l["inbox"] == [] for l in v["lanes"])
        slip = lane(v, "sentinel")["contract"]
        assert slip["resolved_vendor"]["email"] == fixtures.VENDOR and slip["work_item_id"] == "Q-1043"
        assert (await api.get(f"/runs/{v['run_id']}")).json()["status"] == "awaiting_confirmation"
        assert not any(e.type == "session.started" for e in stack.rt.bus.recent()[-3:])
        assert (await api.post(f"/runs/{v['run_id']}/confirm")).status_code == 200
        assert (await api.post(f"/runs/{v['run_id']}/confirm")).status_code == 409  # not twice


# ---- the three-column comparison (D-028) ------------------------------------------------------------------------
async def test_scripted_poisoned_run_leaks_in_the_baselines_and_is_contained_by_sentinel(stack):
    async with stack.api() as api:
        v = await finish(api, await start(api, "poisoned"))
    un, r1, se = lane(v, "unprotected"), lane(v, "r1_only"), lane(v, "sentinel")
    for baseline in (un, r1):
        assert len(baseline["inbox"]) == 1 and baseline["inbox"][0]["oracle_leak"] is True
        assert baseline["leaked"] and baseline["outcome"] == "completed"
    assert se["inbox"] == [] and not se["leaked"] and se["outcome"] == "contained"
    last = se["steps"][-1]
    assert last["tool"] == "send_email" and last["effect"] == "BLOCK" and last["rule_ids"] == ["R2"]
    assert [s["tool"] for s in se["steps"]] == ["read_quotation", "query_stock", "send_email"]
    assert v["disclosure"].startswith("SCRIPTED") and se["badge"] == "FINGERPRINT MODE: value matching"
    assert un["badge"] is None and r1["badge"] is None  # the baselines have no mode


async def test_the_titles_are_exactly_the_wording_agreed_in_d028(stack):
    async with stack.api() as api:
        v = await finish(api, await start(api, "clean"))
    assert [l["title"] for l in v["lanes"]] == ["No policy enforcement — instrumented baseline",
                                                "R1-only access control", "Sentinel"]


async def test_the_clean_task_completes_in_every_column_with_no_false_block(stack):
    async with stack.api() as api:
        v = await finish(api, await start(api, "clean"))
    for l in v["lanes"]:
        assert l["outcome"] == "completed" and len(l["inbox"]) == 1 and not l["inbox"][0]["oracle_leak"]
        assert all(s["effect"] == "ALLOW" for s in l["steps"])


async def test_redirect_to_another_mailbox_only_sentinel_stops(stack):
    async with stack.api() as api:
        v = await finish(api, await start(api, "redirect"))
    assert len(lane(v, "unprotected")["inbox"]) == 1 and len(lane(v, "r1_only")["inbox"]) == 1
    se = lane(v, "sentinel")
    assert se["inbox"] == [] and se["steps"][-1]["rule_ids"] == ["R3"]


async def test_a_persistent_attacker_is_frozen_on_the_third_block(stack):
    async with stack.api() as api:
        v = await finish(api, await start(api, "freeze"))
    se = lane(v, "sentinel")
    assert se["outcome"] == "frozen" and se["session_status"] == "frozen" and se["inbox"] == []
    assert [s["effect"] for s in se["steps"] if s["tool"] == "send_email"] == ["BLOCK", "BLOCK", "FREEZE"]
    assert se["freeze"]["reason"] == "block threshold"
    assert len(lane(v, "unprotected")["inbox"]) == 3  # the baseline just keeps sending


async def test_the_hardened_scenario_is_its_own_two_lane_comparison(stack):
    async with stack.api() as api:
        v = await finish(api, await start(api, "hardened"))
    assert [l["badge"] for l in v["lanes"]] == ["FINGERPRINT MODE: value matching", "HARDENED MODE: structured egress"]
    fp, hd = v["lanes"]
    assert len(fp["inbox"]) == 1 and "western depot" in fp["inbox"][0]["body"]  # the declared gap, shown honestly
    assert hd["inbox"] == [] and hd["outcome"] == "frozen"
    assert not any(l["column"] == "unprotected" for l in v["lanes"])  # never mixed into the 3-column comparison


async def test_a_bank_change_is_held_for_the_officer_and_runs_after_approval(stack):
    before = len(stack.sink.bank_changes)
    async with stack.api() as api:
        run_id = await start(api, "bank_change")
        for _ in range(100):
            v = (await api.get(f"/runs/{run_id}")).json()
            if lane(v, "sentinel")["approvals"]:
                break
            await asyncio.sleep(0.05)
        card = lane(v, "sentinel")["approvals"][0]
        assert card["tool"] == "update_vendor_bank" and card["args"]["account_number"] == "111-222-333"
        for _ in range(100):  # the lanes run concurrently: wait until both baselines have acted
            if len(stack.sink.bank_changes) - before >= 2:
                break
            await asyncio.sleep(0.05)
        await asyncio.sleep(0.2)  # and give a (wrongly) unheld Sentinel call time to show itself
        assert len(stack.sink.bank_changes) - before == 2  # only the two baselines have acted; Sentinel's is held
        assert (await api.post(f"/approvals/{card['approval_id']}", json={"decision": "approve"})).status_code == 200
        v = await finish(api, run_id)
    assert len(stack.sink.bank_changes) - before == 3
    assert [s["effect"] for s in lane(v, "sentinel")["steps"]] == ["ALLOW"] and lane(v, "sentinel")["steps"][0]["held"]


# ---- scope and bookkeeping ------------------------------------------------------------------------------------------
async def test_only_one_run_is_active_at_a_time(stack):
    async with stack.api() as api:
        first = await start(api, "bank_change")  # the Sentinel lane waits for an approval
        second = (await api.post("/runs", json={"scenario": "clean", "source": "scripted"})).json()["run_id"]
        assert (await api.post(f"/runs/{second}/confirm")).status_code == 409
        await api.post(f"/runs/{first}/cancel")
        await finish(api, first)
        assert (await api.post(f"/runs/{second}/confirm")).status_code == 200
        await finish(api, second)


async def test_the_inbox_shows_only_this_runs_messages(stack):
    other = await stack.start_session(column="unprotected")  # a session outside any run
    async with stack.client(other["session_token"]) as c:
        await c.call_tool("send_email", {"to": "someone@elsewhere.example", "subject": "outside", "body": "not part of the run"})
    async with stack.api() as api:
        v = await finish(api, await start(api, "clean"))
    bodies = [m["body"] for l in v["lanes"] for m in l["inbox"]]
    assert bodies and "not part of the run" not in bodies


async def test_request_validation_and_auth(stack):
    async with stack.api() as api:
        assert (await api.post("/runs", json={"scenario": "nope", "source": "scripted"})).status_code == 404
        assert (await api.post("/runs", json={"scenario": "clean", "source": "magic"})).status_code == 422
        assert (await api.post("/runs", json={"scenario": "clean", "source": "replay"})).status_code == 404  # no recording
        assert (await api.post("/runs", json={"scenario": "clean", "source": "live"})).status_code == 422  # no model
        assert (await api.get("/runs/run_missing")).status_code == 404
        assert {s["id"] for s in (await api.get("/scenarios")).json()["scenarios"]} >= {"poisoned", "clean", "hardened"}
    import httpx
    async with httpx.AsyncClient(base_url=stack.api_url) as anon:
        assert (await anon.get("/scenarios")).status_code == 401
        assert (await anon.post("/runs", json={"scenario": "clean"})).status_code == 401


async def test_a_live_run_is_drafted_but_nothing_calls_a_model_until_confirmed(stack):
    async with stack.api() as api:
        r = await api.post("/runs", json={"scenario": "clean", "source": "live",
                                          "model": {"provider": "ollama", "model": "qwen3:latest"}})
        v = r.json()
        assert r.status_code == 201 and v["status"] == "awaiting_confirmation"
        assert v["disclosure"].startswith("LIVE") and "qwen3:latest" in v["disclosure"]
        await api.post(f"/runs/{v['run_id']}/cancel")


# ---- recording and replay -----------------------------------------------------------------------------------------------
async def test_record_keeps_every_attempt(stack, tmp_path):
    paths = await record_scenario("clean", {"provider": "script", "model": "scripted-test"}, 3, tmp_path / "rec",
                                  source="scripted", stack=stack)
    assert len(paths) == 3
    recs = [json.loads(p.read_text()) for p in paths]
    assert [(r["attempt"], r["attempts_total"]) for r in recs] == [(1, 3), (2, 3), (3, 3)]
    assert all(r["schema"] == "sentinel.recording/1" and len(r["lanes"]) == 3 for r in recs)
    assert not any("2400" in json.dumps(r["lanes"][2]) for r in recs)  # the Sentinel lane never saw a secret leave


async def make_recording(stack, scenario):
    """Record a scripted run of `scenario` into the temp recordings directory and return its parsed JSON."""
    paths = await record_scenario(scenario, {"provider": "script", "model": "scripted-test"}, 1,
                                  stack.rt.recordings_dir, source="scripted", stack=stack)
    return paths[0], json.loads(paths[0].read_text())


async def test_a_fresh_recording_replays_without_divergence(stack):
    await make_recording(stack, "poisoned")
    async with stack.api() as api:
        v = await finish(api, await start(api, "poisoned", "replay"))
    assert v["disclosure"].startswith("REPLAY") and "attempt 1 of 1" in v["disclosure"]
    assert "Sentinel decisions computed live" in v["disclosure"] and "time-compressed" in v["disclosure"]
    assert not any(l["diverged"] for l in v["lanes"])
    assert lane(v, "sentinel")["steps"][-1]["rule_ids"] == ["R2"] and lane(v, "sentinel")["inbox"] == []
    assert len(lane(v, "unprotected")["inbox"]) == 1


async def test_every_committed_recording_replays_without_divergence(stack):
    """The demo replays recordings/ on stage: today's rules must still decide exactly as they did when it was recorded."""
    committed = Path(__file__).resolve().parents[1] / "recordings"
    files = sorted(committed.glob("*.json"))
    assert files, "no committed recordings to replay"
    stack.rt.recordings_dir = committed
    async with stack.api() as api:
        for f in files:
            rec = json.loads(f.read_text(encoding="utf-8"))
            v = await finish(api, await start(api, rec["scenario"], "replay", recording_id=f.stem), timeout=60.0)
            assert not any(l["diverged"] for l in v["lanes"]), f.name
            # A lane that ended in agent_error when recorded (the model API failed) has no model to fail on replay: it
            # replays the steps it did make and ends "completed". Every other outcome must reproduce exactly.
            for replayed, recorded in zip(v["lanes"], rec["lanes"], strict=True):
                if recorded["outcome"]["lane_outcome"] != "agent_error":
                    assert replayed["outcome"] == recorded["outcome"]["lane_outcome"], f.name


async def test_a_replay_whose_decision_differs_stops_instead_of_replaying_blind(stack):
    path, rec = await make_recording(stack, "freeze")
    tampered = copy.deepcopy(rec)
    # Change the Sentinel lane's first send so it no longer leaks: the live decision will be ALLOW, the recording says BLOCK.
    sentinel = next(l for l in tampered["lanes"] if l["column"] == "sentinel")
    sentinel["steps"][2]["args"]["body"] = "Quotation received."
    path.write_text(json.dumps(tampered), encoding="utf-8")
    async with stack.api() as api:
        v = await finish(api, await start(api, "freeze", "replay"))
    se = lane(v, "sentinel")
    assert se["outcome"] == "diverged" and se["diverged"]["step"] == 2
    assert se["diverged"]["recorded"]["effect"] == "BLOCK" and se["diverged"]["live"]["effect"] == "ALLOW"
    assert len(se["steps"]) == 3  # steps after the divergence were never issued
    assert any(e.type == "replay.diverged" and e.payload["step"] == 2 for e in stack.rt.bus.recent())
    # the untouched lanes still replayed as recorded
    assert lane(v, "unprotected")["outcome"] == "completed" and len(lane(v, "unprotected")["inbox"]) == 3


async def test_recordings_are_listed_and_a_specific_one_can_be_chosen(stack):
    path, rec = await make_recording(stack, "clean")
    async with stack.api() as api:
        listing = (await api.get("/recordings")).json()["recordings"]
        assert [r["recording_id"] for r in listing] == [path.stem] and listing[0]["attempts_total"] == 1
        v = await finish(api, await start(api, "clean", "replay", recording_id=path.stem))
        assert v["status"] == "finished"
        assert (await api.post("/runs", json={"scenario": "clean", "source": "replay", "recording_id": "nope"})).status_code == 404


async def test_run_lifecycle_events_are_published(stack):
    async with stack.api() as api:
        run_id = await start(api, "clean")
        await finish(api, run_id)
    types = [e.type for e in stack.rt.bus.recent() if e.payload.get("run_id") == run_id]
    assert types[0] == "run.created" and "run.started" in types and types.count("lane.finished") == 3
    assert types[-1] == "run.finished"
