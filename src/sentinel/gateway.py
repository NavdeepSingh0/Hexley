"""The MCP gateway: every agent tool call passes through SentinelMiddleware before anything is forwarded.

Security properties implemented here (ARCHITECTURE.md section 5):
  3  R1 is evaluated on EVERY tools/call, not only reflected in tools/list
  4  incoming agent headers are never forwarded downstream (forward_incoming_headers=False)
  5  the downstream token is added by Sentinel; the agent never holds it
  7  a frozen or revoked session cannot call
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone

from fastmcp import FastMCP
from fastmcp.client.transports import StreamableHttpTransport
from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import get_http_headers
from fastmcp.server.middleware import Middleware
from fastmcp.server.providers.proxy import FastMCPProxy, ProxyClient

from .approvals import ApprovalStatus
from .audit import AuditError, action_payload, decision_payload, result_payload, sha256_hex
from .contracts import Session, SessionError, verify_session_token
from . import egress
from .destinations import extract_destinations
from .engine import decide
from .events import make_event
from .models import (AgentAction, Column, Confidentiality, Decision, Effect, Evidence, Integrity, Mode, ReasonCode,
                     RuleId, SessionStatus)
from .runtime import Runtime
from .tool_pins import definition_hash
from .tools.server import COLUMN_HEADER, SESSION_HEADER, TOKEN_HEADER

log = logging.getLogger("sentinel.gateway")

# The session of the call being forwarded, so the downstream client can label it (for the mail sink).
_current: ContextVar[Session | None] = ContextVar("sentinel_current_session", default=None)
# The recorded hash of the message a fixed-template tool is allowed to send (set only while that call runs).
_egress_expected: ContextVar[str | None] = ContextVar("sentinel_egress_expected", default=None)


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
        allowed = set(session.contract.allowed_tools)
        if session.column == Column.SENTINEL:
            await self._observe_definitions(tools)
        if session.column == Column.UNPROTECTED:
            # The baseline sees every backend tool, but never a gateway-local tool its slip does not allow:
            # otherwise the like-for-like comparison would differ between columns (D-028).
            return [t for t in tools if not self.rt.registry.get(t.name).local or t.name in allowed]
        # Listing is a convenience for the agent, not a control: R1 is enforced again on every call. A tool whose definition
        # changed since it was approved, or whose description reads like instructions, is not shown (plan Q5).
        return [t for t in tools if t.name in allowed and self.rt.registry.is_known(t.name)
                and (session.column != Column.SENTINEL or self.rt.pins.blocked(t.name) is None)]

    async def _observe_definitions(self, tools) -> None:
        """Hash every tool's full definition and compare it with its pin (plan Q5). A new problem is announced once:
        an event for the console and a record in the audit log."""
        for t in tools:
            schema = getattr(t, "parameters", None) or getattr(t, "input_schema", None) or {}
            h = definition_hash(t.name, t.description, schema, getattr(t, "annotations", None))
            state, changed = self.rt.pins.observe(t.name, h, t.description)
            if changed and state.status != "ok":
                payload = {"tool": t.name, "status": state.status, "detail": state.detail, "definition_sha256": h}
                await self.rt.bus.publish(make_event("tool." + state.status, None, None, payload))
                try:
                    await self.rt.audit.append("tool." + state.status, payload=payload)
                except AuditError as e:
                    log.warning("audit append of a tool definition alert failed: %s", e)

    async def _record_decision(self, action: AgentAction, decision: Decision, session: Session, protected: bool) -> Decision:
        """D-020: the decision is recorded durably BEFORE anything is forwarded; no durable record, no action.
        Baseline columns record best-effort (they are controls, not enforcement). Call with the session lock held."""
        try:
            await self.rt.audit.append("decision", session_id=session.session_id, action_id=action.action_id,
                                       decision_id=decision.decision_id,
                                       payload={"action": action_payload(action), "decision": decision_payload(decision)})
        except AuditError as e:
            log.warning("audit append failed for %s: %s", action.action_id, e)
            if protected and decision.effect == Effect.ALLOW:
                return audit_unavailable(action)
        return decision

    async def _evaluate(self, session: Session, action: AgentAction, entry, protected: bool):
        """One locked pass: decide, record, account. Decide, reserve budget, count the block and (on FREEZE)
        revoke all happen under one lock, so two concurrent calls cannot both take the last send slot and a
        freeze takes effect before the next decision. Returns (decision, approval-or-None)."""
        approvals = self.rt.approvals
        async with session.lock:
            if session.status != SessionStatus.ACTIVE:
                raise ToolError("Blocked: this session is frozen. Ask the officer to confirm a new slip.")
            ahash = approvals.hash_for(session.session_id, action.tool, action.args)
            granted = approvals.peek_granted(ahash) if protected else None
            decision = decide(action, session, self.rt.registry, approved=granted is not None)
            approval = None
            if decision.effect == Effect.ASK:
                approval = approvals.request(session.session_id, action.tool, action.args, decision.summary_plain)
            decision = await self._record_decision(action, decision, session, protected)
            if decision.effect == Effect.ALLOW:
                if granted is not None:
                    approvals.consume(ahash)  # one-time: a second identical call needs a new approval (R4 and R7 alike)
                if entry.outbound:
                    session.messages_out += 1  # reserved now; a failed send still counts (conservative)
            elif decision.effect != Effect.ASK and counts_toward_freeze(decision):
                session.blocks += 1
            if decision.effect == Effect.FREEZE:
                self.rt.store.freeze(session.session_id)
        return decision, approval

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
        protected = session.column == Column.SENTINEL
        pin = self.rt.pins.blocked(tool) if protected else None
        if pin is not None:
            # The tool's definition changed since it was approved, or its description reads like instructions to the model:
            # refused until the officer has looked at it (plan Q5). Recorded like any other decision.
            decision = tool_changed(action, pin)
            async with session.lock:
                await self._record_decision(action, decision, session, protected)
            await self.rt.bus.publish(make_event("decision", session.session_id, session.column, decision.model_dump(mode="json")))
            raise ToolError(decision.summary_plain)
        decision, approval = await self._evaluate(session, action, entry, protected)
        await self.rt.bus.publish(make_event("decision", session.session_id, session.column,
                                             decision.model_dump(mode="json")))
        if decision.effect == Effect.ASK and approval is not None:
            # R4: hold this call for the officer. Every other rule runs again once approval arrives, so an
            # approval can never excuse a leak; silence, denial or expiry all end as a BLOCK.
            await self.rt.bus.publish(make_event("approval.pending", session.session_id, session.column, {
                "approval_id": approval.approval_id, "action_id": action.action_id, "tool": tool, "args": args,
                "summary": decision.summary_plain, "expires_in": int(approval.expires - time.time())}))
            status = await self.rt.approvals.wait(approval.approval_id, self.rt.approval_wait)
            await self.rt.bus.publish(make_event("approval.resolved", session.session_id, session.column,
                                                 {"approval_id": approval.approval_id, "action_id": action.action_id,
                                                  "status": status.value}))
            if status == ApprovalStatus.APPROVED:
                decision, approval = await self._evaluate(session, action, entry, protected)
                await self.rt.bus.publish(make_event("decision", session.session_id, session.column,
                                                     decision.model_dump(mode="json")))
            else:
                decision = approval_not_granted(action, status)
                async with session.lock:
                    session.blocks += 1  # an action the officer refused counts as a block
                    await self._record_decision(action, decision, session, protected)
                await self.rt.bus.publish(make_event("decision", session.session_id, session.column,
                                                     decision.model_dump(mode="json")))
        if decision.effect == Effect.FREEZE:
            await self.rt.bus.publish(make_event("freeze", session.session_id, session.column,
                                                 {"reason": "block threshold", "blocks": session.blocks,
                                                  "decision_id": decision.decision_id}))
        if decision.effect != Effect.ALLOW:
            raise ToolError(decision.agent_summary or decision.summary_plain)
        # For a fixed-template tool, hand the tool the hash of the message the decision recorded, so it can
        # refuse to send anything different (D-020).
        egress_ev = next((e for e in decision.evidence if e.kind == "egress" and e.source_ref), None)
        reset = _current.set(session)
        reset_expected = _egress_expected.set(egress_ev.source_ref if egress_ev else None)
        try:
            result = await call_next(context)
        finally:
            _egress_expected.reset(reset_expected)
            _current.reset(reset)
        text = _result_text(result)
        await self.rt.bus.publish(make_event("action.completed", session.session_id, session.column, {
            "action_id": action.action_id, "tool": tool, "ok": True, "result_sha256": sha256_hex(text),
            "chars": len(text)}))
        try:
            await self.rt.audit.append("result", session_id=session.session_id, action_id=action.action_id,
                                       decision_id=decision.decision_id, payload=result_payload(tool, text))
        except AuditError as e:
            log.warning("audit append of result failed for %s: %s", action.action_id, e)
            if protected and entry.output_confidentiality == Confidentiality.RESTRICTED:
                # A restricted result is not handed to the agent unless the record of it is durable.
                raise ToolError("Blocked: Sentinel could not record this result in its audit log, so it was withheld.") from e
            if protected and entry.consequential:
                # The action already ran and cannot be undone or retried: freeze the session and raise the alarm.
                self.rt.store.freeze(session.session_id)
                await self.rt.bus.publish(make_event("audit.failure", session.session_id, session.column,
                                                     {"tool": tool, "action_id": action.action_id,
                                                      "detail": "audit record of an executed action could not be written"}))
                await self.rt.bus.publish(make_event("freeze", session.session_id, session.column,
                                                     {"reason": "audit failure after execution",
                                                      "decision_id": decision.decision_id}))
        # Any credential in any result is remembered, whatever the tool's label: a key in a runbook or a token in a ticket
        # must never be sent out or used by this session (R2, R9; plan Q2).
        if protected and session.secrets.add(text, source_ref=tool, action_id=action.action_id):
            session.restricted_reads.setdefault(tool, "read a credential")
        # Label what came back from the registry (never from the content) and remember restricted values,
        # so a later outbound call can be checked against them (R2).
        if protected and entry.output_confidentiality == Confidentiality.RESTRICTED:
            session.restricted_reads.setdefault(tool, "read restricted data")  # R8 (Rule of Two), with or without fingerprints
            if entry.fingerprint_fields:
                session.index.add(text, entry.fingerprint_fields, source_ref=tool, action_id=action.action_id)
        # Addresses found in untrusted content are remembered so R3 can refuse them as destinations later.
        if protected and entry.output_integrity == Integrity.UNTRUSTED:
            session.tainted_by.setdefault(tool, "read untrusted content")  # R7: from now on consequential actions ask
            for address in extract_destinations(text):
                if address not in session.untrusted_destinations:  # remember the first source, and the exact call
                    session.untrusted_destinations[address] = tool
                    session.untrusted_actions[address] = action.action_id
        return result


def counts_toward_freeze(decision: Decision) -> bool:
    """R6 counts policy blocks only. An engine fault (FAIL_CLOSED) or a session problem is not the agent's
    attempt, and tool errors or timeouts never reach this function at all."""
    return decision.effect in (Effect.BLOCK, Effect.FREEZE) and decision.reason_code not in (
        ReasonCode.FAIL_CLOSED, ReasonCode.SESSION_INVALID, ReasonCode.AUDIT_UNAVAILABLE)


def approval_not_granted(action: AgentAction, status: ApprovalStatus) -> Decision:
    reason = {"denied": "the officer did not approve it", "expired": "no approval arrived in time"}.get(
        status.value, "it was not approved")
    return Decision(
        decision_id=f"dec_{uuid.uuid4().hex[:12]}", action_id=action.action_id, effect=Effect.BLOCK,
        rule_ids=[RuleId.R4], reason_code=ReasonCode.HUMAN_VERIFICATION,
        summary_plain=f"Blocked: '{action.tool}' did not run because {reason}.",
        evidence=[Evidence(kind="approval", detail=f"approval {status.value}", source_ref=action.tool)])


def tool_changed(action: AgentAction, pin) -> Decision:
    why = ("its definition changed since the officer approved it" if pin.status == "changed"
           else f"its description reads like instructions to the model ({pin.detail})")
    return Decision(
        decision_id=f"dec_{uuid.uuid4().hex[:12]}", action_id=action.action_id, effect=Effect.BLOCK,
        rule_ids=[RuleId.R1], reason_code=ReasonCode.TOOL_CHANGED,
        summary_plain=f"Blocked: '{action.tool}' is held for review because {why}. The officer must approve its definition first.",
        evidence=[Evidence(kind="definition", detail=pin.detail or pin.status, source_ref=pin.seen_hash[:16])])


def audit_unavailable(action: AgentAction) -> Decision:
    return Decision(
        decision_id=f"dec_{uuid.uuid4().hex[:12]}", action_id=action.action_id, effect=Effect.BLOCK,
        reason_code=ReasonCode.AUDIT_UNAVAILABLE,
        summary_plain="Blocked: Sentinel could not record this action in its audit log, so it did not run.",
        evidence=[Evidence(kind="audit", detail="durable audit write failed or missed its deadline")])


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

    # With OAuth on (rt.oauth set by `up --public-url/--tunnel`), the HTTP layer demands a valid bearer token and answers
    # a client without one with the 401 that starts the sign-in. Off by default: the header route works either way, and
    # the middleware below remains the real check on every call.
    oauth = getattr(rt, "oauth", None)
    proxy = FastMCPProxy(client_factory=client_factory, name="sentinel-gateway", **({"auth": oauth} if oauth else {}))
    proxy.add_middleware(SentinelMiddleware(rt))
    if oauth is not None:
        from .oauth import register_consent_routes

        register_consent_routes(proxy, oauth)

    @proxy.tool
    async def send_quote_ack(quote_id: str) -> str:
        """Acknowledge receipt of a quotation to its vendor with Sentinel's fixed message.
        Give only the quotation id; Sentinel writes the message and chooses the recipient."""
        # The middleware has already decided. This body runs only for an allowed call, and it still checks
        # everything itself: it is the code that finally sends, so it must not trust its caller.
        session, expected = _current.get(), _egress_expected.get()
        if session is None or expected is None or session.contract.mode != Mode.HARDENED:
            raise ToolError("Blocked: send_quote_ack needs a confirmed hardened-mode slip.")
        template = egress.find_template(session.contract, "quote_ack_v1")
        if template is None:
            raise ToolError("Blocked: this slip defines no acknowledgement template.")
        try:
            msg = egress.render(template, {"quote_id": quote_id}, session.contract)
        except ValueError as e:
            raise ToolError(f"Blocked: {e}") from e
        if msg.message_sha256 != expected:
            raise ToolError("Blocked: the message differs from the one recorded for this decision, so it was not sent.")
        # Call the tool server directly. proxy.call_tool would run the middleware a second time and double-count
        # the budget, the audit record and the block counter.
        async with client_factory() as backend:
            await backend.call_tool("send_email", {"to": msg.to, "subject": msg.subject, "body": msg.body})
        await rt.bus.publish(make_event("egress.rendered", session.session_id, session.column, {
            "template_id": msg.template_id, "to": msg.to, "subject": msg.subject, "body": msg.body,
            "message_sha256": msg.message_sha256}))
        return f"Acknowledgement sent to {msg.to}."

    return proxy
