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
from fastapi.responses import FileResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport
from pydantic import BaseModel, ConfigDict
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.websockets import WebSocketClose

from .approvals import ApprovalError
from .chat import ChatError, ChatManager
from .audit import AuditError
from .confirm import ConfirmError, confirm_draft
from .connect import connect_view, issue_header_token
from .contracts import SlipError, draft_contract, draft_custom
from .matcher import FIELD_KINDS
from .oauth import OAuthError
from .registry import save_overlay, suggest_classification
from .runs import SCENARIOS, RunError, RunManager, list_recordings
from .events import make_event
from .models import Capability, Column, Confidentiality, Integrity, Mode, ToolEntry
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


class ToolClassification(BaseModel):
    """What the officer says about a tool. No `local` and no `egress_template`: a classification labels risk, nothing more."""

    model_config = ConfigDict(extra="forbid")
    capability: Capability
    resource_class: str | None = None
    outbound: bool
    consequential: bool
    output_integrity: Integrity
    output_confidentiality: Confidentiality
    fingerprint_fields: list[str] = []
    destination_args: list[str] = []
    destination_kind: Literal["email", "url", "path"] = "email"
    requires_human_verification: bool = False


class SlipRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    objective: str
    allowed_tools: list[str]
    allowed_destinations: list[str] = []
    internal_destinations: list[str] = []
    max_messages: int = 1
    ttl_seconds: int = 900
    officer: str = "Col. R. Menon"
    confirm: bool = False


class OAuthDecision(BaseModel):
    decision: Literal["approve", "deny"]
    officer_code: str = ""


class ChatRequest(BaseModel):
    preset: str
    mode: Literal["auto", "live", "scripted", "replay"] = "auto"  # auto: a live model when a key is set, else a scripted agent
    recording: dict | None = None  # for mode=replay: an export of an earlier chat (GET /api/v1/chat/{id}/recording)
    officer: str = "Col. R. Menon"


class ChatMessageRequest(BaseModel):
    text: str


class RunRequest(BaseModel):
    scenario: str
    source: Literal["live", "replay", "scripted"] = "scripted"
    model: dict | None = None  # {"provider": "nvidia" | "ollama", "model": "..."} for a live run
    recording_id: str | None = None
    officer: str = "Col. R. Menon"


CONSOLE_DIST = Path(__file__).resolve().parents[2] / "console" / "dist"
SITE_DIST = Path(__file__).resolve().parents[2] / "site" / "dist"


