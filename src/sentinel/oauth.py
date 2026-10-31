"""OAuth sign-in for the gateway: an AI client (Claude.ai, ChatGPT, ...) connects with "Sign in" and the OFFICER approves the
permission slip. Connecting and approving the task are one step.

The flow, on the gateway's public address (docs/plans/CORE_PLAN.md, phase B1):
  1. The client registers itself (dynamic client registration) and sends the user's browser to /authorize.
  2. `authorize()` does not approve anything. It records a pending request with a random 6-digit OFFICER CODE, shown only to
     the officer (terminal, console), and sends the browser to the consent page.
  3. The officer checks the slip on the consent page and types the code. Only then is the slip confirmed
     (`confirm.confirm_draft`, the same single place that mints every session) and a one-time authorization code issued.
  4. The client exchanges the code (PKCE) for an access token. The access token IS our signed session token, so
     `gateway.SentinelMiddleware` is unchanged and the header route (a token pasted into a client) keeps working.

Rules this module enforces itself:
  - No approval without the officer code (constant-time comparison); a request locks after `max_attempts` wrong codes.
  - Pending requests and authorization codes expire and are single-use.
  - A refresh re-issues a token for the SAME session, so it can never reset the message budget, the block counter or the
    fingerprints; it is refused once the session is frozen or the slip's own expiry has passed.
  - Access tokens are short (15 minutes) and never longer than what is left of the slip.
Demo-grade, not production identity management: one officer, in-memory state, a code shown in the terminal.
"""

from __future__ import annotations

import hashlib
import hmac
import html
import logging
import secrets
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlencode, urlsplit

from fastmcp.server.auth.auth import AccessToken, ClientRegistrationOptions, OAuthProvider, RevocationOptions
from mcp.server.auth.provider import (
    AuthorizationCode,
    AuthorizationParams,
    AuthorizeError,
    RefreshToken,
    RegistrationError,
    TokenError,
    construct_redirect_uri,
)
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse, Response

from .confirm import ConfirmError, confirm_draft
from .contracts import (SessionError, SlipError, draft_contract, mint_session_token, normalise_destination_entry,
                        verify_session_token)
from .events import make_event
from .brand import LOGO_SVG
from .google_login import LOGIN_SECONDS, GoogleLogin, GoogleLoginError
from .models import Column
from .runtime import Runtime

log = logging.getLogger("sentinel.oauth")

ACCESS_TTL_SECONDS = 900
OFFICER = "Col. R. Menon"  # the demo officer, as elsewhere (RunRequest.officer)


class OAuthError(Exception):
    """A consent-step failure with an HTTP status and a plain-English message for the officer."""

    def __init__(self, status: int, detail: str):
        super().__init__(detail)
        self.status, self.detail = status, detail


@dataclass
class PendingRequest:
    request_id: str
    client: OAuthClientInformationFull
    params: AuthorizationParams
    officer_code: str
    created: float
    attempts: int = 0


class SentinelAuthCode(AuthorizationCode):
    session_id: str


