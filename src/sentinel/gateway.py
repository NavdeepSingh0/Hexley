"""The MCP gateway: every agent tool call passes through SentinelMiddleware before anything is forwarded.

Security properties implemented here (ARCHITECTURE.md section 5):
  3  R1 is evaluated on EVERY tools/call, not only reflected in tools/list
  4  incoming agent headers are never forwarded downstream (forward_incoming_headers=False)
  5  the downstream token is added by Sentinel; the agent never holds it
  7  a frozen or revoked session cannot call
"""

from __future__ import annotations

import json
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone

from fastmcp import FastMCP
from fastmcp.client.transports import StreamableHttpTransport
from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import get_http_headers
from fastmcp.server.middleware import Middleware
from fastmcp.server.providers.proxy import FastMCPProxy, ProxyClient

from .contracts import Session, SessionError, verify_session_token
from .engine import decide
from .events import make_event
from .models import AgentAction, Column, Confidentiality, Effect
from .runtime import Runtime
from .tools.server import COLUMN_HEADER, SESSION_HEADER, TOKEN_HEADER

# The session of the call being forwarded, so the downstream client can label it (for the mail sink).
_current: ContextVar[Session | None] = ContextVar("sentinel_current_session", default=None)


class SentinelMiddleware(Middleware):
    def __init__(self, rt: Runtime):
        self.rt = rt

    async def _session(self) -> Session:
        """Authenticate the caller. Anything unclear is a BLOCK (fail closed)."""
        auth = get_http_headers(include={"authorization"}).get("authorization", "")
        token = auth.removeprefix("Bearer ").strip() if auth.startswith("Bearer ") else ""
        if not token:
            raise ToolError("Blocked: no session token. Start a task and confirm its permission slip first.")
        try:
            claims = verify_session_token(token, self.rt.key.public_key(), revoked=self.rt.store.revoked)
        except SessionError as e:
            raise ToolError(f"Blocked: this session is not valid ({e}). Ask the officer to confirm a new slip.") from e
        session = self.rt.store.get(claims.session_id)
        if session is None or not self.rt.store.is_usable(claims.session_id):
            raise ToolError("Blocked: this session is frozen or unknown. Ask the officer to confirm a new slip.")
        return session

    async def on_list_tools(self, context, call_next):
        session = await self._session()
        reset = _current.set(session)
        try:
            tools = await call_next(context)
        finally:
            _current.reset(reset)
        if session.column == Column.UNPROTECTED:
            return tools
        allowed = set(session.contract.allowed_tools)
        # Listing is a convenience for the agent, not a control: R1 is enforced again on every call.
        return [t for t in tools if t.name in allowed and self.rt.registry.is_known(t.name)]

    async def on_call_tool(self, context, call_next):
        session = await self._session()
        tool = context.message.name
        args = context.message.arguments or {}
        entry = self.rt.registry.get(tool)
        action = AgentAction(
            action_id=f"act_{uuid.uuid4().hex[:12]}", ts=datetime.now(timezone.utc),
            session_id=session.session_id, contract_id=session.contract.contract_id, column=session.column,
            tool=tool, capability=entry.capability, resource_class=entry.resource_class, args=args,
            outbound=entry.outbound)
        await self.rt.bus.publish(make_event("action.requested", session.session_id, session.column,
                                             action.model_dump(mode="json")))
        decision = decide(action, session, self.rt.registry)
        await self.rt.bus.publish(make_event("decision", session.session_id, session.column,
                                             decision.model_dump(mode="json")))
        if decision.effect != Effect.ALLOW:
            session.blocks += 1
            raise ToolError(decision.summary_plain)
        reset = _current.set(session)
        try:
            result = await call_next(context)
        finally:
            _current.reset(reset)
        # Label what came back from the registry (never from the content) and remember restricted values,
        # so a later outbound call can be checked against them (R2).
        if session.column == Column.SENTINEL and entry.output_confidentiality == Confidentiality.RESTRICTED \
                and entry.fingerprint_fields:
            session.index.add(_result_text(result), entry.fingerprint_fields, source_ref=tool)
        return result


def _result_text(result) -> str:
    parts = [getattr(p, "text", "") for p in (getattr(result, "content", None) or [])]
    structured = getattr(result, "structured_content", None)
    if structured:
        parts.append(json.dumps(structured, default=str))
    return "\n".join(p for p in parts if p)


def build_gateway(rt: Runtime) -> FastMCP:
    def client_factory() -> ProxyClient:
        session = _current.get()
        headers = {TOKEN_HEADER: rt.downstream_token}
        if session is not None:
            headers[SESSION_HEADER] = session.session_id
            headers[COLUMN_HEADER] = session.column.value
        # Never forward what the agent sent: Sentinel alone decides which headers the tools see.
        return ProxyClient(StreamableHttpTransport(rt.tools_url, headers=headers), forward_incoming_headers=False)

    proxy = FastMCPProxy(client_factory=client_factory, name="sentinel-gateway")
    proxy.add_middleware(SentinelMiddleware(rt))
    return proxy
