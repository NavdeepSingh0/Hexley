"""M0 spike S2: can a FastMCP 4.x proxy gate tool calls the way Sentinel needs?

Throwaway code. Proves (or disproves):
  C1  forward one call, block another with a custom error
  C2  middleware can read a per-session bearer token from HTTP headers
  C3  tools/list can be filtered per session (hardened mode)
  C4  downstream receives a Sentinel token the client never had,
      and a direct call without it is rejected
  C5  (finding) whether agent-supplied headers leak through to the backend

Run: python -m uv run python spikes/proxy_spike.py
"""

import asyncio
import json

import uvicorn
from fastmcp import Client, FastMCP
from fastmcp.client.transports import StreamableHttpTransport
from fastmcp.exceptions import ToolError
from fastmcp.server import create_proxy
from fastmcp.server.dependencies import get_http_headers
from fastmcp.server.middleware import Middleware
from fastmcp.server.providers.proxy import ProxyClient

TOOLS_PORT, PROXY_PORT, LEAKY_PORT = 18200, 18100, 18101
SENTINEL_TOKEN = "sentinel-minted-demo-token"
SESSIONS = {"sess-standard": "standard", "sess-hardened": "hardened"}
SECRET_VALUES = {"2400", "FSD-14"}
results: dict[str, object] = {}
backend_seen_headers: list[dict[str, str]] = []

# ---- downstream mock tools -------------------------------------------------
tools = FastMCP("mock-tools")


class RequireSentinelToken(Middleware):
    async def on_call_tool(self, context, call_next):
        headers = get_http_headers(include_all=True)
        backend_seen_headers.append({k: v for k, v in headers.items() if k.startswith("x-")})
        if headers.get("x-sentinel-token") != SENTINEL_TOKEN:
            raise ToolError("401: missing or invalid Sentinel token")
        return await call_next(context)


tools.add_middleware(RequireSentinelToken())


@tools.tool
def read_quotation(quote_id: str) -> str:
    return f"Quotation {quote_id} from vendor@shakti.example: 500 units @ 120"


@tools.tool
def query_stock(item: str) -> str:
    return f"{item}: 2400 units at depot FSD-14, dispatch 2026-11-02"


@tools.tool
def send_email(to: str, subject: str, body: str) -> str:
    return f"sent to {to}"


# ---- Sentinel gateway (spike version) ---------------------------------------
class SentinelSpikeMiddleware(Middleware):
    def _session(self) -> tuple[str, str]:
        auth = get_http_headers(include={"authorization"}).get("authorization", "")
        token = auth.removeprefix("Bearer ").strip()
        if token not in SESSIONS:
            raise ToolError("BLOCKED: no valid session token (fail closed)")
        return token, SESSIONS[token]

    async def on_list_tools(self, context, call_next):
        token, mode = self._session()
        listed = await call_next(context)
        if mode == "hardened":
            listed = [t for t in listed if t.name != "send_email"]
        results.setdefault("C2_tokens_seen", []).append(token)
        return listed

    async def on_call_tool(self, context, call_next):
        token, mode = self._session()
        name, args = context.message.name, context.message.arguments or {}
        blob = json.dumps(args)
        if name == "send_email" and any(v in blob for v in SECRET_VALUES):
            raise ToolError(f"BLOCKED (R2): SECRET register value in outbound email [session {token}]")
        return await call_next(context)


def gateway(forward_headers: bool) -> FastMCP:
    backend = ProxyClient(
        StreamableHttpTransport(
            f"http://127.0.0.1:{TOOLS_PORT}/mcp", headers={"x-sentinel-token": SENTINEL_TOKEN}
        ),
        forward_incoming_headers=forward_headers,
    )
    proxy = create_proxy(backend, name="sentinel-spike")
    proxy.add_middleware(SentinelSpikeMiddleware())
    return proxy


async def serve(app, port):
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    task = asyncio.create_task(server.serve())
    while not server.started:
        await asyncio.sleep(0.05)
    return server, task


def text_of(result) -> str:
    parts = getattr(result, "content", None) or []
    return " ".join(getattr(p, "text", str(p)) for p in parts)


async def call(url, token, tool, args, extra_headers=None):
    headers = {"Authorization": f"Bearer {token}", **(extra_headers or {})}
    async with Client(StreamableHttpTransport(url, headers=headers)) as c:
        try:
            r = await c.call_tool(tool, args)
            return "OK: " + text_of(r)
        except Exception as e:  # noqa: BLE001 - spike: record whatever comes back
            return f"ERR: {type(e).__name__}: {e}"


async def list_names(url, token):
    async with Client(StreamableHttpTransport(url, headers={"Authorization": f"Bearer {token}"})) as c:
        return sorted(t.name for t in await c.list_tools())


async def main():
    servers = [
        await serve(tools.http_app(), TOOLS_PORT),
        await serve(gateway(forward_headers=False).http_app(), PROXY_PORT),
        await serve(gateway(forward_headers=True).http_app(), LEAKY_PORT),
    ]
    gw = f"http://127.0.0.1:{PROXY_PORT}/mcp"
    leaky = f"http://127.0.0.1:{LEAKY_PORT}/mcp"
    tools_url = f"http://127.0.0.1:{TOOLS_PORT}/mcp"

    results["C1_forward_read"] = await call(gw, "sess-standard", "read_quotation", {"quote_id": "Q-1042"})
    results["C1_block_leak"] = await call(
        gw, "sess-standard", "send_email",
        {"to": "sales@shakti.example", "subject": "re: Q-1042", "body": "Stock: 2400 units at FSD-14"},
    )
    results["C1_allow_benign_send"] = await call(
        gw, "sess-standard", "send_email",
        {"to": "sales@shakti.example", "subject": "re: Q-1042", "body": "Quote received, PO to follow."},
    )
    results["C2_no_token_fail_closed"] = await call(gw, "sess-unknown", "read_quotation", {"quote_id": "Q-1"})
    results["C3_tools_standard"] = await list_names(gw, "sess-standard")
    results["C3_tools_hardened"] = await list_names(gw, "sess-hardened")
    results["C3_hardened_call_hidden_tool"] = await call(
        gw, "sess-hardened", "send_email", {"to": "x@y.example", "subject": "s", "body": "b"}
    )
    backend_seen_headers.clear()
    results["C4_via_gateway"] = await call(
        gw, "sess-standard", "read_quotation", {"quote_id": "Q-7"}, {"X-Sentinel-Token": "forged-by-agent"}
    )
    results["C4_backend_headers_secure_gateway"] = list(backend_seen_headers)
    results["C4_direct_call_no_token"] = await call(tools_url, "none", "read_quotation", {"quote_id": "Q-7"})
    backend_seen_headers.clear()
    results["C5_leaky_gateway_forged_header"] = await call(
        leaky, "sess-standard", "read_quotation", {"quote_id": "Q-8"}, {"X-Agent-Injected": "hello-backend"}
    )
    results["C5_backend_headers_leaky_gateway"] = list(backend_seen_headers)

    for server, task in servers:
        server.should_exit = True
    await asyncio.gather(*(t for _, t in servers), return_exceptions=True)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
