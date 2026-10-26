"""Shared fixtures: a full in-process Sentinel stack on ephemeral ports (tools, gateway, API)."""

import asyncio
import socket
import tempfile
from dataclasses import dataclass
from pathlib import Path

import httpx
import pytest_asyncio
import uvicorn
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

from sentinel.api import create_api
from sentinel.gateway import build_gateway
from sentinel.runtime import Runtime, build_runtime
from sentinel.tools.server import MailSink, build_tools_server

API_TOKEN = "test-api-token"
DOWNSTREAM_TOKEN = "test-downstream-secret"


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

    async def start_session(self, column="sentinel", mode="fingerprint", template="quotation_processing") -> dict:
        async with httpx.AsyncClient(base_url=self.api_url, headers={"Authorization": f"Bearer {API_TOKEN}"}) as c:
            draft = (await c.post("/tasks", json={"template": template, "officer": "Col. R. Menon", "mode": mode})).json()
            r = await c.post(f"/tasks/{draft['contract_id']}/confirm", json={"column": column})
            r.raise_for_status()
            return r.json()

    def client(self, session_token: str, headers: dict | None = None) -> Client:
        return Client(StreamableHttpTransport(
            self.gateway_url, headers={"Authorization": f"Bearer {session_token}", **(headers or {})}))


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def stack():
    ports = {k: free_port() for k in ("tools", "gateway", "api")}
    tools_url = f"http://127.0.0.1:{ports['tools']}/mcp"
    gateway_url = f"http://127.0.0.1:{ports['gateway']}/mcp"
    audit_dir = tempfile.mkdtemp(prefix="sentinel-audit-")
    rt = build_runtime(tools_url=tools_url, gateway_url=gateway_url, downstream_token=DOWNSTREAM_TOKEN,
                       api_token=API_TOKEN, audit_dir=Path(audit_dir))
    tools, sink = build_tools_server(DOWNSTREAM_TOKEN)
    started = [await serve(tools.http_app(), ports["tools"]),
               await serve(build_gateway(rt).http_app(), ports["gateway"]),
               await serve(create_api(rt), ports["api"])]
    yield Stack(rt=rt, sink=sink, api_url=f"http://127.0.0.1:{ports['api']}", gateway_url=gateway_url,
                tools_url=tools_url)
    for server, _ in started:
        server.should_exit = True
    await asyncio.gather(*(t for _, t in started), return_exceptions=True)
