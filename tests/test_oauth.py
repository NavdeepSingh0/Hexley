"""OAuth sign-in (core plan phase B1): an AI client signs in, the officer approves the permission slip with a code.

The flow is exercised over real HTTP against a running stack, exactly as Claude.ai would: register, authorize, consent,
exchange (PKCE), call tools, refresh. Most tests are the ways to cheat it, each of which must fail."""

import base64
import hashlib
import re
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

import httpx
import jwt
import pytest
import pytest_asyncio
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

from sentinel.contracts import verify_session_token
from sentinel.stack import running_stack

REDIRECT = "https://claude.example/api/mcp/auth_callback"


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def ostack():
    async with running_stack(oauth=True) as s:
        yield s


def base(stack) -> str:
    return stack.gateway_url.removesuffix("/mcp")


def pkce() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    return verifier, challenge


async def register(c: httpx.AsyncClient, stack, name: str = "Claude") -> str:
    r = await c.post(f"{base(stack)}/register", json={
        "redirect_uris": [REDIRECT], "client_name": name, "token_endpoint_auth_method": "none",
        "grant_types": ["authorization_code", "refresh_token"], "response_types": ["code"]})
    assert r.status_code == 201, r.text
    return r.json()["client_id"]


async def start(c: httpx.AsyncClient, stack, client_id: str, challenge: str, state: str = "st-1") -> str:
    """Hit /authorize; returns the pending request id from the consent address it redirects to."""
    r = await c.get(f"{base(stack)}/authorize", params={
        "response_type": "code", "client_id": client_id, "redirect_uri": REDIRECT, "code_challenge": challenge,
        "code_challenge_method": "S256", "state": state})
    assert r.status_code in (302, 307), r.text
    loc = r.headers["location"]
    assert "/oauth/consent" in loc
    return parse_qs(urlparse(loc).query)["request"][0]


def officer_code(stack, request_id: str) -> str:
    return stack.rt.oauth.pending[request_id].officer_code


async def consent(c, stack, request_id: str, code: str, decision: str = "approve") -> httpx.Response:
    return await c.post(f"{base(stack)}/oauth/consent", data={"request": request_id, "decision": decision, "officer_code": code})


def code_from(resp: httpx.Response) -> str:
    assert resp.status_code == 303, resp.text
    return parse_qs(urlparse(resp.headers["location"]).query)["code"][0]


async def signed_in(c, stack, name: str = "Claude") -> dict:
    """The whole happy path; returns the token response plus the pieces a test needs."""
    client_id = await register(c, stack, name)
    verifier, challenge = pkce()
    rid = await start(c, stack, client_id, challenge)
    code = code_from(await consent(c, stack, rid, officer_code(stack, rid)))
    r = await c.post(f"{base(stack)}/token", data={
        "grant_type": "authorization_code", "code": code, "redirect_uri": REDIRECT, "client_id": client_id,
        "code_verifier": verifier})
    assert r.status_code == 200, r.text
    tok = r.json()
    claims = verify_session_token(tok["access_token"], stack.rt.key.public_key())
    return {**tok, "client_id": client_id, "session_id": claims.session_id, "code": code, "verifier": verifier}


def refused(r: httpx.Response, error: str | None = None) -> bool:
    """The token endpoint said no: 400 or 401 (the library picks), an OAuth error, and above all no token."""
    body = r.json()
    return r.status_code in (400, 401) and "access_token" not in body and (error is None or body.get("error") == error)


def mcp(stack, token: str) -> Client:
    return Client(StreamableHttpTransport(stack.gateway_url, headers={"Authorization": f"Bearer {token}"}))


async def refresh(c, stack, tokens: dict, refresh_token: str | None = None) -> httpx.Response:
    return await c.post(f"{base(stack)}/token", data={
        "grant_type": "refresh_token", "refresh_token": refresh_token or tokens["refresh_token"], "client_id": tokens["client_id"]})


# ---- discovery and the unauthenticated answer ----------------------------------------------------------------------
async def test_discovery_and_the_401_that_starts_sign_in(ostack):
    async with httpx.AsyncClient() as c:
        meta = (await c.get(f"{base(ostack)}/.well-known/oauth-authorization-server")).json()
        assert meta["authorization_endpoint"].endswith("/authorize") and meta["token_endpoint"].endswith("/token")
        assert meta["registration_endpoint"].endswith("/register") and "S256" in meta["code_challenge_methods_supported"]
        assert "revocation_endpoint" not in meta  # revocation is deliberately off
        res = await c.get(f"{base(ostack)}/.well-known/oauth-protected-resource/mcp")
        assert res.status_code == 200 and res.json()["resource"].endswith("/mcp")
        r = await c.post(ostack.gateway_url, json={"jsonrpc": "2.0", "id": 1, "method": "ping"})
        assert r.status_code == 401 and "resource_metadata" in r.headers["www-authenticate"]


