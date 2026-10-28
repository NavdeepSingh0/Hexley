"""Capture real GET /runs/{id} views as console test fixtures.

The console's tests run against exactly what the backend produces, never hand-written JSON.
Run (from the repo root): python -m uv run python spikes/capture_fixtures.py
Writes console/src/fixtures/*.json.
"""

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sentinel.stack import running_stack  # noqa: E402

OUT = ROOT / "console" / "src" / "fixtures"


async def finish(api, run_id, timeout=60):
    for _ in range(timeout * 10):
        v = (await api.get(f"/runs/{run_id}")).json()
        if v["status"] in ("finished", "cancelled"):
            return v
        await asyncio.sleep(0.1)
    raise SystemExit("run did not finish")


async def main():
    OUT.mkdir(parents=True, exist_ok=True)
    async with running_stack(allow_tamper=True) as stack:
        stack.rt.runs.pace = 0.0
        stack.rt.approval_wait = 30.0
        async with stack.api() as api:
            for scenario in ("poisoned", "clean", "redirect", "stranger", "freeze", "hardened", "compromised_pdf",
                             "poisoned_web"):
                run_id = (await api.post("/runs", json={"scenario": scenario, "source": "scripted"})).json()["run_id"]
                if scenario == "poisoned":  # the slip screen, before the officer confirms
                    (OUT / "poisoned_awaiting.json").write_text(json.dumps((await api.get(f"/runs/{run_id}")).json(), indent=2))
                await api.post(f"/runs/{run_id}/confirm")
                v = await finish(api, run_id)
                (OUT / f"{scenario}.json").write_text(json.dumps(v, indent=2))
                print("captured", scenario, [l["outcome"] for l in v["lanes"]])
            run_id = (await api.post("/runs", json={"scenario": "bank_change", "source": "scripted"})).json()["run_id"]
            await api.post(f"/runs/{run_id}/confirm")
            for _ in range(200):
                v = (await api.get(f"/runs/{run_id}")).json()
                if v["lanes"][2]["approvals"]:
                    break
                await asyncio.sleep(0.05)
            await asyncio.sleep(0.4)  # let the baseline lanes finish their changes
            v = (await api.get(f"/runs/{run_id}")).json()
            (OUT / "bank_change_waiting.json").write_text(json.dumps(v, indent=2))
            await api.post(f"/approvals/{v['lanes'][2]['approvals'][0]['approval_id']}", json={"decision": "approve"})
            v = await finish(api, run_id)
            (OUT / "bank_change_done.json").write_text(json.dumps(v, indent=2))
            print("captured bank_change", [l["outcome"] for l in v["lanes"]])
            (OUT / "verify_ok.json").write_text(json.dumps((await api.get("/audit/verify")).json(), indent=2))
            await api.post("/audit/tamper")
            (OUT / "verify_tampered.json").write_text(json.dumps((await api.get("/audit/verify")).json(), indent=2))
            print("captured verify (intact and tampered)")


asyncio.run(main())
