"""REST and WebSocket API for the console (I3, I4). Static bearer token on everything but /health."""

from __future__ import annotations

import asyncio
import hmac
import json
from datetime import datetime, timezone

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

from .audit import AuditError
from .contracts import SessionError, draft_contract, mint_session_token, verify_session_token
from .events import make_event
from .models import Column, Mode, SessionStatus
from .runtime import Runtime
from .tools.server import TOKEN_HEADER

CONSOLE_ORIGIN = "http://localhost:5173"


class TaskRequest(BaseModel):
    template: str
    officer: str
    mode: Mode = Mode.FINGERPRINT


class ConfirmRequest(BaseModel):
    column: Column = Column.SENTINEL


class KillRequest(BaseModel):
    session_id: str


class TamperRequest(BaseModel):
    seq: int


def create_api(rt: Runtime) -> FastAPI:
    app = FastAPI(title="Sentinel API", version="0.1")
    app.add_middleware(CORSMiddleware, allow_origins=[CONSOLE_ORIGIN], allow_methods=["*"], allow_headers=["*"])

    def authorised(token: str) -> bool:
        return hmac.compare_digest(token.encode(), rt.api_token.encode())

    def require_token(authorization: str = Header(default="")) -> None:
        if not authorization.startswith("Bearer ") or not authorised(authorization.removeprefix("Bearer ")):
            raise HTTPException(status_code=401, detail="missing or invalid API token")

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.post("/tasks", dependencies=[Depends(require_token)])
    async def create_task(req: TaskRequest):
        try:
            contract = draft_contract(rt.templates, req.template, officer=req.officer, mode=req.mode)
        except KeyError:
            raise HTTPException(status_code=404, detail=f"unknown template {req.template!r}") from None
        rt.drafts[contract.contract_id] = contract
        return contract.model_dump(mode="json")

    @app.post("/tasks/{contract_id}/confirm", dependencies=[Depends(require_token)])
    async def confirm_task(contract_id: str, req: ConfirmRequest):
        """The officer confirms the slip. Only now is a token minted; the agent never creates one."""
        draft = rt.drafts.pop(contract_id, None)
        if draft is None:
            raise HTTPException(status_code=404, detail="no pending contract with that id (already confirmed?)")
        contract = draft.model_copy(update={"status": SessionStatus.ACTIVE})
        ttl = max(1, int((contract.expires_at - datetime.now(timezone.utc)).total_seconds()))
        token, _ = mint_session_token(contract, req.column, rt.key, ttl_seconds=ttl)
        try:
            claims = verify_session_token(token, rt.key.public_key())
        except SessionError as e:  # pragma: no cover - would indicate a bug in minting
            raise HTTPException(status_code=500, detail=str(e)) from e
        try:  # the officer's confirmation is the first record of the session; no record, no session
            await rt.audit.append("contract.issued", session_id=claims.session_id, payload={
                "contract_id": contract.contract_id, "contract_hash": contract.contract_hash,
                "template": contract.template, "mode": contract.mode.value, "officer": contract.officer,
                "allowed_tools": contract.allowed_tools, "column": req.column.value})
        except AuditError as e:
            rt.drafts[contract_id] = draft  # the officer can try again
            raise HTTPException(status_code=503, detail=f"audit log unavailable: {e}") from e
        session = rt.store.add(claims, contract)
        await rt.bus.publish(make_event("contract.issued", session.session_id, session.column,
                                        {"contract": contract.model_dump(mode="json")}))
        await rt.bus.publish(make_event("session.started", session.session_id, session.column,
                                        {"mcp_url": rt.gateway_url, "expires_at": claims.expires_at.isoformat()}))
        return {"session_id": session.session_id, "session_token": token, "mcp_url": rt.gateway_url,
                "contract_hash": contract.contract_hash, "column": session.column.value,
                "expires_at": claims.expires_at.isoformat()}

    @app.get("/sessions/{session_id}", dependencies=[Depends(require_token)])
    async def get_session(session_id: str):
        s = rt.store.get(session_id)
        if s is None:
            raise HTTPException(status_code=404, detail="unknown session")
        return {"session_id": s.session_id, "column": s.column.value, "status": s.status.value,
                "blocks": s.blocks, "contract_id": s.contract.contract_id}

    @app.post("/killswitch", dependencies=[Depends(require_token)])
    async def killswitch(req: KillRequest):
        s = rt.store.get(req.session_id)
        if s is None:
            raise HTTPException(status_code=404, detail="unknown session")
        rt.store.freeze(req.session_id)  # the safety action never waits on the audit log
        try:
            await rt.audit.append("freeze", session_id=s.session_id, payload={"reason": "kill switch"})
        except AuditError:
            pass  # the freeze stands; the missing record is itself visible as a gap in the log
        await rt.bus.publish(make_event("freeze", s.session_id, s.column, {"reason": "kill switch"}))
        return {"session_id": s.session_id, "status": s.status.value}

    @app.get("/audit/verify", dependencies=[Depends(require_token)])
    async def audit_verify(expected_head: str | None = None):
        """Re-read the log from disk and check every hash and signature. Truncation is only caught if the
        caller supplies the chain head it saw earlier."""
        res = rt.audit.verify(expected_head)
        return {"ok": res.ok, "checked": res.checked, "head": res.head, "first_bad_seq": res.first_bad_seq,
                "reason": res.reason}

    @app.get("/audit/export", dependencies=[Depends(require_token)])
    async def audit_export():
        return Response(content=rt.audit.export_lines(), media_type="application/x-ndjson")

    @app.post("/audit/tamper", dependencies=[Depends(require_token)])
    async def audit_tamper(req: TamperRequest):
        """DEMO ONLY: alter one record on disk so the console can show detection. Off unless enabled at start."""
        if not rt.allow_tamper:
            raise HTTPException(status_code=403, detail="tamper demo is disabled")
        try:
            rt.audit.tamper(req.seq)
        except AuditError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
        return {"tampered_seq": req.seq}

    @app.get("/inbox", dependencies=[Depends(require_token)])
    async def inbox(column: str | None = None):
        """What actually reached the outside world, as recorded by the mail sink on the tool server."""
        base = rt.tools_url.removesuffix("/mcp")
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"{base}/inbox", params={"column": column} if column else None,
                                 headers={TOKEN_HEADER: rt.downstream_token})
        r.raise_for_status()
        return r.json()

    @app.websocket("/ws")
    async def ws(websocket: WebSocket):
        await websocket.accept()
        try:
            first = json.loads(await asyncio.wait_for(websocket.receive_text(), timeout=10))
            if first.get("type") != "auth" or not authorised(str(first.get("token", ""))):
                await websocket.close(code=4401)
                return
        except (asyncio.TimeoutError, json.JSONDecodeError, WebSocketDisconnect):
            await websocket.close(code=4401)
            return
        queue: asyncio.Queue = asyncio.Queue(maxsize=1000)

        async def push(event):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:  # a slow console must not block the gateway
                pass

        for ev in rt.bus.recent(200):  # late joiners see recent history
            queue.put_nowait(ev)
        unsubscribe = rt.bus.subscribe(push)
        try:
            await websocket.send_json({"type": "auth.ok"})
            reader = asyncio.create_task(websocket.receive_text())
            while True:
                getter = asyncio.create_task(queue.get())
                done, _ = await asyncio.wait({getter, reader}, return_when=asyncio.FIRST_COMPLETED)
                if reader in done:
                    getter.cancel()
                    break  # client sent something or disconnected; the console only listens
                await websocket.send_json(getter.result().model_dump(mode="json"))
        except WebSocketDisconnect:
            pass
        finally:
            unsubscribe()

    return app