class SentinelOAuthProvider(OAuthProvider):
    def __init__(self, rt: Runtime, *, base_url: str, consent_base_url: str | None = None,
                 preset: str = "quotation_processing", work_item_id: str | None = "Q-1043", slip_ttl: int = 3600,
                 request_ttl: int = 300, code_ttl: int = 300, max_attempts: int = 5, max_clients: int = 200,
                 max_pending: int = 50, on_request=None, destinations: list[str] | None = None,
                 internal: list[str] | None = None):
        super().__init__(base_url=base_url,
                         client_registration_options=ClientRegistrationOptions(enabled=True),
                         revocation_options=RevocationOptions(enabled=False))  # disconnecting simply lets the token lapse
        self.rt = rt
        self.consent_base = (consent_base_url or base_url).rstrip("/")
        self.preset, self.work_item_id, self.slip_ttl = preset, work_item_id, slip_ttl
        # A deployment's own destinations for its slip (plan F3). They are the officer's, shown on the consent page, and not in git.
        self.destinations = [normalise_destination_entry(d) for d in (destinations or [])]
        self.internal = [normalise_destination_entry(d) for d in (internal or [])]
        outside = [d for d in self.internal if d not in self.destinations]
        if outside:
            raise SlipError(f"internal destination {', '.join(outside)} is not in the allowed destinations")
        self.request_ttl, self.code_ttl, self.max_attempts = request_ttl, code_ttl, max_attempts
        self.max_clients, self.max_pending = max_clients, max_pending
        self.on_request = on_request  # called with the new PendingRequest: prints the officer code in the terminal
        self.google: GoogleLogin | None = None  # Sign in with Google, set by `up` when configured (D-060). When set, it is the only way
        self.clients: dict[str, OAuthClientInformationFull] = {}
        self.pending: dict[str, PendingRequest] = {}
        self.codes: dict[str, SentinelAuthCode] = {}
        self.refresh_tokens: dict[str, tuple[RefreshToken, str]] = {}  # token -> (record, session_id)

    # ---- clients -------------------------------------------------------------------------------------------------
    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        return self.clients.get(client_id)

    async def register_client(self, client_info: OAuthClientInformationFull) -> None:
        if client_info.client_id is None:
            raise RegistrationError("invalid_client_metadata", "client_id is required")
        if client_info.client_id not in self.clients and len(self.clients) >= self.max_clients:
            raise RegistrationError("invalid_client_metadata", "too many registered clients")
        self.clients[client_info.client_id] = client_info

    # ---- the officer's step --------------------------------------------------------------------------------------
    def _purge(self) -> None:
        now = time.time()
        for rid in [r for r, p in self.pending.items() if now - p.created > self.request_ttl]:
            del self.pending[rid]
        for code in [c for c, a in self.codes.items() if a.expires_at < now]:
            del self.codes[code]

    def _slip_draft(self):
        spec = {**self.rt.templates[self.preset], "ttl_seconds": self.slip_ttl}
        if self.destinations:
            spec.update(allowed_recipient_domains=self.destinations, internal_destinations=self.internal)
        templates = {**self.rt.templates, self.preset: spec}
        # A work item (a quotation id) belongs only to a slip that is about one; any other slip, such as the one for working with
        # your own document, must not be tied to a quotation's vendor (plan R1: found when preparing the Claude.ai test).
        needs_item = bool(self.rt.templates[self.preset].get("requires_work_item")) or self.preset == "quotation_processing"
        return draft_contract(templates, self.preset, officer=OFFICER, work_item_id=self.work_item_id if needs_item else None)

    async def authorize(self, client: OAuthClientInformationFull, params: AuthorizationParams) -> str:
        """Called by /authorize. Approves nothing: it parks the request and sends the browser to the consent page."""
        self._purge()
        if client.client_id is None or client.client_id not in self.clients:
            raise AuthorizeError("unauthorized_client", "Client is not registered.")
        if len(self.pending) >= self.max_pending:
            raise AuthorizeError("temporarily_unavailable", "Too many sign-ins are waiting for the officer.")
        req = PendingRequest(request_id=f"oar_{secrets.token_hex(8)}", client=client, params=params,
                             officer_code=f"{secrets.randbelow(10**6):06d}", created=time.time())
        self.pending[req.request_id] = req
        await self.rt.bus.publish(make_event("oauth.request", None, None, {
            "request_id": req.request_id, "client_name": client.client_name or "an AI client",
            "officer_code": req.officer_code, "expires_in": self.request_ttl}))
        if self.on_request:
            self.on_request(req)
        if self.google is not None:
            return f"{self.consent_base}/oauth/google/start?{urlencode({'request': req.request_id})}"  # no page before the login
        return f"{self.consent_base}/oauth/consent?request={req.request_id}"

    def _get_pending(self, request_id: str) -> PendingRequest:
        self._purge()
        req = self.pending.get(request_id)
        if req is None:
            raise OAuthError(410, "This sign-in request has expired or was already used. Start again from the AI app.")
        return req

    def view(self, request_id: str) -> dict:
        """What the officer is asked to approve (contract: GET /api/v1/oauth/requests/{id})."""
        req = self._get_pending(request_id)
        slip = self._slip_draft()
        return {"request_id": req.request_id, "client_name": req.client.client_name or "an AI client",
                "expires_in": max(0, int(self.request_ttl - (time.time() - req.created))),
                "slip": {"objective": slip.objective, "allowed_tools": slip.allowed_tools,
                         "allowed_destinations": slip.allowed_recipient_domains, "max_messages": slip.max_messages,
                         "ttl_seconds": self.slip_ttl}}

    # ---- who the officer is, without a code each time (D-060) ------------------------------------------------------
    def login_value(self) -> str:
        """What the officer's browser holds after logging in: derived from the officer's token, so it survives a restart, stops
        working when the token changes, and cannot be turned back into the token."""
        return hmac.new(self.rt.api_token.encode(), b"hexley-officer-login-v1", hashlib.sha256).hexdigest()

    def is_officer(self, cookie: str | None) -> bool:
        if self.google is not None:
            return self.google.email_from(cookie) is not None
        return bool(cookie) and hmac.compare_digest(cookie.encode(), self.login_value().encode())

    def token_ok(self, secret: str) -> bool:
        return self.google is None and bool(secret) and hmac.compare_digest(secret.strip().encode(), self.rt.api_token.encode())

    def same_origin(self, origin: str | None, fetch_site: str | None = None) -> bool:
        """A form on another site must not approve a connection with the officer's login. A browser says so itself in Sec-Fetch-Site,
        which a page cannot set. Origin is the fallback for one that does not: found in real Chrome, a page with a no-referrer policy
        sends its own form's POST with Origin: null, so null alone cannot be told from a forged form and is refused only as a fallback."""
        if fetch_site is not None:
            return fetch_site == "same-origin"
        if origin is None:
            return True
        parts = urlsplit(self.consent_base)
        return origin == f"{parts.scheme}://{parts.netloc}"

    async def decide(self, request_id: str, decision: str, officer_code: str, verified: bool = False) -> str:
        """The officer approves or denies. Returns the address to send the browser back to the AI client. `verified` means the
        officer has already shown who they are by the login or the token, so no code is needed."""
        req = self._get_pending(request_id)
        redirect = str(req.params.redirect_uri)
        if decision == "deny":
            del self.pending[request_id]
            return construct_redirect_uri(redirect, error="access_denied", state=req.params.state)
        if decision != "approve":
            raise OAuthError(422, "The decision must be approve or deny.")
        code_ok = self.google is None and officer_code and hmac.compare_digest(officer_code.strip().encode(), req.officer_code.encode())
        if not verified and not code_ok:
            req.attempts += 1
            if req.attempts >= self.max_attempts:
                del self.pending[request_id]
                raise OAuthError(410, "Too many wrong codes: this request is locked. Start again from the AI app.")
            raise OAuthError(403, "That officer code is not right.")
        del self.pending[request_id]  # single use, whatever happens next
        try:
            contract = self._slip_draft()
            self.rt.drafts[contract.contract_id] = contract
            confirmed = await confirm_draft(self.rt, contract.contract_id, Column.SENTINEL)
        except (SlipError, ConfirmError, KeyError) as e:
            raise OAuthError(503, f"The slip could not be confirmed: {e}") from e
        code = secrets.token_urlsafe(32)
        self.codes[code] = SentinelAuthCode(
            code=code, scopes=req.params.scopes or [], expires_at=time.time() + self.code_ttl, client_id=req.client.client_id,
            code_challenge=req.params.code_challenge, redirect_uri=req.params.redirect_uri,
            redirect_uri_provided_explicitly=req.params.redirect_uri_provided_explicitly, resource=req.params.resource,
            session_id=confirmed["session_id"])
        await self.rt.bus.publish(make_event("oauth.approved", confirmed["session_id"], Column.SENTINEL, {
            "request_id": request_id, "client_name": req.client.client_name or "an AI client"}))
        return construct_redirect_uri(redirect, code=code, state=req.params.state)

    # ---- tokens --------------------------------------------------------------------------------------------------
    async def load_authorization_code(self, client: OAuthClientInformationFull, authorization_code: str):
        self._purge()
        code = self.codes.get(authorization_code)
        return code if code is not None and code.client_id == client.client_id else None

    def _issue(self, client_id: str, session_id: str, scopes: list[str]) -> OAuthToken:
        """A short access token (our signed session token) for an EXISTING session, plus a rotating refresh token."""
        session = self.rt.store.get(session_id)
        if session is None or not self.rt.store.is_usable(session_id):
            raise TokenError("invalid_grant", "This session is frozen or unknown. Sign in again.")
        remaining = (session.contract.expires_at - datetime.now(timezone.utc)).total_seconds()
        ttl = int(min(ACCESS_TTL_SECONDS, remaining))
        if ttl <= 0:
            raise TokenError("invalid_grant", "The permission slip has expired. Sign in again for a new one.")
        access, _ = mint_session_token(session.contract, session.column, self.rt.key, ttl_seconds=ttl, session_id=session_id)
        refresh = secrets.token_urlsafe(32)
        self.refresh_tokens[refresh] = (RefreshToken(token=refresh, client_id=client_id, scopes=scopes,
                                                     expires_at=int(session.contract.expires_at.timestamp())), session_id)
        return OAuthToken(access_token=access, token_type="Bearer", expires_in=ttl, refresh_token=refresh,
                          scope=" ".join(scopes) or None)

    async def exchange_authorization_code(self, client: OAuthClientInformationFull,
                                          authorization_code: SentinelAuthCode) -> OAuthToken:
        if self.codes.pop(authorization_code.code, None) is None:  # one time: popped before anything is issued
            raise TokenError("invalid_grant", "Authorization code not found or already used.")
        return self._issue(client.client_id, authorization_code.session_id, authorization_code.scopes)

    async def load_refresh_token(self, client: OAuthClientInformationFull, refresh_token: str) -> RefreshToken | None:
        entry = self.refresh_tokens.get(refresh_token)
        if entry is None or entry[0].client_id != client.client_id:
            return None
        if entry[0].expires_at is not None and entry[0].expires_at < time.time():
            del self.refresh_tokens[refresh_token]
            return None
        return entry[0]

    async def exchange_refresh_token(self, client: OAuthClientInformationFull, refresh_token: RefreshToken,
                                     scopes: list[str]) -> OAuthToken:
        entry = self.refresh_tokens.pop(refresh_token.token, None)  # rotation: the old token dies here
        if entry is None:
            raise TokenError("invalid_grant", "Refresh token not found or already used.")
        if not set(scopes) <= set(refresh_token.scopes):
            raise TokenError("invalid_scope", "Requested scopes exceed those originally granted.")
        return self._issue(client.client_id, entry[1], scopes or refresh_token.scopes)

    async def load_access_token(self, token: str) -> AccessToken | None:  # type: ignore[override]
        """The HTTP-layer check: signature, algorithm, audience and expiry only. Whether the session is frozen is left to
        the gateway middleware, which answers a quarantined agent with a clear message instead of a bare 401."""
        try:
            claims = verify_session_token(token, self.rt.key.public_key())
        except SessionError:
            return None
        return AccessToken(token=token, client_id=f"session:{claims.session_id}", scopes=[],
                           expires_at=int(claims.expires_at.timestamp()), claims={"jti": claims.session_id})

    async def verify_token(self, token: str) -> AccessToken | None:  # type: ignore[override]
        return await self.load_access_token(token)

    async def revoke_token(self, token) -> None:  # revocation is disabled; present only to satisfy the interface
        return None