def create_api(rt: Runtime, console_dir: Path | None = None, site_dir: Path | None = None) -> FastAPI:
    # FastAPI's own /docs, /redoc and /openapi.json are off: /docs is the website's documentation page (core plan, F6).
    app = FastAPI(title="Sentinel API", version="0.1", docs_url=None, redoc_url=None, openapi_url=None)
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
    chats = ChatManager(rt)
    rt.chats = chats

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
    # Public on purpose (D-041): it holds no secret (statuses, steps, the address an AI client is meant to paste), so the
    # site's Connect and Integrations pages work without the officer token. Creating a token below still needs it.
    @app.get("/api/v1/connect")
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


    # ---- Sentinel Chat (core plan B5; docs/contracts/API.md) -----------------------------------------------------------
    def chat_error(e: ChatError) -> HTTPException:
        return HTTPException(status_code=e.status, detail=e.detail)

    @app.get("/api/v1/chat/presets", dependencies=[Depends(require_token)])
    async def chat_presets():
        return chats.presets()

    @app.post("/api/v1/chat", status_code=201, dependencies=[Depends(require_token)])
    async def chat_create(req: ChatRequest):
        try:
            chat = await chats.create(req.preset, req.mode, req.recording, req.officer)
            return chats.view(chat.chat_id)
        except ChatError as e:
            raise chat_error(e) from e

    @app.post("/api/v1/chat/{chat_id}/confirm", dependencies=[Depends(require_token)])
    async def chat_confirm(chat_id: str):
        try:
            await chats.confirm(chat_id)
            return chats.view(chat_id)
        except ChatError as e:
            raise chat_error(e) from e

    @app.post("/api/v1/chat/{chat_id}/messages", status_code=202, dependencies=[Depends(require_token)])
    async def chat_send(chat_id: str, req: ChatMessageRequest):
        try:
            return {"message_id": await chats.send(chat_id, req.text)}
        except ChatError as e:
            raise chat_error(e) from e

    @app.get("/api/v1/chat/{chat_id}", dependencies=[Depends(require_token)])
    async def chat_view(chat_id: str):
        try:
            return chats.view(chat_id)
        except ChatError as e:
            raise chat_error(e) from e

    @app.get("/api/v1/chat/{chat_id}/recording", dependencies=[Depends(require_token)])
    async def chat_recording(chat_id: str):
        try:
            return chats.recording(chat_id)
        except ChatError as e:
            raise chat_error(e) from e

    # ---- tool onboarding: nothing new runs until the officer has classified it (core plan B2) -------------------------
    async def upstream_tools():
        try:
            async with Client(StreamableHttpTransport(rt.tools_url, headers={TOKEN_HEADER: rt.downstream_token})) as c:
                return await asyncio.wait_for(c.list_tools(), timeout=10)
        except Exception as e:  # noqa: BLE001 - reported plainly, never leaked as a stack trace
            raise HTTPException(status_code=503, detail="Sentinel could not read the tool list from the tool server.") from e

    def schema_of(tool) -> dict:
        return getattr(tool, "input_schema", None) or getattr(tool, "inputSchema", None) or {}

    @app.get("/api/v1/tools", dependencies=[Depends(require_token)])
    async def list_tools_for_onboarding():
        """Every tool the tool server offers, whether Sentinel has classified it, and a SUGGESTION for the ones it has not.
        An unclassified tool is invisible to agents and refused by R1 until the officer classifies it."""
        out = []
        for t in await upstream_tools():
            known = rt.registry.is_known(t.name)
            out.append({"name": t.name, "description": t.description or "", "arguments": list(schema_of(t).get("properties", {})),
                        "classified": known, "builtin": rt.registry.is_builtin(t.name),
                        "labels": rt.registry.get(t.name).model_dump(mode="json", exclude={"name"}) if known else None,
                        "suggested": None if known else suggest_classification(t.name, t.description or "", schema_of(t))})
        return {"tools": out, "unclassified": sum(1 for x in out if not x["classified"])}

    @app.post("/api/v1/tools/{name}/classify", dependencies=[Depends(require_token)])
    async def classify_tool(name: str, body: ToolClassification):
        """The officer labels one tool. Built-in entries cannot be changed; the record is written to the audit log first."""
        tools = {t.name: t for t in await upstream_tools()}
        if name not in tools:
            raise HTTPException(status_code=404, detail=f"The tool server has no tool called '{name}'.")
        if rt.registry.is_builtin(name):
            raise HTTPException(status_code=409, detail=f"'{name}' is a built-in tool and cannot be reclassified.")
        bad = [f for f in body.fingerprint_fields if f != "all" and f not in FIELD_KINDS]
        if bad:
            raise HTTPException(status_code=422, detail=f"Unknown fingerprint field(s): {', '.join(bad)}. "
                                                        f"Use 'all' or any of: {', '.join(sorted(FIELD_KINDS))}.")
        args = set(schema_of(tools[name]).get("properties", {}))
        unknown = [a for a in body.destination_args if a not in args]
        if unknown:
            raise HTTPException(status_code=422, detail=f"'{name}' has no argument called {', '.join(unknown)}.")
        if body.outbound and not body.destination_args:
            raise HTTPException(status_code=422, detail="An outbound tool must say which argument names the destination, "
                                                        "otherwise Sentinel cannot check where it sends data.")
        entry = ToolEntry(name=name, resource_class=body.resource_class or name, **body.model_dump(exclude={"resource_class"}))
        try:
            await rt.audit.append("registry.classified", payload={"tool": name, "labels": entry.model_dump(mode="json", exclude={"name"})})
        except AuditError as e:
            raise HTTPException(status_code=503, detail="The audit log is unavailable, so the classification was not saved.") from e
        rt.registry.add(entry)
        if rt.registry_overlay is not None:
            save_overlay(rt.registry, rt.registry_overlay)
        await rt.bus.publish(make_event("registry.classified", None, None, {"tool": name}))
        return {"name": name, "classified": True, "labels": entry.model_dump(mode="json", exclude={"name"})}

    # ---- the slip builder: a permission slip for ANY task ---------------------------------------------------------
    @app.post("/api/v1/slips", status_code=201, dependencies=[Depends(require_token)])
    async def build_slip(req: SlipRequest):
        """The officer defines a slip from tools the registry knows. With `confirm: true` it is confirmed at once and a token
        for a client is returned; otherwise confirm it with POST /tasks/{contract_id}/confirm."""
        try:
            contract = draft_custom(rt.registry, objective=req.objective, allowed_tools=req.allowed_tools,
                                    allowed_destinations=req.allowed_destinations,
                                    internal_destinations=req.internal_destinations, max_messages=req.max_messages,
                                    ttl_seconds=req.ttl_seconds, officer=req.officer)
        except SlipError as e:
            raise HTTPException(status_code=422, detail=str(e)) from e
        rt.drafts[contract.contract_id] = contract
        slip = {"objective": contract.objective, "allowed_tools": contract.allowed_tools,
                "allowed_destinations": contract.allowed_recipient_domains,
                "internal_destinations": contract.internal_destinations, "max_messages": contract.max_messages,
                "ttl_seconds": req.ttl_seconds}
        out = {"contract_id": contract.contract_id, "contract_hash": contract.contract_hash, "slip": slip, "confirmed": False}
        if req.confirm:
            try:
                done = await confirm_draft(rt, contract.contract_id, Column.SENTINEL)
            except ConfirmError as e:
                raise HTTPException(status_code=e.status, detail=e.detail) from e
            out.update(confirmed=True, session_id=done["session_id"], header_value=f"Bearer {done['session_token']}",
                       expires_at=done["expires_at"])
        return out

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
    mount_site(app, site_dir)  # last: it answers every path nothing above matched
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


