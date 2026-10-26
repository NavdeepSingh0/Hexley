"""Throwaway: after a nested record_scenario, which part of the OUTER stack is dead?

Run: python -m uv run python spikes/nested_probe.py
"""

import asyncio
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fastmcp import Client  # noqa: E402
from fastmcp.client.transports import StreamableHttpTransport  # noqa: E402

from sentinel.record import record_scenario  # noqa: E402
from sentinel.stack import running_stack  # noqa: E402
from sentinel.tools.server import TOKEN_HEADER  # noqa: E402


async def attempt(label, coro):
    try:
        await coro
        print(f"{label}: ok")
    except Exception as e:  # noqa: BLE001
        print(f"{label}: FAILED {type(e).__name__}: {str(e)[:90]}")


async def main():
    async with running_stack() as outer:
        async def tools_direct():
            async with Client(StreamableHttpTransport(outer.tools_url, headers={TOKEN_HEADER: "test-downstream-secret"})) as c:
                await c.list_tools()

        async def gateway_call():
            s = await outer.start_session(column="unprotected")
            async with outer.client(s["session_token"]) as c:
                await c.call_tool("read_quotation", {"quote_id": "Q-1042"})

        await attempt("before nested record: tools server direct", tools_direct())
        await attempt("before nested record: gateway call", gateway_call())
        await record_scenario("clean", {"provider": "script", "model": "x"}, 1, Path(tempfile.mkdtemp()), source="scripted")
        await attempt("after nested record: tools server direct", tools_direct())
        await attempt("after nested record: gateway call", gateway_call())


asyncio.run(main())
