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

import hmac
import html
import logging
import secrets
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import parse_qs

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
from .contracts import SessionError, SlipError, draft_contract, mint_session_token, verify_session_token
from .events import make_event
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
                 max_pending: int = 50, on_request=None):
        super().__init__(base_url=base_url,
                         client_registration_options=ClientRegistrationOptions(enabled=True),
                         revocation_options=RevocationOptions(enabled=False))  # disconnecting simply lets the token lapse
        self.rt = rt
        self.consent_base = (consent_base_url or base_url).rstrip("/")
        self.preset, self.work_item_id, self.slip_ttl = preset, work_item_id, slip_ttl
        self.request_ttl, self.code_ttl, self.max_attempts = request_ttl, code_ttl, max_attempts
        self.max_clients, self.max_pending = max_clients, max_pending
        self.on_request = on_request  # called with the new PendingRequest: prints the officer code in the terminal
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
        templates = {**self.rt.templates, self.preset: {**self.rt.templates[self.preset], "ttl_seconds": self.slip_ttl}}
        return draft_contract(templates, self.preset, officer=OFFICER, work_item_id=self.work_item_id)

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

    async def decide(self, request_id: str, decision: str, officer_code: str) -> str:
        """The officer approves or denies. Returns the address to send the browser back to the AI client."""
        req = self._get_pending(request_id)
        redirect = str(req.params.redirect_uri)
        if decision == "deny":
            del self.pending[request_id]
            return construct_redirect_uri(redirect, error="access_denied", state=req.params.state)
        if decision != "approve":
            raise OAuthError(422, "The decision must be approve or deny.")
        if not (officer_code and hmac.compare_digest(officer_code.strip().encode(), req.officer_code.encode())):
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


# ---- the consent page (served by the gateway, so it works over the public tunnel too) --------------------------------
_PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sentinel: approve the permission slip</title><style>
:root{{color-scheme:dark}}body{{margin:0;background:#1f1f1e;color:#f2f1ed;font:18px/1.45 "Helvetica Neue",Helvetica,Arial,sans-serif}}
main{{max-width:760px;margin:0 auto;padding:40px 16px}}.label{{text-transform:uppercase;letter-spacing:.18em;font-size:13px;color:#a3a29d}}
h1{{font-size:34px;letter-spacing:-.01em;margin:8px 0 20px}}.slip{{border:2px solid #f2f1ed;padding:16px 20px;margin:0 0 24px}}
dl{{display:grid;grid-template-columns:170px 1fr;gap:6px 14px;margin:12px 0 0}}dt{{color:#a3a29d}}dd{{margin:0;font-weight:600}}
input{{font:inherit;font-size:28px;letter-spacing:.3em;width:9em;padding:8px 12px;background:#262625;color:#f2f1ed;border:1px solid #3b3b39}}
button{{font:inherit;font-weight:600;padding:10px 22px;margin-right:10px;border:2px solid #f2f1ed;background:#f2f1ed;color:#1f1f1e;cursor:pointer}}
button.ghost{{background:none;color:#f2f1ed}}.err{{color:#ff7f73;font-weight:600;margin:0 0 16px}}.muted{{color:#a3a29d;font-size:15px}}
</style></head><body><main><p class="label">Sentinel · officer approval</p>{body}</main></body></html>"""


def _page(body: str, status: int = 200) -> HTMLResponse:
    return HTMLResponse(_PAGE.format(body=body), status_code=status, headers={
        "Cache-Control": "no-store", "X-Frame-Options": "DENY", "Referrer-Policy": "no-referrer",
        "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; frame-ancestors 'none'"})


def _consent_body(view: dict, error: str = "") -> str:
    e = html.escape
    slip = view["slip"]
    tools = ", ".join(slip["allowed_tools"])
    return (f"<h1>{e(view['client_name'])} wants to connect to Sentinel</h1>"
            + (f'<p class="err">{e(error)}</p>' if error else "")
            + f"""<div class="slip"><span class="label">The permission slip you are approving</span>
<p><b>{e(slip['objective'])}</b></p><dl><dt>Allowed actions</dt><dd>{e(tools)}</dd>
<dt>May write to</dt><dd>{e(', '.join(slip['allowed_destinations']) or 'nobody')}</dd>
<dt>Message limit</dt><dd>{slip['max_messages']}</dd><dt>Lasts</dt><dd>{slip['ttl_seconds'] // 60} minutes</dd></dl></div>
<form method="post" action="/oauth/consent"><input type="hidden" name="request" value="{e(view['request_id'])}">
<p>Officer code (shown in the Sentinel terminal and console):</p>
<p><input name="officer_code" inputmode="numeric" autocomplete="off" maxlength="6" autofocus></p>
<button name="decision" value="approve">Approve</button><button class="ghost" name="decision" value="deny">Deny</button></form>
<p class="muted">Only approve if you started this connection. The AI can do what the slip lists and nothing else.</p>""")


def register_consent_routes(server, provider: SentinelOAuthProvider) -> None:
    """Add GET/POST /oauth/consent to the gateway app."""

    @server.custom_route("/oauth/consent", methods=["GET"])
    async def consent_get(request: Request) -> Response:
        try:
            return _page(_consent_body(provider.view(request.query_params.get("request", ""))))
        except OAuthError as e:
            return _page(f'<h1>Sign-in not available</h1><p class="err">{html.escape(e.detail)}</p>', e.status)

    @server.custom_route("/oauth/consent", methods=["POST"])
    async def consent_post(request: Request) -> Response:
        form = {k: v[0] for k, v in parse_qs((await request.body()).decode("utf-8", "replace")).items()}
        request_id = form.get("request", "")
        try:
            target = await provider.decide(request_id, form.get("decision", ""), form.get("officer_code", ""))
        except OAuthError as e:
            if e.status == 403:  # a wrong code: let the officer try again on the same page
                return _page(_consent_body(provider.view(request_id), e.detail), 403)
            return _page(f'<h1>Sign-in not available</h1><p class="err">{html.escape(e.detail)}</p>', e.status)
        return RedirectResponse(target, status_code=303, headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"})