# Paths that belong to the API. An unknown one is a plain 404, never the website's page, so a mistyped API call is not
# answered with HTML.
API_PREFIXES = ("/api/", "/runs", "/approvals", "/audit", "/scenarios", "/recordings", "/sessions", "/tasks",
                "/killswitch", "/inbox", "/health", "/oauth", "/mcp", "/ws", "/console")


class SiteFiles(StaticFiles):
    """The built website, with the single-page-app fallback: a path that is not a file and not an API path (for example
    /docs or /how-it-works) gets index.html, and the page's own router takes over. A missing build is a 404 with an
    instruction, as for the console."""

    async def __call__(self, scope, receive, send):
        if scope["type"] == "websocket":
            await WebSocketClose()(scope, receive, send)
            return
        if not Path(str(self.directory)).is_dir():
            await PlainTextResponse("The website is not built yet. Run: npm --prefix site run build",
                                    status_code=404)(scope, receive, send)
            return
        await super().__call__(scope, receive, send)

    async def get_response(self, path: str, scope):
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as e:  # Starlette's own class: FastAPI's HTTPException is only a subclass of it
            url_path = scope.get("path", "/")
            is_asset = "." in url_path.rsplit("/", 1)[-1]
            if e.status_code != 404 or is_asset or url_path.startswith(API_PREFIXES):
                raise
            index = Path(str(self.directory)) / "index.html"
            if not index.is_file():
                raise
            return FileResponse(index)


def mount_site(app: FastAPI, directory: Path | None = None) -> None:
    """Serve the built website at /, so `python -m sentinel up` shows the site and the console from one address."""
    app.mount("/", SiteFiles(directory=directory or SITE_DIST, html=True, check_dir=False), name="site")
