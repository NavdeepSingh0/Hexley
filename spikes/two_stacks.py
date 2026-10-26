"""Throwaway: what, exactly, makes a second in-process Sentinel stack break the first when it shuts down?

Run: python -m uv run python spikes/two_stacks.py <variant>
  idle        inner stack starts and stops without any traffic
  calls       inner stack serves sequential calls, then stops
  concurrent  inner stack serves three concurrent sessions, then stops
  record      inner stack runs a full scripted run via the RunManager (what `record` does), then stops
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sentinel.stack import running_stack  # noqa: E402


async def probe(stack, label):
    s = await stack.start_session(column="unprotected")
    try:
        async with stack.client(s["session_token"]) as c:
            await c.call_tool("read_quotation", {"quote_id": "Q-1042"})
        print(f"{label}: ok")
    except Exception as e:  # noqa: BLE001
        print(f"{label}: FAILED {type(e).__name__}: {str(e)[:90]}")


async def one_session(stack):
    s = await stack.start_session(column="unprotected")
    async with stack.client(s["session_token"]) as c:
        await c.call_tool("read_quotation", {"quote_id": "Q-1042"})


async def main(variant: str):
    async with running_stack() as outer:
        async with running_stack() as inner:
            if variant == "calls":
                await one_session(inner)
                await one_session(inner)
            elif variant == "concurrent":
                await asyncio.gather(*(one_session(inner) for _ in range(3)))
            elif variant == "record":
                async with inner.api() as api:
                    run_id = (await api.post("/runs", json={"scenario": "poisoned", "source": "scripted"})).json()["run_id"]
                    await api.post(f"/runs/{run_id}/confirm")
                    for _ in range(100):
                        if (await api.get(f"/runs/{run_id}")).json()["status"] != "running":
                            break
                        await asyncio.sleep(0.1)
        await asyncio.sleep(0.3)
        print(f"[{variant}] inner stack has shut down")
        await probe(outer, f"[{variant}] outer after inner shut down")
        try:  # three sessions at once, as the lanes of a run do
            await asyncio.gather(*(one_session(outer) for _ in range(3)))
            print(f"[{variant}] outer, three concurrent sessions: ok")
        except Exception as e:  # noqa: BLE001
            print(f"[{variant}] outer, three concurrent sessions: FAILED {type(e).__name__}: {str(e)[:80]}")


asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "idle"))