LOGIN_COOKIE = "hexley_officer"
STATE_COOKIE = "hexley_google_state"
LOGIN_DAYS = 30


# ---- the consent page (served by the gateway, so it works over the public tunnel too) --------------------------------
_PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Allow access to Hexley</title><link rel="icon" href="/favicon.svg" type="image/svg+xml"><style>
:root{{color-scheme:light dark;--bg:#f4f4f7;--card:#fff;--ink:#1c1b22;--soft:#62606e;--line:#e2e1e8;--accent:#6a3de8;--on:#fff}}
@media (prefers-color-scheme:dark){{:root{{--bg:#0d0d12;--card:#17171f;--ink:#f2f1f6;--soft:#a3a1b0;--line:#2c2b36;--accent:#9a7bff;--on:#14121f}}}}
*{{box-sizing:border-box}}body{{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:24px 16px;background:var(--bg);color:var(--ink);font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}}
main{{width:100%;max-width:440px;background:var(--card);border:1px solid var(--line);border-radius:14px;padding:32px}}
.brand{{display:flex;align-items:center;justify-content:center;gap:9px;margin-bottom:20px}}.brand svg{{width:30px;height:30px}}.label{{margin:0;font-weight:600;font-size:15px}}
h1{{font-size:21px;line-height:1.3;font-weight:600;text-align:center;margin:0 0 18px}}
.who{{display:flex;align-items:center;justify-content:space-between;gap:10px;border:1px solid var(--line);border-radius:10px;padding:9px 12px;margin:0 0 20px;font-size:14px;overflow-wrap:anywhere}}.who form{{flex:none}}
.lead{{margin:0 0 8px;font-weight:600}}ul.perms{{list-style:none;margin:0 0 16px;padding:0;border-top:1px solid var(--line)}}
ul.perms li{{padding:10px 0 10px 26px;border-bottom:1px solid var(--line);position:relative}}ul.perms li::before{{content:"\\2713";position:absolute;left:3px;color:var(--accent);font-weight:700}}
details{{margin:0 0 20px;font-size:14px}}summary{{cursor:pointer;color:var(--soft)}}details p{{margin:8px 0 0;color:var(--soft);overflow-wrap:anywhere}}details b{{color:var(--ink);font-weight:600}}
.actions{{display:flex;gap:10px;margin:0 0 16px}}.actions button,.actions a{{flex:1;text-align:center;text-decoration:none}}
button,a.go{{font:inherit;font-weight:600;padding:10px 16px;border-radius:9px;border:1px solid var(--accent);background:var(--accent);color:var(--on);cursor:pointer}}
button.ghost{{background:none;border-color:var(--line);color:var(--ink)}}button.link{{background:none;border:0;padding:0;color:var(--accent);font-size:13px;font-weight:500}}
input.proof{{font:inherit;width:100%;padding:10px 12px;margin-top:6px;background:none;color:var(--ink);border:1px solid var(--line);border-radius:9px}}
.err{{color:#d92d3f;font-weight:600;margin:0 0 16px}}.small{{margin:0;font-size:13px;color:var(--soft);text-align:center}}
</style></head><body><main><div class="brand">@LOGO@<p class="label">Hexley</p></div>{body}</main></body></html>""".replace("@LOGO@", LOGO_SVG)


def _page(body: str, status: int = 200) -> HTMLResponse:
    return HTMLResponse(_PAGE.format(body=body), status_code=status, headers={
        "Cache-Control": "no-store", "X-Frame-Options": "DENY", "Referrer-Policy": "no-referrer",
        "Content-Security-Policy": "default-src 'none'; img-src 'self'; style-src 'unsafe-inline'; frame-ancestors 'none'"})


def _lasts(seconds: int) -> str:
    if seconds >= 86400:
        days = seconds // 86400
        return f"{days} day" + ("s" if days != 1 else "")
    return f"{seconds // 60} minutes"


def _proof_field(officer: bool, google: GoogleLogin | None = None) -> str:
    if google is not None:
        return ""
    if officer:
        return '<p class="who">You are logged in as the officer on this browser.</p>'
    return ('<p class="lead"><label>Officer token, needed once on this browser. A code from the server\'s log works too.'
            '<input class="proof" name="officer_code" type="password" autocomplete="current-password" autofocus></label></p>')


def _sign_out(officer: bool) -> str:
    if not officer:
        return ""
    return ('<form method="post" action="/oauth/sign-out"><button class="ghost" name="back" value="1">Log out on this browser</button></form>')


def _words(items: list[str]) -> str:
    return items[0] if len(items) == 1 else f"{', '.join(items[:-1])} and {items[-1]}"


def _places(destinations: list[str]) -> str:
    """Where it may send, as a person says it. The exact channel and page ids are one click away, under the details."""
    kinds = [("channel:", "Slack channel"), ("page:", "Notion page"), ("repo:", "GitHub repository")]
    named = [(sum(d.startswith(prefix) for d in destinations), label) for prefix, label in kinds]
    rest = [d for d in destinations if not d.startswith(tuple(p for p, _ in kinds))]
    places = [f"{n} {label}" + ("" if n == 1 else "s") for n, label in named if n]
    if rest:
        places.insert(0, f"{len(rest)} e-mail address" + ("" if len(rest) == 1 else "es") if all("@" in d for d in rest) else _words(rest))
    return _words(places)


def _permissions(slip: dict) -> list[str]:
    connectors = sorted({t.split(".", 1)[0].capitalize() for t in slip["allowed_tools"] if "." in t})
    used = f"Use your {_words(connectors)} connectors, with Hexley checking each call" if connectors else slip["objective"]
    where = slip["allowed_destinations"]
    limit = slip["max_messages"]
    return [used, f"Send only to {_places(where)} chosen for this task" if where else "Send nothing outside",
            f"Send at most {limit} message" + ("" if limit == 1 else "s"), f"Keep this access for {_lasts(slip['ttl_seconds'])}"]


def _consent_body(view: dict, error: str = "", officer: bool = False, google: GoogleLogin | None = None, email: str | None = None) -> str:
    """The page every connector has: who is asking, which account, what it may do, Cancel or Allow. No code to type (D-060)."""
    e = html.escape
    client, request_id, slip = e(view["client_name"]), e(view["request_id"]), view["slip"]
    hidden = f'<input type="hidden" name="request" value="{request_id}">'
    if google is not None and not email:
        start = f'/oauth/google/start?{urlencode({"request": view["request_id"]})}'
        who = ""
        action = (f'<form method="post" action="/oauth/consent" class="actions">{hidden}<button class="ghost" name="decision" value="deny">Cancel</button>'
                  f'<a class="go" href="{e(start)}">Continue with Google</a></form>')
    else:
        allow = "Allow" if google is not None else "Approve"
        who = (f'<div class="who"><span>Signed in as <b>{e(email)}</b></span><form method="post" action="/oauth/sign-out">{hidden}'
               '<button class="link">Use another account</button></form></div>') if google is not None else ""
        action = (f'<form method="post" action="/oauth/consent">{hidden}{_proof_field(officer, google)}<div class="actions">'
                  f'<button class="ghost" name="decision" value="deny">Cancel</button><button name="decision" value="approve">{allow}</button></div></form>')
    perms = "".join(f"<li>{e(p)}</li>" for p in _permissions(slip))
    places = e(", ".join(slip["allowed_destinations"]) or "nowhere")
    return (f"<h1>{client} wants to connect to Hexley</h1>"
            + (f'<p class="err">{e(error)}</p>' if error else "")
            + f"""{who}<p class="lead">This will let {client}:</p><ul class="perms">{perms}</ul>
<details><summary>See the exact permissions</summary><p><b>Task:</b> {e(slip['objective'])}</p><p><b>May send to:</b> {places}</p>
<p><b>Actions:</b> {e(", ".join(slip["allowed_tools"]))}</p></details>
{action}
<p class="small">Only allow this if you started it from {client}. Hexley never holds your connectors' passwords.</p>
{_sign_out(officer and google is None)}""")


def register_consent_routes(server, provider: SentinelOAuthProvider) -> None:
    """Add GET/POST /oauth/consent to the gateway app."""

    @server.custom_route("/oauth/consent", methods=["GET"])
    async def consent_get(request: Request) -> Response:
        try:
            cookie = request.cookies.get(LOGIN_COOKIE)
            email = provider.google.email_from(cookie) if provider.google else None
            return _page(_consent_body(provider.view(request.query_params.get("request", "")), officer=provider.is_officer(cookie),
                                       google=provider.google, email=email))
        except OAuthError as e:
            return _page(f'<h1>Sign-in not available</h1><p class="err">{html.escape(e.detail)}</p>', e.status)

    @server.custom_route("/oauth/consent", methods=["POST"])
    async def consent_post(request: Request) -> Response:
        if not provider.same_origin(request.headers.get("origin"), request.headers.get("sec-fetch-site")):
            return _page('<h1>Sign-in not available</h1><p class="err">This request came from another site.</p>', 403)
        form = {k: v[0] for k, v in parse_qs((await request.body()).decode("utf-8", "replace")).items()}
        request_id = form.get("request", "")
        proof = form.get("officer_code", "")
        logged_in = provider.is_officer(request.cookies.get(LOGIN_COOKIE))
        by_token = provider.token_ok(proof)
        try:
            target = await provider.decide(request_id, form.get("decision", ""), proof, verified=logged_in or by_token)
        except OAuthError as e:
            if e.status == 403:  # a wrong code: let the officer try again on the same page
                return _page(_consent_body(provider.view(request_id), e.detail, officer=logged_in, google=provider.google), 403)
            return _page(f'<h1>Sign-in not available</h1><p class="err">{html.escape(e.detail)}</p>', e.status)
        response = RedirectResponse(target, status_code=303, headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"})
        if by_token and form.get("decision") == "approve":
            response.set_cookie(LOGIN_COOKIE, provider.login_value(), max_age=LOGIN_DAYS * 86400, path="/oauth/", httponly=True,
                                samesite="lax", secure=provider.consent_base.startswith("https://"))
        return response

    @server.custom_route("/oauth/google/start", methods=["GET"])
    async def google_start(request: Request) -> Response:
        if provider.google is None:
            return _page('<h1>Not available</h1><p class="err">Google sign-in is not configured here.</p>', 404)
        try:
            request_id = request.query_params.get("request", "")
            provider.view(request_id)  # a live request only: this page cannot be used to fish for logins
            if provider.is_officer(request.cookies.get(LOGIN_COOKIE)):  # already logged in on this browser: straight to Allow
                return RedirectResponse(f"/oauth/consent?{urlencode({'request': request_id})}", status_code=303, headers={"Cache-Control": "no-store"})
            target, state = provider.google.start(request_id)
        except (OAuthError, GoogleLoginError) as e:
            return _page(f'<h1>Sign-in not available</h1><p class="err">{html.escape(getattr(e, "detail", str(e)))}</p>', 410)
        response = RedirectResponse(target, status_code=303, headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"})
        response.set_cookie(STATE_COOKIE, state, max_age=600, path="/oauth/google/", httponly=True, samesite="lax",
                            secure=provider.consent_base.startswith("https://"))
        return response

    @server.custom_route("/oauth/google/callback", methods=["GET"])
    async def google_callback(request: Request) -> Response:
        if provider.google is None:
            return _page('<h1>Not available</h1><p class="err">Google sign-in is not configured here.</p>', 404)
        q = request.query_params
        try:
            if q.get("error"):
                raise GoogleLoginError("Google sign-in was cancelled. Start again from the AI app.")
            email, request_id = await provider.google.finish(q.get("state", ""), request.cookies.get(STATE_COOKIE), q.get("code", ""))
        except GoogleLoginError as e:
            return _page(f'<h1>Sign-in not available</h1><p class="err">{html.escape(str(e))}</p>', 403)
        response = RedirectResponse(f"/oauth/consent?{urlencode({'request': request_id})}", status_code=303, headers={"Cache-Control": "no-store"})
        response.set_cookie(LOGIN_COOKIE, provider.google.login_value(email), max_age=LOGIN_SECONDS, path="/oauth/", httponly=True, samesite="lax",
                            secure=provider.consent_base.startswith("https://"))
        response.delete_cookie(STATE_COOKIE, path="/oauth/google/")
        return response

    @server.custom_route("/oauth/sign-out", methods=["POST"])
    async def sign_out(request: Request) -> Response:
        if not provider.same_origin(request.headers.get("origin"), request.headers.get("sec-fetch-site")):
            return _page('<h1>Not available</h1><p class="err">This request came from another site.</p>', 403)
        form = {k: v[0] for k, v in parse_qs((await request.body()).decode("utf-8", "replace")).items()}
        if provider.google is not None and form.get("request"):  # "Use another account": back to Google's picker for the same connection
            response = RedirectResponse(f"/oauth/google/start?{urlencode({'request': form['request']})}", status_code=303,
                                        headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"})
        else:
            response = _page("<h1>Logged out</h1><p>This browser will be asked for the officer token next time.</p>")
        response.delete_cookie(LOGIN_COOKIE, path="/oauth/")
        return response
