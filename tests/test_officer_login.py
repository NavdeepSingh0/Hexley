"""D-060: the officer logs in once on a browser, then approves a connection with one click. The code stays as a fallback."""

from __future__ import annotations

import httpx
import pytest_asyncio

from sentinel.oauth import LOGIN_COOKIE, SentinelOAuthProvider
from sentinel.stack import running_stack
from tests.test_oauth import base, code_from, officer_code, pkce, register, start

TOKEN = "test-api-token"


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def stack():
    async with running_stack(oauth=True) as s:
        yield s


async def _request(c, stack) -> str:
    return await start(c, stack, await register(c, stack), pkce()[1])


async def _post(c, stack, rid: str, proof: str = "", decision: str = "approve", headers: dict | None = None) -> httpx.Response:
    return await c.post(f"{base(stack)}/oauth/consent", data={"request": rid, "decision": decision, "officer_code": proof}, headers=headers or {})


async def test_the_token_once_approves_and_leaves_a_login_that_makes_the_next_one_a_single_click(stack):
    async with httpx.AsyncClient(timeout=30) as c:
        rid = await _request(c, stack)
        page = (await c.get(f"{base(stack)}/oauth/consent", params={"request": rid})).text
        assert 'name="officer_code"' in page and 'type="password"' in page and "logged in" not in page
        first = await _post(c, stack, rid, TOKEN)
        assert code_from(first)
        cookie = first.headers["set-cookie"]
        assert LOGIN_COOKIE in cookie and "httponly" in cookie.lower() and "samesite=lax" in cookie.lower() and "path=/oauth/" in cookie.lower()
        assert TOKEN not in cookie  # the browser holds something derived, never the token

        rid = await _request(c, stack)
        page = (await c.get(f"{base(stack)}/oauth/consent", params={"request": rid})).text
        assert "logged in" in page and 'name="officer_code"' not in page
        assert code_from(await _post(c, stack, rid))  # no code, no token: one click


async def test_a_wrong_token_is_refused_sets_nothing_and_counts_towards_the_lock(stack):
    async with httpx.AsyncClient(timeout=30) as c:
        rid = await _request(c, stack)
        r = await _post(c, stack, rid, "not-the-token")
        assert r.status_code == 403 and "set-cookie" not in r.headers
        for _ in range(3):
            assert (await _post(c, stack, rid, "not-the-token")).status_code == 403
        assert (await _post(c, stack, rid, "not-the-token")).status_code == 410
        assert (await _post(c, stack, rid, TOKEN)).status_code == 410  # locked, even for the right token


async def test_a_forged_login_opens_nothing(stack):
    async with httpx.AsyncClient(timeout=30, cookies={LOGIN_COOKIE: "0" * 64}) as c:
        rid = await _request(c, stack)
        assert 'name="officer_code"' in (await c.get(f"{base(stack)}/oauth/consent", params={"request": rid})).text
        assert (await _post(c, stack, rid)).status_code == 403


async def test_the_code_still_works_and_leaves_no_login(stack):
    async with httpx.AsyncClient(timeout=30) as c:
        rid = await _request(c, stack)
        r = await _post(c, stack, rid, officer_code(stack, rid))
        assert code_from(r) and "set-cookie" not in r.headers


async def test_a_form_on_another_site_cannot_use_the_officers_login(stack):
    login = stack.rt.oauth.login_value()
    async with httpx.AsyncClient(timeout=30, cookies={LOGIN_COOKIE: login}) as c:
        rid = await _request(c, stack)
        assert (await _post(c, stack, rid, headers={"Origin": "https://evil.example"})).status_code == 403
        assert rid in stack.rt.oauth.pending  # still waiting: nothing was approved
        assert (await _post(c, stack, rid, headers={"Origin": "null"})).status_code == 403
        assert code_from(await _post(c, stack, rid, headers={"Origin": base(stack)}))


async def test_logging_out_ends_the_login_on_this_browser(stack):
    async with httpx.AsyncClient(timeout=30, cookies={LOGIN_COOKIE: stack.rt.oauth.login_value()}) as c:
        r = await c.post(f"{base(stack)}/oauth/sign-out")
        assert r.status_code == 200 and 'max-age=0' in r.headers["set-cookie"].lower()
        assert (await c.post(f"{base(stack)}/oauth/sign-out", headers={"Origin": "https://evil.example"})).status_code == 403


def test_the_login_survives_a_restart_ends_when_the_token_changes_and_is_secure_over_https(stack):
    same = SentinelOAuthProvider(stack.rt, base_url="https://hexley.site")
    assert same.login_value() == stack.rt.oauth.login_value()  # derived from the token, not from anything in memory
    assert same.is_officer(same.login_value()) and not same.is_officer(None) and not same.is_officer("")
    saved, stack.rt.api_token = stack.rt.api_token, "a-different-officer-token-0123"
    try:
        assert not stack.rt.oauth.is_officer(hmac_of(saved))  # the login made with the old token no longer works
    finally:
        stack.rt.api_token = saved
    assert same.same_origin("https://hexley.site") and not same.same_origin("http://hexley.site") and same.same_origin(None)


def hmac_of(token: str) -> str:
    import hashlib
    import hmac

    return hmac.new(token.encode(), b"hexley-officer-login-v1", hashlib.sha256).hexdigest()
