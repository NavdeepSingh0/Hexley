"""D-060: connect, sign in with Google, Allow. Real HTTP to a real gateway; only Google's token endpoint is a stand-in."""

from __future__ import annotations

import base64
import json
import time
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
import pytest_asyncio

from sentinel.cli import tool_server_env
from sentinel.google_login import GoogleLogin, GoogleLoginError, google_from_env
from sentinel.oauth import LOGIN_COOKIE
from sentinel.stack import running_stack
from sentinel.upstreams import UpstreamSet
from tests.test_oauth import REDIRECT, base, code_from, officer_code, pkce, register, start

CLIENT = "client-id.apps.googleusercontent.example"
BOSS = "officer@team.example"
SECRET = b"s" * 32


def _token(**over) -> str:
    claims = {"iss": "https://accounts.google.com", "aud": CLIENT, "email": BOSS, "email_verified": True, "exp": time.time() + 600, **over}
    body = base64.urlsafe_b64encode(json.dumps(claims).encode()).rstrip(b"=").decode()
    return f"h.{body}.s"


class FakeGoogle:
    """Google's token endpoint. It records what it was sent, and answers with the ID token a test chose."""

    def __init__(self):
        self.id_token, self.status, self.seen = _token(), 200, []

    def transport(self) -> httpx.MockTransport:
        def handler(request: httpx.Request) -> httpx.Response:
            self.seen.append(parse_qs(request.content.decode()))
            return httpx.Response(self.status, json={"id_token": self.id_token})
        return httpx.MockTransport(handler)


@pytest_asyncio.fixture(scope="module")
async def stack():
    async with running_stack(oauth=True) as s:
        yield s


@pytest.fixture
def google(stack):
    fake = FakeGoogle()
    stack.rt.oauth.google = GoogleLogin(CLIENT, "client-secret", f"{base(stack)}/oauth/google/callback", SECRET, frozenset({BOSS}), fake.transport())
    yield fake
    stack.rt.oauth.google = None


async def _request(c, stack) -> str:
    return await start(c, stack, await register(c, stack), pkce()[1])


async def _sign_in(c, stack, rid: str, code: str = "google-code") -> httpx.Response:
    """Click the button, then come back from Google."""
    r = await c.get(f"{base(stack)}/oauth/google/start", params={"request": rid})
    assert r.status_code == 303 and r.headers["location"].startswith("https://accounts.google.com/"), r.text
    state = parse_qs(urlparse(r.headers["location"]).query)["state"][0]
    return await c.get(f"{base(stack)}/oauth/google/callback", params={"state": state, "code": code})


async def test_connect_sign_in_with_google_allow_then_the_next_connection_is_one_click(stack, google):
    async with httpx.AsyncClient(timeout=30) as c:
        rid = await _request(c, stack)
        page = (await c.get(f"{base(stack)}/oauth/consent", params={"request": rid})).text
        assert "Continue with Google" in page and "officer_code" not in page and "code" not in page.lower()
        back = await _sign_in(c, stack, rid)
        assert back.status_code == 303 and rid in back.headers["location"]
        cookie = back.headers["set-cookie"]
        assert LOGIN_COOKIE in cookie and "httponly" in cookie.lower() and "samesite=lax" in cookie.lower() and "path=/oauth/" in cookie.lower()
        page = (await c.get(f"{base(stack)}/oauth/consent", params={"request": rid})).text
        assert BOSS in page and ">Allow<" in page and "Continue with Google" not in page
        assert code_from(await c.post(f"{base(stack)}/oauth/consent", data={"request": rid, "decision": "approve"}))
        rid2 = await _request(c, stack)
        assert code_from(await c.post(f"{base(stack)}/oauth/consent", data={"request": rid2, "decision": "approve"}))  # one click


async def test_connecting_goes_straight_to_google_and_a_logged_in_browser_straight_to_allow(stack, google):
    async with httpx.AsyncClient(timeout=30) as c:
        client = await register(c, stack)
        r = await c.get(f"{base(stack)}/authorize", params={"response_type": "code", "client_id": client, "redirect_uri": REDIRECT,
                                                            "code_challenge": pkce()[1], "code_challenge_method": "S256", "state": "s"})
        assert "/oauth/google/start" in r.headers["location"]  # no Hexley page before the login
        first = await c.get(r.headers["location"])
        assert first.headers["location"].startswith("https://accounts.google.com/")
    async with httpx.AsyncClient(timeout=30, cookies={LOGIN_COOKIE: stack.rt.oauth.google.login_value(BOSS)}) as c:
        rid = await _request(c, stack)
        r = await c.get(f"{base(stack)}/oauth/google/start", params={"request": rid})
        assert r.status_code == 303 and r.headers["location"].startswith("/oauth/consent") and "accounts.google.com" not in r.headers["location"]


