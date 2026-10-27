"""REST and WebSocket API for the console (I3, I4). Static bearer token on everything but /health."""

from __future__ import annotations

import asyncio
import functools
import hmac
import json
from pathlib import Path
from typing import Literal

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .approvals import ApprovalError
from .audit import AuditError
from .confirm import ConfirmError, confirm_draft
from .connect import connect_view, issue_header_token
from .contracts import SlipError, draft_contract
from .oauth import OAuthError
from .runs import SCENARIOS, RunError, RunManager, list_recordings
from .events import make_event
from .models import Column, Mode
from .runtime import Runtime
from .tools.server import TOKEN_HEADER

CONSOLE_ORIGIN = "http://localhost:5173"


class TaskRequest(BaseModel):
    template: str
    officer: str
    mode: Mode | None = None  # normally omitted: the template sets the mode; a disagreeing value is refused
    work_item_id: str | None = None  # the quotation this slip is about; resolved through the intake queue


class ConfirmRequest(BaseModel):
    column: Column = Column.SENTINEL


class KillRequest(BaseModel):
    session_id: str


class TamperRequest(BaseModel):
    seq: int | None = None


class ApprovalDecision(BaseModel):
    decision: Literal["approve", "deny"]


class ConnectTokenRequest(BaseModel):
    preset: str = "quotation_processing"


class OAuthDecision(BaseModel):
    decision: Literal["approve", "deny"]
    officer_code: str = ""


class RunRequest(BaseModel):
    scenario: str
    source: Literal["live", "replay", "scripted"] = "scripted"
    model: dict | None = None  # {"provider": "nvidia" | "ollama", "model": "..."} for a live run
    recording_id: str | None = None
    officer: str = "Col. R. Menon"


CONSOLE_DIST = Path(__file__).resolve().parents[2] / "console" / "dist"


