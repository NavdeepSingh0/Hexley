"""Sign in with Google on the page where an AI client asks to connect (Navdeep's decision, D-060).

A real connector's flow: the person clicks connect in the AI app, signs in with their account, and clicks Allow. Hexley uses Google only to
learn who is at the browser, with the scopes `openid email`: it reads nothing else from the account and keeps no Google token. A browser
that signed in holds a signed login naming the address, so the next connection is one click, and it survives a restart.

This is who may approve a connection. It is not who may act: the permission slip still decides that.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass, field
from urllib.parse import urlencode

import httpx

AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
ISSUERS = ("https://accounts.google.com", "accounts.google.com")
LOGIN_SECONDS = 30 * 86400
STATE_SECONDS = 600
MAX_STATES = 200


class GoogleLoginError(Exception):
    """Sign-in did not complete, or it is not configured properly. The message is safe to show the person."""


def google_from_env(environ, api_token: str, public_url: str) -> GoogleLogin | None:
    """Google login from a deployment's settings, or None when it is not configured. Half a configuration stops the start rather than
    falling back to something weaker, and so does a plain http address: a login must never cross one."""
    client_id, secret = environ.get("HEXLEY_GOOGLE_CLIENT_ID", ""), environ.get("HEXLEY_GOOGLE_CLIENT_SECRET", "")
    if not client_id and not secret:
        return None
    if not client_id or not secret:
        raise GoogleLoginError("HEXLEY_GOOGLE_CLIENT_ID and HEXLEY_GOOGLE_CLIENT_SECRET must be set together")
    allowed = frozenset(e.strip().lower() for e in environ.get("HEXLEY_OFFICER_EMAILS", "").split(",") if e.strip())
    if not allowed:
        raise GoogleLoginError("HEXLEY_OFFICER_EMAILS must name who may approve a connection, or be * for any Google account")
    if not public_url.startswith("https://"):
        raise GoogleLoginError("Google sign-in needs an https public address")
    derived = hmac.new(api_token.encode(), b"hexley-google-login-v1", hashlib.sha256).digest()
    return GoogleLogin(client_id, secret, f"{public_url.rstrip('/')}/oauth/google/callback", derived, allowed)


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _claims(id_token: str) -> dict:
    """The claims of an ID token received directly from Google's token endpoint over TLS, which the OpenID Connect specification allows
    without checking its signature (section 3.1.3.7). Never use this on a token that arrived any other way."""
    try:
        payload = id_token.split(".")[1]
        return json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    except (IndexError, ValueError) as e:
        raise GoogleLoginError("Google's answer could not be read.") from e


@dataclass
class GoogleLogin:
    client_id: str
    client_secret: str
    redirect_uri: str
    secret: bytes  # signs the browser's login; derived from the officer's token, so changing that token ends every login
    allowed: frozenset[str] = frozenset()  # addresses that may approve; {"*"} means any verified Google account
    transport: object | None = None  # tests replace Google here
    states: dict[str, tuple[str, str, float]] = field(default_factory=dict)  # state -> (PKCE verifier, request id, created)

    def may_approve(self, email: str) -> bool:
        return "*" in self.allowed or email.strip().lower() in self.allowed

    # ---- the browser's login -----------------------------------------------------------------------------------------
    def _sign(self, text: str) -> str:
        return hmac.new(self.secret, text.encode(), hashlib.sha256).hexdigest()

    def login_value(self, email: str, now: float | None = None) -> str:
        expires = int((now or time.time()) + LOGIN_SECONDS)
        body = _b64(json.dumps({"e": email.strip().lower(), "x": expires}).encode())
        return f"{body}.{self._sign(body)}"

    def email_from(self, cookie: str | None, now: float | None = None) -> str | None:
        """The address a login names, if it is genuine, unexpired and still on the list."""
        if not cookie or "." not in cookie:
            return None
        body, _, mac = cookie.rpartition(".")
        if not hmac.compare_digest(mac.encode(), self._sign(body).encode()):
            return None
        try:
            doc = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
            email, expires = str(doc["e"]), float(doc["x"])
        except (ValueError, KeyError, TypeError):
            return None
        return email if expires > (now or time.time()) and self.may_approve(email) else None

    # ---- the round trip to Google ---------------------------------------------------------------------------------------
    def start(self, request_id: str, now: float | None = None) -> tuple[str, str]:
        """The address to send the browser to, and the state to bind to this browser. Single use, and it expires."""
        now = now or time.time()
        for s in [s for s, v in self.states.items() if now - v[2] > STATE_SECONDS]:
            del self.states[s]
        if len(self.states) >= MAX_STATES:
            raise GoogleLoginError("Too many sign-ins are in progress. Try again in a few minutes.")
        state, verifier = secrets.token_urlsafe(32), secrets.token_urlsafe(48)
        self.states[state] = (verifier, request_id, now)
        challenge = _b64(hashlib.sha256(verifier.encode()).digest())
        query = urlencode({"client_id": self.client_id, "redirect_uri": self.redirect_uri, "response_type": "code", "scope": "openid email",
                           "state": state, "code_challenge": challenge, "code_challenge_method": "S256", "prompt": "select_account"})
        return f"{AUTHORIZE_URL}?{query}", state

    async def finish(self, state: str, browser_state: str | None, code: str, now: float | None = None) -> tuple[str, str]:
        """Google sent the browser back. Returns (verified address on the list, the request it belongs to). Raises GoogleLoginError."""
        now = now or time.time()
        if not state or not browser_state or not hmac.compare_digest(state.encode(), browser_state.encode()):
            raise GoogleLoginError("This sign-in did not start on this browser. Start again from the AI app.")
        entry = self.states.pop(state, None)
        if entry is None or now - entry[2] > STATE_SECONDS:
            raise GoogleLoginError("This sign-in has expired or was already used. Start again from the AI app.")
        verifier, request_id, _ = entry
        kwargs = {"transport": self.transport} if self.transport else {}
        async with httpx.AsyncClient(timeout=20, **kwargs) as c:
            try:
                r = await c.post(TOKEN_URL, data={"grant_type": "authorization_code", "code": code, "client_id": self.client_id,
                                                  "client_secret": self.client_secret, "redirect_uri": self.redirect_uri, "code_verifier": verifier})
            except httpx.HTTPError as e:
                raise GoogleLoginError("Google could not be reached. Try again.") from e
        if r.status_code != 200:
            raise GoogleLoginError("Google did not accept this sign-in. Start again from the AI app.")
        claims = _claims(str(r.json().get("id_token", "")))
        email = str(claims.get("email", "")).strip().lower()
        if (claims.get("iss") not in ISSUERS or claims.get("aud") != self.client_id or float(claims.get("exp", 0)) <= now
                or claims.get("email_verified") is not True or not email):
            raise GoogleLoginError("Google's answer could not be verified. Start again from the AI app.")
        if not self.may_approve(email):
            raise GoogleLoginError(f"{email} is not allowed to approve connections on this Hexley. Ask the officer to add it.")
        return email, request_id