async def test_the_allow_page_says_what_it_gives_in_plain_words_and_folds_the_list(stack, google):
    stack.rt.oauth.preset = "claude_connectors"
    try:
        async with httpx.AsyncClient(timeout=30, cookies={LOGIN_COOKIE: stack.rt.oauth.google.login_value(BOSS)}) as c:
            page = (await c.get(f"{base(stack)}/oauth/consent", params={"request": await _request(c, stack)})).text
    finally:
        stack.rt.oauth.preset = "quotation_processing"
    assert "wants to connect to Hexley" in page and "Gmail, Notion and Slack connectors" in page and "<details>" in page and "officer approval" not in page
    assert page.index(">Cancel<") < page.index(">Allow<") and "Keep this access for" in page and "Use another account" in page


async def test_use_another_account_goes_back_to_googles_picker_for_the_same_connection(stack, google):
    async with httpx.AsyncClient(timeout=30, cookies={LOGIN_COOKIE: stack.rt.oauth.google.login_value(BOSS)}) as c:
        rid = await _request(c, stack)
        r = await c.post(f"{base(stack)}/oauth/sign-out", data={"request": rid})
        assert r.status_code == 303 and rid in r.headers["location"] and LOGIN_COOKIE in r.headers["set-cookie"]
    async with httpx.AsyncClient(timeout=30) as signed_out:  # the browser dropped the cookie it was told to; this client's jar would not
        assert (await signed_out.get(f"{base(stack)}{r.headers['location']}")).headers["location"].startswith("https://accounts.google.com/")


async def test_raw_channel_and_page_ids_stay_under_the_details_on_the_allow_page(stack, google):
    from sentinel.oauth import _places
    assert _places(["a@b.example", "channel:C123", "channel:C456", "page:abc"]) == "1 e-mail address, 2 Slack channels and 1 Notion page"
    assert _places(["corp.example"]) == "corp.example"


async def test_google_is_sent_the_code_the_secret_and_the_proof_of_the_browser(stack, google):
    async with httpx.AsyncClient(timeout=30) as c:
        await _sign_in(c, stack, await _request(c, stack), "the-code")
    sent = google.seen[-1]
    assert sent["code"] == ["the-code"] and sent["client_secret"] == ["client-secret"] and sent["code_verifier"][0]


async def test_with_google_on_neither_the_code_nor_the_officer_token_approves_anything(stack, google):
    async with httpx.AsyncClient(timeout=30) as c:
        rid = await _request(c, stack)
        for proof in (officer_code(stack, rid), "test-api-token"):
            r = await c.post(f"{base(stack)}/oauth/consent", data={"request": rid, "decision": "approve", "officer_code": proof})
            assert r.status_code == 403 and "set-cookie" not in r.headers


@pytest.mark.parametrize("claims, why", [
    ({"email": "stranger@elsewhere.example"}, "not on the list"),
    ({"aud": "someone-elses-client"}, "made for another app"),
    ({"iss": "https://evil.example"}, "not from Google"),
    ({"email_verified": False}, "address not verified"),
    ({"exp": 0}, "expired"),
    ({"email": ""}, "no address"),
])
async def test_an_answer_from_google_that_does_not_hold_up_signs_nobody_in(stack, google, claims, why):
    google.id_token = _token(**claims)
    async with httpx.AsyncClient(timeout=30) as c:
        rid = await _request(c, stack)
        r = await _sign_in(c, stack, rid)
        assert r.status_code == 403 and "set-cookie" not in r.headers or LOGIN_COOKIE not in r.headers.get("set-cookie", ""), why
        assert (await c.post(f"{base(stack)}/oauth/consent", data={"request": rid, "decision": "approve"})).status_code == 403, why


async def test_a_refusal_from_google_or_a_garbled_answer_signs_nobody_in(stack, google):
    async with httpx.AsyncClient(timeout=30) as c:
        google.status = 400
        assert (await _sign_in(c, stack, await _request(c, stack))).status_code == 403
        google.status, google.id_token = 200, "garbled"
        assert (await _sign_in(c, stack, await _request(c, stack))).status_code == 403
        r = await c.get(f"{base(stack)}/oauth/google/callback", params={"error": "access_denied"})
        assert r.status_code == 403 and "set-cookie" not in r.headers


async def test_a_return_from_google_on_another_browser_is_refused(stack, google):
    async with httpx.AsyncClient(timeout=30) as mine, httpx.AsyncClient(timeout=30) as other:
        rid = await _request(mine, stack)
        r = await mine.get(f"{base(stack)}/oauth/google/start", params={"request": rid})
        state = parse_qs(urlparse(r.headers["location"]).query)["state"][0]
        assert (await other.get(f"{base(stack)}/oauth/google/callback", params={"state": state, "code": "x"})).status_code == 403