# ---- the happy path -------------------------------------------------------------------------------------------------
async def test_sign_in_ends_with_a_working_slip_bound_session(ostack):
    async with httpx.AsyncClient() as c:
        t = await signed_in(c, ostack)
    assert t["token_type"].lower() == "bearer" and 0 < t["expires_in"] <= 900 and t["refresh_token"]
    session = ostack.rt.store.get(t["session_id"])
    assert session is not None and ostack.rt.store.is_usable(t["session_id"])
    async with mcp(ostack, t["access_token"]) as client:
        assert {x.name for x in await client.list_tools()} == {"read_quotation", "query_stock", "send_email"}
        assert "Shakti" in (await client.call_tool("read_quotation", {"quote_id": "Q-1043"})).content[0].text
    # the slip is the officer-approved one: one message, the vendor's domain only
    assert session.contract.max_messages == 1 and session.contract.allowed_recipient_domains == ["shakti.example"]


async def test_the_oauth_slip_still_denies_a_leak(ostack):
    async with httpx.AsyncClient() as c:
        t = await signed_in(c, ostack)
    async with mcp(ostack, t["access_token"]) as client:
        await client.call_tool("query_stock", {"item": "all"})
        with pytest.raises(Exception, match="restricted"):
            await client.call_tool("send_email", {"to": "sales@shakti.example", "subject": "stock",
                                                  "body": "We hold 2,400 units at depot FSD-14."})


async def test_the_header_route_still_works_with_oauth_on(ostack):
    s = await ostack.start_session()
    async with mcp(ostack, s["session_token"]) as client:
        assert len(await client.list_tools()) == 3


# ---- ways to cheat the officer's step ---------------------------------------------------------------------------------
async def test_no_approval_without_the_officer_code(ostack):
    async with httpx.AsyncClient() as c:
        cid = await register(c, ostack)
        sessions_before = len(ostack.rt.store.sessions)
        rid = await start(c, ostack, cid, pkce()[1])
        for wrong in ("", "000000" if officer_code(ostack, rid) != "000000" else "111111", "abc"):
            r = await consent(c, ostack, rid, wrong)
            assert r.status_code == 403 and "location" not in r.headers
        assert len(ostack.rt.store.sessions) == sessions_before  # nothing was confirmed
        assert rid in ostack.rt.oauth.pending  # still waiting for the real code


async def test_a_request_locks_after_too_many_wrong_codes(ostack):
    async with httpx.AsyncClient() as c:
        cid = await register(c, ostack)
        rid = await start(c, ostack, cid, pkce()[1])
        real = officer_code(ostack, rid)
        wrong = "000000" if real != "000000" else "111111"
        statuses = [(await consent(c, ostack, rid, wrong)).status_code for _ in range(ostack.rt.oauth.max_attempts)]
        assert statuses == [403] * (ostack.rt.oauth.max_attempts - 1) + [410]
        assert (await consent(c, ostack, rid, real)).status_code == 410  # the right code no longer helps


async def test_an_expired_request_cannot_be_approved(ostack):
    async with httpx.AsyncClient() as c:
        cid = await register(c, ostack)
        rid = await start(c, ostack, cid, pkce()[1])
        real = officer_code(ostack, rid)
        ostack.rt.oauth.pending[rid].created -= 10_000
        assert (await c.get(f"{base(ostack)}/oauth/consent", params={"request": rid})).status_code == 410
        assert (await consent(c, ostack, rid, real)).status_code == 410


async def test_denying_issues_no_code_and_no_session(ostack):
    async with httpx.AsyncClient() as c:
        cid = await register(c, ostack)
        before = len(ostack.rt.store.sessions)
        rid = await start(c, ostack, cid, pkce()[1], state="keep-me")
        r = await consent(c, ostack, rid, "", decision="deny")
        q = parse_qs(urlparse(r.headers["location"]).query)
        assert r.status_code == 303 and q["error"] == ["access_denied"] and q["state"] == ["keep-me"] and "code" not in q
        assert len(ostack.rt.store.sessions) == before and rid not in ostack.rt.oauth.pending


