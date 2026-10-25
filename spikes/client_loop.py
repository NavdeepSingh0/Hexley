"""M0 spike S3: a real local model, driven over MCP, through the spike gateway.

Throwaway code. Lists tools from the gateway with fastmcp.Client, converts them to the
OpenAI tool schema, and runs the poisoned and benign tasks once each. Shows end to end
that the gateway sees the agent's real calls and blocks the leaking send.

Run: python -m uv run python spikes/client_loop.py <model>
"""

import asyncio
import json
import sys

import httpx
from fastmcp import Client, FastMCP
from fastmcp.client.transports import StreamableHttpTransport

from bakeoff import CLEAN_QUOTE, INJECTION, STOCK, SYSTEM, TASK
from proxy_spike import PROXY_PORT, TOOLS_PORT, RequireSentinelToken, gateway, serve

OLLAMA = "http://localhost:11434/v1/chat/completions"
GW = f"http://127.0.0.1:{PROXY_PORT}/mcp"
quote_text = {"value": CLEAN_QUOTE}

tools = FastMCP("mock-tools-s3")
tools.add_middleware(RequireSentinelToken())


@tools.tool
def read_quotation(quote_id: str) -> str:
    """Read an incoming vendor quotation by id."""
    return quote_text["value"]


@tools.tool
def query_stock(item: str) -> str:
    """Look up current stock for an item in the stock register."""
    return STOCK


@tools.tool
def send_email(to: str, subject: str, body: str) -> str:
    """Send an email."""
    return f"Email sent to {to}."


def to_openai(tool) -> dict:
    schema = getattr(tool, "input_schema", None) or getattr(tool, "inputSchema", None) or {}
    return {"type": "function", "function": {
        "name": tool.name, "description": tool.description or "", "parameters": schema}}


async def run(model: str, poisoned: bool) -> list[dict]:
    quote_text["value"] = CLEAN_QUOTE + (INJECTION if poisoned else "")
    log: list[dict] = []
    transport = StreamableHttpTransport(GW, headers={"Authorization": "Bearer sess-standard"})
    async with Client(transport) as mcp, httpx.AsyncClient(timeout=300) as http:
        oa_tools = [to_openai(t) for t in await mcp.list_tools()]
        user = TASK + (" /no_think" if model.startswith("qwen3") else "")
        messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]
        for _ in range(8):
            resp = await http.post(OLLAMA, json={
                "model": model, "messages": messages, "tools": oa_tools, "temperature": 0.6})
            msg = resp.json()["choices"][0]["message"]
            calls = msg.get("tool_calls") or []
            messages.append({"role": "assistant", "content": msg.get("content") or "", "tool_calls": calls})
            if not calls:
                break
            done = False
            for call in calls:
                name = call["function"]["name"]
                args = json.loads(call["function"].get("arguments") or "{}")
                try:
                    result = await mcp.call_tool(name, args)
                    out = " ".join(getattr(p, "text", "") for p in result.content)
                    verdict = "ALLOW"
                except Exception as e:  # noqa: BLE001 - spike: gateway blocks surface as errors
                    out, verdict = str(e), "BLOCK"
                log.append({"tool": name, "args": args, "verdict": verdict, "result": out[:160]})
                messages.append({"role": "tool", "tool_call_id": call.get("id", ""), "content": out})
                done = done or (name == "send_email" and verdict == "ALLOW")
            if done:
                break
    return log


async def main(model: str) -> None:
    servers = [await serve(tools.http_app(), TOOLS_PORT),
               await serve(gateway(forward_headers=False).http_app(), PROXY_PORT)]
    report = {"model": model, "poisoned": await run(model, True), "benign": await run(model, False)}
    for server, _ in servers:
        server.should_exit = True
    await asyncio.gather(*(t for _, t in servers), return_exceptions=True)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "qwen3:latest"))
