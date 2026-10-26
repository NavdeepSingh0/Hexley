"""The officer's confirmation of a slip: the only place a session token is created.

Used by POST /tasks/{id}/confirm and by the runs manager. The agent never reaches this code.
"""

from __future__ import annotations

from datetime import datetime, timezone

from .audit import AuditError
from .contracts import SessionError, mint_session_token, verify_session_token
from .events import make_event
from .models import Column, SessionStatus
from .runtime import Runtime


class ConfirmError(Exception):
    def __init__(self, status: int, detail: str):
        super().__init__(detail)
        self.status, self.detail = status, detail


async def confirm_draft(rt: Runtime, contract_id: str, column: Column) -> dict:
    """Activate a pending slip, record the confirmation durably, and mint the session token."""
    draft = rt.drafts.pop(contract_id, None)
    if draft is None:
        raise ConfirmError(404, "no pending contract with that id (already confirmed?)")
    contract = draft.model_copy(update={"status": SessionStatus.ACTIVE})
    ttl = max(1, int((contract.expires_at - datetime.now(timezone.utc)).total_seconds()))
    token, _ = mint_session_token(contract, column, rt.key, ttl_seconds=ttl)
    try:
        claims = verify_session_token(token, rt.key.public_key())
    except SessionError as e:  # pragma: no cover - would indicate a bug in minting
        raise ConfirmError(500, str(e)) from e
    try:  # the officer's confirmation is the first record of the session; no record, no session
        await rt.audit.append("contract.issued", session_id=claims.session_id, payload={
            "contract_id": contract.contract_id, "contract_hash": contract.contract_hash,
            "template": contract.template, "mode": contract.mode.value, "officer": contract.officer,
            "allowed_tools": contract.allowed_tools, "column": column.value,
            "work_item_id": contract.work_item_id})
    except AuditError as e:
        rt.drafts[contract_id] = draft  # the officer can try again
        raise ConfirmError(503, f"audit log unavailable: {e}") from e
    session = rt.store.add(claims, contract)
    session.trusted_addresses = rt.trusted_addresses  # the vendor records, never the documents
    await rt.bus.publish(make_event("contract.issued", session.session_id, session.column,
                                    {"contract": contract.model_dump(mode="json")}))
    await rt.bus.publish(make_event("session.started", session.session_id, session.column,
                                    {"mcp_url": rt.gateway_url, "expires_at": claims.expires_at.isoformat()}))
    return {"session_id": session.session_id, "session_token": token, "mcp_url": rt.gateway_url,
            "contract_hash": contract.contract_hash, "column": session.column.value,
            "expires_at": claims.expires_at.isoformat()}