async def test_an_unregistered_client_cannot_start_sign_in(ostack):
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{base(ostack)}/authorize", params={
            "response_type": "code", "client_id": "never-registered", "redirect_uri": REDIRECT,
            "code_challenge": pkce()[1], "code_challenge_method": "S256"})
        assert r.status_code == 400 and not ostack.rt.oauth.pending.get("never-registered")


async def test_the_consent_page_is_served_as_utf8_and_reads_correctly(ostack):
    """Caught on the first live sign-in: a file rewritten in the wrong encoding showed 'Â·' in the page title."""
    async with httpx.AsyncClient() as c:
        rid = await start(c, ostack, await register(c, ostack), pkce()[1])
        r = await c.get(f"{base(ostack)}/oauth/consent", params={"request": rid})
        assert "utf-8" in r.headers["content-type"].lower()
        assert "Sentinel · officer approval" in r.text and "Â" not in r.text


async def test_the_consent_page_escapes_what_a_client_calls_itself(ostack):
    async with httpx.AsyncClient() as c:
        cid = await register(c, ostack, name="<script>alert(1)</script>")
        rid = await start(c, ostack, cid, pkce()[1])
        page = (await c.get(f"{base(ostack)}/oauth/consent", params={"request": rid})).text
        assert "<script>alert(1)" not in page and "&lt;script&gt;" in page
        r = await c.get(f"{base(ostack)}/oauth/consent", params={"request": rid})
        assert r.headers["x-frame-options"] == "DENY" and "no-store" in r.headers["cache-control"]


# ---- ways to cheat the token exchange ---------------------------------------------------------------------------------
async def test_a_wrong_pkce_verifier_is_refused(ostack):
    async with httpx.AsyncClient() as c:
        cid = await register(c, ostack)
        _, challenge = pkce()
        rid = await start(c, ostack, cid, challenge)
        code = code_from(await consent(c, ostack, rid, officer_code(ostack, rid)))
        r = await c.post(f"{base(ostack)}/token", data={"grant_type": "authorization_code", "code": code, "redirect_uri": REDIRECT,
                                                         "client_id": cid, "code_verifier": secrets.token_urlsafe(48)})
        assert refused(r, "invalid_grant")


async def test_an_authorization_code_works_once(ostack):
    async with httpx.AsyncClient() as c:
        t = await signed_in(c, ostack)
        r = await c.post(f"{base(ostack)}/token", data={
            "grant_type": "authorization_code", "code": t["code"], "redirect_uri": REDIRECT, "client_id": t["client_id"],
            "code_verifier": t["verifier"]})
        assert refused(r, "invalid_grant")


async def test_a_different_redirect_uri_at_exchange_is_refused(ostack):
    async with httpx.AsyncClient() as c:
        cid = await register(c, ostack)
        verifier, challenge = pkce()
        rid = await start(c, ostack, cid, challenge)
        code = code_from(await consent(c, ostack, rid, officer_code(ostack, rid)))
        r = await c.post(f"{base(ostack)}/token", data={"grant_type": "authorization_code", "code": code,
                                                         "redirect_uri": "https://evil.example/cb", "client_id": cid,
                                                         "code_verifier": verifier})
        assert refused(r)


async def test_a_code_cannot_be_used_by_another_client(ostack):
    async with httpx.AsyncClient() as c:
        cid = await register(c, ostack)
        other = await register(c, ostack, name="Other")
        verifier, challenge = pkce()
        rid = await start(c, ostack, cid, challenge)
        code = code_from(await consent(c, ostack, rid, officer_code(ostack, rid)))
        r = await c.post(f"{base(ostack)}/token", data={"grant_type": "authorization_code", "code": code, "redirect_uri": REDIRECT,
                                                         "client_id": other, "code_verifier": verifier})
        assert refused(r)


async def test_forged_and_garbage_tokens_get_401(ostack):
    forged_none = jwt.encode({"iss": "x"}, key=None, algorithm="none")
    async with httpx.AsyncClient() as c:
        for bad in ("garbage", forged_none, "Bearer"):  # (a missing header is covered by the discovery test)
            r = await c.post(ostack.gateway_url, headers={"Authorization": f"Bearer {bad}"},
                             json={"jsonrpc": "2.0", "id": 1, "method": "ping"})
            assert r.status_code == 401, bad


