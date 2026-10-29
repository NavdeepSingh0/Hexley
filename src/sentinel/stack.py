"""A complete in-process Sentinel stack (tool server, gateway, API) on ephemeral ports.

Used by the tests, by `python -m sentinel record` and by `python -m sentinel eval`, so every one of them
exercises the real gateway over real HTTP and reads what actually reached the mail sink.
"""

from __future__ import annotations

import asyncio
import socket
import tempfile
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path

import httpx
import uvicorn
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

from .api import create_api
from .gateway import build_gateway
from .runtime import Runtime, build_runtime
from .tools.server import MailSink, build_tools_server


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


async def serve(app, port: int) -> tuple[uvicorn.Server, asyncio.Task]:
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    task = asyncio.create_task(server.serve())
    while not server.started:
        await asyncio.sleep(0.02)
    return server, task


@dataclass
class Stack:
    rt: Runtime
    sink: MailSink
    api_url: str
    gateway_url: str
    tools_url: str
    api_token: str = "test-api-token"

    def api(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(base_url=self.api_url, headers={"Authorization": f"Bearer {self.api_token}"},
                                 timeout=30)

    async def start_session(self, column="sentinel", mode=None, template="quotation_processing",
                            work_item_id=None) -> dict:
        body = {"template": template, "officer": "Col. R. Menon"}
        if mode:
            body["mode"] = mode
        if work_item_id:
            body["work_item_id"] = work_item_id
        async with self.api() as c:
            draft = (await c.post("/tasks", json=body)).json()
            r = await c.post(f"/tasks/{draft['contract_id']}/confirm", json={"column": column})
            r.raise_for_status()
            return r.json()

    def client(self, session_token: str, headers: dict | None = None) -> Client:
        return Client(StreamableHttpTransport(
            self.gateway_url, headers={"Authorization": f"Bearer {session_token}", **(headers or {})}))


@asynccontextmanager
async def running_stack(api_token: str = "test-api-token", downstream_token: str = "test-downstream-secret",
                        audit_dir: Path | None = None, oauth: dict | bool = False, **runtime_kwargs):
    """Start tool server, gateway and API; yield a Stack; shut everything down afterwards.

    `oauth=True` (or a dict of SentinelOAuthProvider options) turns on the OAuth sign-in on the gateway, whose public
    address is then its own local one."""
    ports = {k: free_port() for k in ("tools", "gateway", "api")}
    tools_url = f"http://127.0.0.1:{ports['tools']}/mcp"
    gateway_url = f"http://127.0.0.1:{ports['gateway']}/mcp"
    audit_dir = audit_dir or Path(tempfile.mkdtemp(prefix="sentinel-audit-"))
    rt = build_runtime(tools_url=tools_url, gateway_url=gateway_url, downstream_token=downstream_token,
                       api_token=api_token, audit_dir=audit_dir, **runtime_kwargs)
    if oauth:
        from .oauth import SentinelOAuthProvider

        rt.oauth = SentinelOAuthProvider(rt, base_url=f"http://127.0.0.1:{ports['gateway']}",
                                         **(oauth if isinstance(oauth, dict) else {}))
    tools, sink = build_tools_server(downstream_token, rt.uploads_dir)
    started = [await serve(tools.http_app(), ports["tools"]),
               await serve(build_gateway(rt).http_app(), ports["gateway"]),
               await serve(create_api(rt), ports["api"])]
    try:
        # Known limitation (D-033): do not start a second stack in this process while another is serving
        # concurrent lanes; an inner stack shutting down was seen to break the outer one. Production runs one
        # stack per process (`up`, `record`, `eval`), so this only affects tests that nest stacks.
        yield Stack(rt=rt, sink=sink, api_url=f"http://127.0.0.1:{ports['api']}", gateway_url=gateway_url,
                    tools_url=tools_url, api_token=api_token)
    finally:
        for server, _ in started:
            server.should_exit = True
        await asyncio.gather(*(t for _, t in started), return_exceptions=True)
