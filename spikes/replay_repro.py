"""Throwaway: replay a recording on a single stack, many times, and report whether it ever diverges or errors.

Run: python -m uv run python spikes/replay_repro.py [scenario] [rounds]
"""

import asyncio
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sentinel.record import record_scenario  # noqa: E402
from sentinel.stack import running_stack  # noqa: E402


async def finish(api, run_id):
    for _ in range(300):
        v = (await api.get(f"/runs/{run_id}")).json()
        if v["status"] in ("finished", "cancelled"):
            return v
        await asyncio.sleep(0.1)
    raise SystemExit("did not finish")


async def main(scenario: str, rounds: int):
    rec_dir = Path(tempfile.mkdtemp(prefix="sentinel-rec-"))
    nested = len(sys.argv) > 3 and sys.argv[3] == "nested"
    if not nested:
        await record_scenario(scenario, {"provider": "script", "model": "scripted-test"}, 1, rec_dir, source="scripted")
    async with running_stack() as stack:
        if nested:  # a second stack runs and shuts down while this one is alive (what the tests did)
            await record_scenario(scenario, {"provider": "script", "model": "scripted-test"}, 1, rec_dir, source="scripted")
        stack.rt.recordings_dir = rec_dir
        stack.rt.runs.pace = 0.0
        async with stack.api() as api:
            for i in range(rounds):
                source = sys.argv[4] if len(sys.argv) > 4 else "replay"
                r = await api.post("/runs", json={"scenario": scenario, "source": source})
                run_id = r.json()["run_id"]
                await api.post(f"/runs/{run_id}/confirm")
                v = await finish(api, run_id)
                print(f"round {i + 1}: " + ", ".join(f"{l['column']}={l['outcome']}({len(l['inbox'])} mail)" for l in v["lanes"]))


asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "poisoned", int(sys.argv[2]) if len(sys.argv) > 2 else 4))