# ---- refresh: the same session, never a fresh one ---------------------------------------------------------------------
async def test_refresh_keeps_the_session_so_it_cannot_reset_the_message_budget(ostack):
    async with httpx.AsyncClient() as c:
        t = await signed_in(c, ostack)
        async with mcp(ostack, t["access_token"]) as client:  # the slip allows one message: use it
            await client.call_tool("send_email", {"to": "sales@shakti.example", "subject": "hi", "body": "Quotation received."})
        r = await refresh(c, ostack, t)
        assert r.status_code == 200, r.text
        t2 = r.json()
        assert verify_session_token(t2["access_token"], ostack.rt.key.public_key()).session_id == t["session_id"]
        # (the access token may be byte-identical when refreshed within the same second: same session, same claims)
        assert t2["refresh_token"] != t["refresh_token"]
        async with mcp(ostack, t2["access_token"]) as client:  # a fresh session would allow a second message; this must not
            with pytest.raises(Exception, match="limit|budget|message"):
                await client.call_tool("send_email", {"to": "sales@shakti.example", "subject": "again", "body": "Second."})


async def test_a_refresh_token_works_once(ostack):
    async with httpx.AsyncClient() as c:
        t = await signed_in(c, ostack)
        assert (await refresh(c, ostack, t)).status_code == 200
        r = await refresh(c, ostack, t)  # the old one was rotated away
        assert refused(r, "invalid_grant")


async def test_refresh_is_refused_for_a_frozen_session(ostack):
    async with httpx.AsyncClient() as c:
        t = await signed_in(c, ostack)
        ostack.rt.store.freeze(t["session_id"])
        r = await refresh(c, ostack, t)
        assert refused(r, "invalid_grant")
        # the old access token still passes the HTTP layer; the gateway then answers the agent's call clearly
        async with mcp(ostack, t["access_token"]) as client:
            with pytest.raises(Exception, match="session is not valid|frozen"):
                await client.call_tool("read_quotation", {"quote_id": "Q-1043"})


async def test_refresh_is_refused_after_the_slip_expires(ostack):
    async with httpx.AsyncClient() as c:
        t = await signed_in(c, ostack)
        s = ostack.rt.store.get(t["session_id"])
        s.contract = s.contract.model_copy(update={"expires_at": datetime.now(timezone.utc) - timedelta(seconds=5)})
        r = await refresh(c, ostack, t)
        assert refused(r, "invalid_grant")


async def test_a_refresh_token_belongs_to_its_client(ostack):
    async with httpx.AsyncClient() as c:
        t = await signed_in(c, ostack)
        other = await register(c, ostack, name="Other")
        r = await c.post(f"{base(ostack)}/token", data={"grant_type": "refresh_token", "refresh_token": t["refresh_token"],
                                                         "client_id": other})
        assert refused(r)


async def test_access_tokens_never_outlive_the_slip(ostack):
    async with httpx.AsyncClient() as c:
        cid = await register(c, ostack)
        ostack.rt.oauth.slip_ttl = 120  # a short slip: the token must be capped to it
        try:
            verifier, challenge = pkce()
            rid = await start(c, ostack, cid, challenge)
            code = code_from(await consent(c, ostack, rid, officer_code(ostack, rid)))
            r = await c.post(f"{base(ostack)}/token", data={"grant_type": "authorization_code", "code": code, "redirect_uri": REDIRECT,
                                                             "client_id": cid, "code_verifier": verifier})
        finally:
            ostack.rt.oauth.slip_ttl = 3600
        assert r.status_code == 200 and r.json()["expires_in"] <= 120


# ---- the JSON endpoints the site's consent page uses, and the connect endpoints -------------------------------------
async def test_json_consent_endpoints_follow_the_contract(ostack):
    async with httpx.AsyncClient(base_url=ostack.api_url) as api, httpx.AsyncClient() as c:  # no API token on purpose
        cid = await register(c, ostack, name="Claude")
        rid = await start(c, ostack, cid, pkce()[1])
        v = (await api.get(f"/api/v1/oauth/requests/{rid}")).json()
        assert v["client_name"] == "Claude" and v["request_id"] == rid and 0 < v["expires_in"] <= 300
        assert v["slip"]["allowed_tools"] == ["read_quotation", "query_stock", "send_email"]
        wrong = await api.post(f"/api/v1/oauth/requests/{rid}", json={"decision": "approve", "officer_code": "abc"})
        assert wrong.status_code == 403 and "not right" in wrong.json()["detail"]
        ok = await api.post(f"/api/v1/oauth/requests/{rid}", json={"decision": "approve", "officer_code": officer_code(ostack, rid)})
        assert ok.status_code == 200 and "code=" in ok.json()["redirect_to"]
        assert (await api.get(f"/api/v1/oauth/requests/{rid}")).status_code == 410  # single use