async def test_a_state_works_once(stack, google):
    async with httpx.AsyncClient(timeout=30) as c:
        rid = await _request(c, stack)
        r = await c.get(f"{base(stack)}/oauth/google/start", params={"request": rid})
        state = parse_qs(urlparse(r.headers["location"]).query)["state"][0]
        assert (await c.get(f"{base(stack)}/oauth/google/callback", params={"state": state, "code": "x"})).status_code == 303
        assert (await c.get(f"{base(stack)}/oauth/google/callback", params={"state": state, "code": "x"})).status_code == 403


async def test_denying_needs_no_login_and_issues_no_code(stack, google):
    async with httpx.AsyncClient(timeout=30) as c:
        rid = await _request(c, stack)
        r = await c.post(f"{base(stack)}/oauth/consent", data={"request": rid, "decision": "deny"})
        assert r.status_code == 303 and "error=access_denied" in r.headers["location"] and "code=" not in r.headers["location"]


async def test_a_form_on_another_site_cannot_use_the_login(stack, google):
    login = stack.rt.oauth.google.login_value(BOSS)
    async with httpx.AsyncClient(timeout=30, cookies={LOGIN_COOKIE: login}) as c:
        rid = await _request(c, stack)
        r = await c.post(f"{base(stack)}/oauth/consent", data={"request": rid, "decision": "approve"}, headers={"Origin": "https://evil.example"})
        assert r.status_code == 403 and rid in stack.rt.oauth.pending


async def test_the_forms_own_post_passes_in_a_real_browser_and_another_sites_does_not(stack, google):
    """Real Chrome sends Origin: null for a form on a page with a no-referrer policy, which refused the Allow button on the live site."""
    login = stack.rt.oauth.google.login_value(BOSS)
    async with httpx.AsyncClient(timeout=30, cookies={LOGIN_COOKIE: login}) as c:
        rid = await _request(c, stack)
        for bad in ("cross-site", "same-site", "none"):
            r = await c.post(f"{base(stack)}/oauth/consent", data={"request": rid, "decision": "approve"},
                             headers={"Origin": "null", "Sec-Fetch-Site": bad})
            assert r.status_code == 403 and rid in stack.rt.oauth.pending, bad
        assert (await c.post(f"{base(stack)}/oauth/consent", data={"request": rid, "decision": "approve"}, headers={"Origin": "null"})).status_code == 403
        ok = await c.post(f"{base(stack)}/oauth/consent", data={"request": rid, "decision": "approve"}, headers={"Origin": "null", "Sec-Fetch-Site": "same-origin"})
        assert code_from(ok)


def _login(**over) -> GoogleLogin:
    return GoogleLogin(CLIENT, "s", "https://hexley.site/oauth/google/callback", SECRET, over.get("allowed", frozenset({BOSS})))


def test_a_login_is_signed_ends_on_its_date_and_ends_when_removed_from_the_list():
    g = _login()
    value = g.login_value(BOSS)
    assert g.email_from(value) == BOSS
    assert g.email_from(value + "0") is None and g.email_from("forged.value") is None and g.email_from(None) is None and g.email_from("") is None
    assert g.email_from(value, now=time.time() + 31 * 86400) is None
    assert _login(allowed=frozenset({"other@team.example"})).email_from(value) is None  # taken off the list: out at once
    assert GoogleLogin(CLIENT, "s", "x", b"another" * 8, frozenset({BOSS})).email_from(value) is None  # survives a restart only with the same token


def test_any_account_is_only_ever_an_explicit_choice():
    assert _login(allowed=frozenset({"*"})).may_approve("anyone@elsewhere.example")
    assert not _login().may_approve("anyone@elsewhere.example")


def test_google_login_needs_all_its_settings_and_a_list_of_who_may_approve():
    env = {"HEXLEY_GOOGLE_CLIENT_ID": CLIENT, "HEXLEY_GOOGLE_CLIENT_SECRET": "s", "HEXLEY_OFFICER_EMAILS": "Officer@Team.example, b@team.example"}
    assert google_from_env({}, "token", "https://hexley.site") is None  # not configured: off
    g = google_from_env(env, "token", "https://hexley.site")
    assert g.allowed == {"officer@team.example", "b@team.example"} and g.redirect_uri == "https://hexley.site/oauth/google/callback"
    with pytest.raises(GoogleLoginError):
        google_from_env({**env, "HEXLEY_OFFICER_EMAILS": ""}, "token", "https://hexley.site")
    with pytest.raises(GoogleLoginError):
        google_from_env({"HEXLEY_GOOGLE_CLIENT_ID": CLIENT}, "token", "https://hexley.site")
    with pytest.raises(GoogleLoginError):
        google_from_env(env, "token", "http://hexley.site")  # Google's secret and a login never cross plain http


def test_the_built_in_tool_server_does_not_inherit_googles_secret():
    env = tool_server_env({"PATH": "/bin", "HEXLEY_GOOGLE_CLIENT_SECRET": "s", "HEXLEY_GOOGLE_CLIENT_ID": "i"}, UpstreamSet())
    assert env == {"PATH": "/bin"}