def create_api(rt: Runtime, console_dir: Path | None = None) -> FastAPI:
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
            contract = draft_contract(rt.templates, req.template, officer=req.officer, mode=req.mode,
                                      work_item_id=req.work_item_id)
        except KeyError:
            raise HTTPException(status_code=404, detail=f"unknown template {req.template!r}") from None
        except SlipError as e:
            raise HTTPException(status_code=422, detail=str(e)) from e
        rt.drafts[contract.contract_id] = contract
        return contract.model_dump(mode="json")

    @app.post("/tasks/{contract_id}/confirm", dependencies=[Depends(require_token)])
    async def confirm_task(contract_id: str, req: ConfirmRequest):
        """The officer confirms the slip. Only now is a token minted; the agent never creates one."""
        try:
            return await confirm_draft(rt, contract_id, req.column)
        except ConfirmError as e:
            raise HTTPException(status_code=e.status, detail=e.detail) from e

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

    runs = RunManager(rt)
    rt.runs = runs

    def run_errors(fn):
        @functools.wraps(fn)  # keeps the signature, so FastAPI still reads the parameters from it
        async def wrapper(*a, **k):
            try:
                return await fn(*a, **k)
            except RunError as e:
                raise HTTPException(status_code=e.status, detail=e.detail) from e
        return wrapper

    @app.get("/scenarios", dependencies=[Depends(require_token)])
    async def list_scenarios():
        return {"scenarios": [{"id": s.id, "title": s.title, "description": s.description,
                               "lanes": [{"column": l.column.value, "template": l.template} for l in s.lanes]}
                              for s in SCENARIOS.values()]}

    @app.get("/recordings", dependencies=[Depends(require_token)])
    async def get_recordings():
        return {"recordings": list_recordings(rt.recordings_dir)}

    @app.post("/runs", status_code=201, dependencies=[Depends(require_token)])
    @run_errors
    async def create_run(req: RunRequest):
        """Draft one slip per lane. Nothing runs until the officer confirms (POST /runs/{id}/confirm)."""
        run = await runs.create(req.scenario, req.source, req.officer, model=req.model, recording_id=req.recording_id)
        return await runs.view(run.run_id)

    @app.post("/runs/{run_id}/confirm", dependencies=[Depends(require_token)])
    @run_errors
    async def confirm_run(run_id: str):
        run = await runs.confirm(run_id)
        return await runs.view(run.run_id)

    @app.get("/runs", dependencies=[Depends(require_token)])
    async def list_runs():
        """Lets the console re-attach to the active run after a page reload."""
        return runs.list_runs()

    @app.get("/runs/{run_id}", dependencies=[Depends(require_token)])
    @run_errors
    async def get_run(run_id: str):
        return await runs.view(run_id)

    @app.post("/runs/{run_id}/cancel", dependencies=[Depends(require_token)])
    @run_errors
    async def cancel_run(run_id: str):
        await runs.cancel(run_id)
        return await runs.view(run_id)

    @app.get("/approvals", dependencies=[Depends(require_token)])
    async def list_approvals():
        return {"pending": [a.card() for a in rt.approvals.pending()]}

    @app.get("/approvals/{approval_id}", dependencies=[Depends(require_token)])
    async def get_approval(approval_id: str):
        a = rt.approvals.get(approval_id)
        if a is None:
            raise HTTPException(status_code=404, detail="unknown approval")
        return a.card()

    @app.post("/approvals/{approval_id}", dependencies=[Depends(require_token)])
    async def resolve_approval(approval_id: str, req: ApprovalDecision):
        """The officer approves or denies one exact pending action. An approval is recorded durably BEFORE it
        takes effect; a denial never waits on the log."""
        a = rt.approvals.get(approval_id)
        if a is None:
            raise HTTPException(status_code=404, detail="unknown approval")
        approve = req.decision == "approve"
        if approve:
            try:
                await rt.audit.append("approval.resolved", session_id=a.session_id, payload={
                    "approval_id": a.approval_id, "action_hash": a.action_hash, "tool": a.tool, "decision": "approve"})
            except AuditError as e:
                raise HTTPException(status_code=503, detail=f"audit log unavailable: {e}") from e
        try:
            a = rt.approvals.resolve(approval_id, approve)
        except ApprovalError as e:
            raise HTTPException(status_code=409, detail=str(e)) from e
        if not approve:
            try:
                await rt.audit.append("approval.resolved", session_id=a.session_id, payload={
                    "approval_id": a.approval_id, "action_hash": a.action_hash, "tool": a.tool, "decision": "deny"})
            except AuditError:
                pass
        return a.card()

    @app.get("/audit/verify", dependencies=[Depends(require_token)])
    async def audit_verify(expected_head: str | None = None):
        """Re-read the log from disk and check every hash and signature. Truncation is only caught if the
        caller supplies the chain head it saw earlier."""
        res = rt.audit.verify(expected_head)
        return {"ok": res.ok, "checked": res.checked, "head": res.head, "first_bad_seq": res.first_bad_seq,
                "reason": res.reason, "tamper_enabled": rt.allow_tamper}

    @app.get("/audit/export", dependencies=[Depends(require_token)])
    async def audit_export():
        return Response(content=rt.audit.export_lines(), media_type="application/x-ndjson")

    @app.post("/audit/tamper", dependencies=[Depends(require_token)])
    async def audit_tamper(req: TamperRequest = TamperRequest()):
        """DEMO ONLY: alter one record on disk so the console can show detection. Off unless enabled at start.
        Without a `seq` it targets the most recent BLOCK or FREEZE decision, which is the one the audience just saw."""
        if not rt.allow_tamper:
            raise HTTPException(status_code=403, detail="tamper demo is disabled")
        try:
            seq = req.seq if req.seq is not None else rt.audit.latest_block_seq()
            action_id = rt.audit.tamper(seq)
        except AuditError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
        return {"tampered_seq": seq, "action_id": action_id}

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

    # ---- connecting a real client (docs/contracts/API.md; core plan phase B1) --------------------------------------
    @app.get("/api/v1/connect", dependencies=[Depends(require_token)])
    async def connect():
        return connect_view(rt)

    @app.post("/api/v1/connect/token", dependencies=[Depends(require_token)])
    async def connect_token(req: ConnectTokenRequest = ConnectTokenRequest()):
        try:
            return await issue_header_token(rt, req.preset)
        except SlipError as e:
            raise HTTPException(status_code=422, detail=str(e)) from e
        except ConfirmError as e:
            raise HTTPException(status_code=e.status, detail=e.detail) from e

    # The consent endpoints are NOT behind the API token: the officer code is the credential. The officer's browser reaches
    # them from the AI client's sign-in redirect, where the console's token may not be present.
    def oauth_provider():
        if rt.oauth is None:
            raise HTTPException(status_code=404, detail="OAuth is not enabled; start Sentinel with --public-url or --tunnel")
        return rt.oauth

    @app.get("/api/v1/oauth/requests/{request_id}")
    async def oauth_request(request_id: str):
        try:
            return oauth_provider().view(request_id)
        except OAuthError as e:
            raise HTTPException(status_code=e.status, detail=e.detail) from e

    @app.post("/api/v1/oauth/requests/{request_id}")
    async def oauth_decide(request_id: str, req: OAuthDecision):
        try:
            return {"redirect_to": await oauth_provider().decide(request_id, req.decision, req.officer_code)}
        except OAuthError as e:
            raise HTTPException(status_code=e.status, detail=e.detail) from e

    mount_console(app, console_dir)
    return app


class ConsoleFiles(StaticFiles):
    """StaticFiles that answers 404 with an instruction, instead of raising, while the console is not built.
    (Starlette's own check_dir=False still raises RuntimeError at request time, which would be a 500 on stage.)"""

    async def __call__(self, scope, receive, send):
        if not Path(str(self.directory)).is_dir():
            await PlainTextResponse("The console is not built yet. Run: npm --prefix console run build",
                                    status_code=404)(scope, receive, send)
            return
        await super().__call__(scope, receive, send)


def mount_console(app: FastAPI, directory: Path | None = None) -> None:
    """Serve the built console at /console, so `python -m sentinel up` is the only command a demo needs."""
    app.mount("/console", ConsoleFiles(directory=directory or CONSOLE_DIST, html=True, check_dir=False),
              name="console")