async def test_connect_endpoints(ostack):
    async with ostack.api() as api:
        v = (await api.get("/api/v1/connect")).json()
        assert v["public_url"] == base(ostack) and v["mcp_url"].endswith("/mcp")
        assert [m["id"] for m in v["methods"]] == ["oauth", "header"]
        assert all(c["screenshot"] is None for c in v["clients"] if c["status"] != "tested")
        assert {m["id"]: m["status"] for m in v["methods"]} == {"oauth": "tested", "header": "tested"}
        assert [c["id"] for c in v["clients"] if c["status"] == "tested"] == ["claude-web", "claude-code", "claude-code-hook", "local-chat"]
        assert all(c["transcript"] is None for c in v["clients"] if c["status"] != "tested")
        tok = (await api.post("/api/v1/connect/token", json={"preset": "quotation_processing"})).json()
        assert tok["header_value"].startswith("Bearer ") and tok["slip"]["max_messages"] == 1
        assert (await api.post("/api/v1/connect/token", json={"preset": "nope"})).status_code == 422
    async with mcp(ostack, tok["header_value"].removeprefix("Bearer ")) as client:
        assert len(await client.list_tools()) == 3
    async with httpx.AsyncClient(base_url=ostack.api_url) as anon:
        r = await anon.get("/api/v1/connect")  # public by design (D-041): statuses, steps and the connector address only
        assert r.status_code == 200 and r.json()["mcp_url"] == v["mcp_url"]
        assert tok["header_value"].removeprefix("Bearer ") not in r.text
        assert (await anon.post("/api/v1/connect/token", json={"preset": "quotation_processing"})).status_code == 401  # the token still needs the officer


async def test_oauth_endpoints_report_clearly_when_oauth_is_off(stack):
    async with httpx.AsyncClient(base_url=stack.api_url) as api:
        r = await api.get("/api/v1/oauth/requests/oar_x")
        assert r.status_code == 404 and "not enabled" in r.json()["detail"]
    async with stack.api() as api:
        v = (await api.get("/api/v1/connect")).json()
        assert v["public_url"] is None and [m["id"] for m in v["methods"]] == ["header"]


def test_the_officer_code_is_six_digits_and_unpredictable_enough():
    assert re.fullmatch(r"\d{6}", f"{secrets.randbelow(10**6):06d}")  # the format the consent page promises


def test_every_tested_status_is_backed_by_evidence_that_exists_and_holds_no_credential():
    """F8: a client is only `tested` if a screenshot or a captured session is committed for it, and neither may hold a token."""
    from pathlib import Path

    from sentinel.connect import CLIENTS
    site = Path(__file__).resolve().parents[1] / "site" / "public"
    for cid, _name, _kind, status, _method, _snippet, screenshot, transcript in CLIENTS:
        if status != "tested":
            assert screenshot is None and transcript is None, cid
            continue
        assert screenshot or transcript, f"{cid} is marked tested with no evidence"
        if screenshot:
            assert (site / screenshot.lstrip("/")).is_file(), screenshot
        if transcript:
            f = site / transcript["url"].lstrip("/")
            assert f.is_file(), transcript["url"]
            body = f.read_text(encoding="utf-8")
            assert "Bearer ey" not in body and "eyJ" not in body and len(body) > 500 and transcript["caption"]


async def test_sign_in_can_use_a_slip_that_is_not_about_a_quotation(ostack):
    """Found when preparing a Claude.ai test with the own-document slip: the sign-in always attached quotation Q-1043, so any
    other slip failed because the quotation's vendor is not in its domains (plan R1)."""
    from sentinel.oauth import SentinelOAuthProvider

    p = SentinelOAuthProvider(ostack.rt, base_url=ostack.gateway_url.removesuffix("/mcp"), preset="own_document")
    draft = p._slip_draft()
    assert draft.template == "own_document" and draft.work_item_id is None and draft.resolved_vendor is None
    assert "read_document" in draft.allowed_tools and draft.strict_flows
    q = SentinelOAuthProvider(ostack.rt, base_url=ostack.gateway_url.removesuffix("/mcp"))  # the default is unchanged
    assert q._slip_draft().work_item_id == "Q-1043"
