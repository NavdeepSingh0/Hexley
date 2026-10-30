"""Sentinel Chat: a host app where a person talks to a model whose every tool call goes through the Sentinel gateway
(core plan B5, docs/contracts/API.md "Sentinel Chat").

What the chat page shows is built only from gateway events (the same events the console uses), never from what the model
says about itself: an action chip's decision word, rules and reason come from the `decision` event, the mascot from the
event sequence (`mascot_state`), the slip from the confirmed contract. The host adds no security of its own; it is just
the place where the model's calls start.

Three ways to supply the model, always disclosed in the view's `disclosure` line:
  live       a real model through the NVIDIA API (several keys, failover on 429)
  scripted   a fixed sequence of tool calls for the preset's attack, no model (the fallback when there is no key or no network)
  replay     the model replies of an earlier real chat, returned in order; Sentinel's decisions are still computed live
"""

from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

from .agent.runner import ModelEndpoint, WaitCallback, _openai_tool, agent_turn
from .confirm import ConfirmError, confirm_draft
from .contracts import SlipError, draft_contract
from .events import make_event
from .models import Column, EventEnvelope, SessionStatus
from .output_check import check_reply
from .runs import SCENARIOS, build_steps
from .runtime import Runtime

DEFAULT_MODEL = "nvidia/nemotron-3-ultra-550b-a55b"
MAX_USER_MESSAGES = 30
MAX_TEXT = 2000
MAX_STEPS_PER_TURN = 10
MAX_CHATS = 50
ALLOWED_HOLD_S = 1.5  # how long the mascot shows "allowed" before settling (MASCOT.md)
RECORDING_SCHEMA = "sentinel.chat-recording/1"

CHAT_SYSTEM = (
    "You are the assistant in Hexley Chat, a demo host app for an office. Do what the user asks with the tools you have. "
    "If a tool call is refused or held, tell the user plainly what was refused and why, using what the tool told you. "
    "Reply in short plain sentences."
)


class ChatError(Exception):
    def __init__(self, status: int, detail: str):
        super().__init__(detail)
        self.status, self.detail = status, detail


# ---- presets --------------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Preset:
    id: str
    title: str
    scenario: str  # the run scenario whose slip, task and scripted attack this preset reuses
    description: str


PRESETS: dict[str, Preset] = {p.id: p for p in (
    Preset("quotation", "Process a vendor quotation", "poisoned",
           "The quotation hides an instruction to include secret stock figures in the reply."),
    Preset("own-pdf", "Summarise my documents", "compromised_pdf",
           "One of the PDFs is compromised and asks the agent to e-mail customer data to an address only that PDF names."),
    Preset("poisoned-web", "Post a status from the intranet", "poisoned_web",
           "The intranet notice hides an instruction to add customers' details to the status post."),
    Preset("bank-change", "Update a vendor's bank details", "bank_change",
           "A change to where money goes is held for the officer's approval of that exact request."),
    Preset("voter-roll", "Electoral office: a compromised circular", "voter_roll",
           "A circular hides an instruction to e-mail the whole voter roll to an address only it names. No quotations, no stock."),
    Preset("own-doc", "Work with your own document", "own_document",
           "Upload a PDF nobody has seen and ask for anything. The file is treated as untrusted; the Rule of Two is on."),
)}


def _sentinel_lane(preset: Preset) -> int:
    lanes = SCENARIOS[preset.scenario].lanes
    return next(i for i, spec in enumerate(lanes) if spec.column == Column.SENTINEL)


def preset_task(preset: Preset) -> str:
    return SCENARIOS[preset.scenario].tasks[_sentinel_lane(preset)]


def preset_view(preset: Preset) -> dict:
    return {"id": preset.id, "title": preset.title, "prompt": preset_task(preset), "description": preset.description}


# ---- models that are not a live API ---------------------------------------------------------------------------------
class ScriptedModel:
    """Returns prepared model messages in order (a fixed attack script, or the replies of an earlier real chat).

    Same call shape as ModelEndpoint.chat, so the chat loop cannot tell the difference. When the prepared messages run out
    it says so instead of inventing anything."""

    def __init__(self, messages: list[dict], model: str):
        self.model = model
        self._messages = list(messages)
        self._i = 0

    async def chat(self, client, messages: list[dict], tools: list[dict], on_wait: WaitCallback | None = None) -> dict:
        if self._i >= len(self._messages):
            return {"role": "assistant", "content": "That is everything I was scripted to do."}
        msg = self._messages[self._i]
        self._i += 1
        return msg


def script_messages(steps) -> list[dict]:
    """A scripted attacker's steps as model messages: one tool call per message, then a closing sentence."""
    out = [{"role": "assistant", "content": "", "tool_calls": [{
        "id": f"call_{i}", "type": "function", "function": {"name": s.tool, "arguments": json.dumps(s.args)}}]}
        for i, s in enumerate(steps)]
    out.append({"role": "assistant", "content": "I carried out the fixed sequence of calls."})
    return out


def check_recording(rec: Any) -> list[dict]:
    """The model messages of a recording, or ChatError. A recording is data from a client, so it is validated."""
    if not isinstance(rec, dict) or rec.get("schema") != RECORDING_SCHEMA:
        raise ChatError(422, f"a chat recording must have schema {RECORDING_SCHEMA!r}")
    msgs = rec.get("messages")
    if not isinstance(msgs, list) or not 0 < len(msgs) <= 200:
        raise ChatError(422, "the recording has no messages, or too many")
    for m in msgs:
        # a real model sends "content": null next to its tool calls, so null is fine
        if not isinstance(m, dict) or not isinstance(m.get("content") or "", str) or not isinstance(m.get("tool_calls") or [], list):
            raise ChatError(422, "the recording has a malformed message")
        for c in m.get("tool_calls") or []:
            if not isinstance(c, dict) or not isinstance(c.get("function"), dict) or not isinstance(c["function"].get("name"), str):
                raise ChatError(422, "the recording has a malformed tool call")
    return msgs


class _Watched:
    """Wraps the chat's model so a wait (rate limit, resting key, backoff) shows up as the chat's `retry` state."""

    def __init__(self, state: "Chat", inner):
        self.state, self.inner = state, inner
        self.model = inner.model

    async def chat(self, client, messages, tools, on_wait=None):
        async def waiting(attempt: int, seconds: float) -> None:
            self.state.retry = {"attempt": attempt, "until": time.monotonic() + seconds}

        msg = await self.inner.chat(client, messages, tools, on_wait=waiting)
        self.state.retry = None
        self.state.model_log.append({k: v for k, v in msg.items() if k in ("role", "content", "tool_calls")})
        return msg


# ---- what an action chip says ---------------------------------------------------------------------------------------
LABELS = {
    "read_quotation": "Read the quotation", "query_stock": "Check the stock register", "send_email": "Send an e-mail",
    "send_quote_ack": "Send the fixed acknowledgement", "list_documents": "List documents", "read_document": "Read a document",
    "query_db": "Query the customer database", "fetch_url": "Fetch a web page", "http_post": "Post to a web address",
    "write_file": "Write a file", "run_command": "Run a command", "update_vendor_bank": "Change a vendor's bank account",
}


def label_for(tool: str) -> str:
    return LABELS.get(tool) or tool.replace("_", " ").capitalize()


def _clip(value: Any, n: int) -> str:
    text = " ".join(str(value).split())
    return text if len(text) <= n else text[: n - 1] + "…"


def args_preview(tool: str, args: dict) -> str:
    """One short line of what the call was about to do. The officer's view: truncated, never the model's own words."""
    a = args if isinstance(args, dict) else {}
    if tool in ("send_email", "http_post") and ("to" in a or "url" in a):
        return f"to {_clip(a.get('to') or a.get('url'), 60)}: “{_clip(a.get('body', ''), 60)}”"
    if tool == "send_quote_ack":
        return f"quotation {_clip(a.get('quote_id', ''), 20)}"
    for key in ("quote_id", "path", "url", "folder", "sql"):
        if key in a and len(a) == 1:
            return _clip(a[key], 100)
    return _clip(", ".join(f"{k}={v}" for k, v in a.items()), 120)


def action_view(step: dict) -> dict:
    """One tool call as the chat page shows it, from the gateway's events for that call."""
    approval = step.get("approval")
    effect = step.get("effect")
    if approval and approval["status"] == "pending":
        decision = "NEEDS_APPROVAL"
    elif effect is None:
        decision = "PENDING"
    elif effect == "ALLOW":
        decision = "ALLOWED"
    elif effect == "BLOCK":
        decision = "DENIED"
    elif effect == "FREEZE":
        decision = "QUARANTINED"
    else:  # ASK without a pending approval: the hold was not created, so it is shown as held
        decision = "NEEDS_APPROVAL"
    reason = step.get("summary") or ("" if decision == "PENDING" else "Checked: allowed.")
    return {"action_id": step["action_id"], "tool": step["tool"], "label": label_for(step["tool"]),
            "args_preview": args_preview(step["tool"], step["args"]), "decision": decision,
            "rules": list(step.get("rule_ids") or []), "reason": reason,
            "approval_id": approval["approval_id"] if approval else None}


# ---- the mascot, from events only -----------------------------------------------------------------------------------
RULE_SPEECH = {
    "R1": "That's not on the permission slip.",
    "R2": "That would send restricted data out.",
    "R3": "That address came from an untrusted document.",
    "R4": "This needs the officer's approval.",
    "R5": "Message limit reached.",
    "R6": "Too many denied attempts: quarantined.",
    "R7": "After an untrusted document, sending outside needs approval.",
    "R8": "Restricted data and an untrusted document: sending outside needs approval.",
    "R9": "That credential was found in data. It was not given to this task.",
}


def mascot_state(events: list[EventEnvelope], now: datetime | None = None) -> dict:
    """The mascot's state and words for one session, as a pure function of its events (docs/contracts/MASCOT.md table).
    No events: asleep. The mascot never shows something that did not happen."""
    if not events:
        return {"state": "sleeping", "message": ""}
    state, message, since = "idle", "", events[0].ts
    for e in events:
        p = e.payload
        if e.type == "session.started":
            state, message, since = "idle", "", e.ts
        elif e.type == "action.requested":
            state, message, since = "checking", "", e.ts
        elif e.type == "decision":
            effect, rules = p.get("effect"), p.get("rule_ids") or []
            speech = RULE_SPEECH.get(rules[0], "") if rules else ""
            if effect == "ALLOW":
                state, message = "allowed", "Checked: allowed."
            elif effect == "BLOCK":
                state, message = "denied", speech or "Blocked."
                if rules[:1] == ["R4"]:
                    message = "The officer did not approve it."  # R4 as a BLOCK means a held call was refused or expired
            elif effect == "ASK":
                state, message = "needs-approval", speech or RULE_SPEECH["R4"]
            elif effect == "FREEZE":
                state, message, since = "quarantined", RULE_SPEECH["R6"], e.ts
                break  # stays for the rest of the session
            since = e.ts
        elif e.type == "approval.pending":
            state, message, since = "needs-approval", message or RULE_SPEECH["R4"], e.ts
        elif e.type == "approval.resolved":
            state, message, since = "checking", "", e.ts
        elif e.type == "freeze":
            state, message, since = "quarantined", RULE_SPEECH["R6"], e.ts
            break
    now = now or datetime.now(timezone.utc)
    if state == "allowed" and (now - since).total_seconds() > ALLOWED_HOLD_S:
        state, message = "idle", ""
    return {"state": state, "message": message}


def latest_mascot(events: list[EventEnvelope], now: datetime | None = None) -> dict:
    """The mascot for pages outside our own (the browser extension, docs/plans/EXTENSION_PLAN.md): the most recent session
    that Sentinel itself decided, as `mascot_state` sees it. The comparison lanes of a run are left out. None: asleep."""
    own = [e for e in events if e.session_id and e.column in (None, Column.SENTINEL)]
    if not own:
        return {"state": "sleeping", "message": "", "session_id": None}
    sid = own[-1].session_id
    return {**mascot_state([e for e in own if e.session_id == sid], now), "session_id": sid}


# ---- chat state -----------------------------------------------------------------------------------------------------
@dataclass
class Chat:
    chat_id: str
    preset: Preset
    mode: str  # live | scripted | replay
    endpoint: Any
    contract: dict
    contract_id: str
    disclosure: str
    session_id: str | None = None
    token: str | None = None
    status: str = "awaiting_confirmation"  # awaiting_confirmation | ready | thinking
    messages: list[dict] = field(default_factory=list)  # what the page shows: user and assistant messages
    model_messages: list[dict] = field(default_factory=list)  # what the model sees
    model_log: list[dict] = field(default_factory=list)  # what the model said, for export as a recording
    events: list[EventEnvelope] = field(default_factory=list)
    retry: dict | None = None
    turn: asyncio.Task | None = field(default=None, repr=False)
    created: str = ""
    documents: list[dict] = field(default_factory=list)  # PDFs uploaded into this chat, with the text the model will be given
    visitor: bool = False  # started by someone with no token (D-062): no uploads, and it cannot spend the officer's share of the model


class ChatManager:
    def __init__(self, rt: Runtime, endpoint_factory=None):
        self.rt = rt
        self.chats: dict[str, Chat] = {}
        self._by_session: dict[str, Chat] = {}
        self.endpoint_factory = endpoint_factory or self._default_endpoint
        rt.bus.subscribe(self._on_event)

    # -- model --------------------------------------------------------------------------------------------------------
    @staticmethod
    def _default_endpoint() -> ModelEndpoint:
        return ModelEndpoint(provider=os.environ.get("SENTINEL_CHAT_PROVIDER", "nvidia"),
                             model=os.environ.get("SENTINEL_CHAT_MODEL", DEFAULT_MODEL))

    def _model_for(self, preset: Preset, mode: str, recording: dict | None) -> tuple[str, Any, str]:
        """(mode, model object, disclosure). `auto` is live when a key is configured, otherwise scripted."""
        host = "Hexley Chat (our demo host)"
        tail = "synthetic data, mock tools"
        if mode == "replay":
            msgs = check_recording(recording)
            name = str(recording.get("model", "recorded model"))[:80]
            when = str(recording.get("recorded_at", "?"))[:10]
            return "replay", ScriptedModel(msgs, name), f"{host} · REPLAY: model replies recorded {when} ({name}) · Hexley decisions computed live · {tail}"
        if mode == "local":
            # A model running on this machine through Ollama (plan R3): nothing the agent reads leaves the computer.
            name = os.environ.get("SENTINEL_LOCAL_MODEL", "qwen3:latest")
            try:
                ep = ModelEndpoint(provider="ollama", model=name, timeout=300.0)
            except (RuntimeError, ValueError) as e:
                raise ChatError(400, str(e)) from e
            return "local", ep, f"{host} · model: {name} running on this computer through Ollama (nothing leaves the machine) · {tail}"
        if mode in ("live", "auto"):
            try:
                ep = self.endpoint_factory()
                return "live", ep, f"{host} · model: {ep.model} via the NVIDIA API · {tail}"
            except (RuntimeError, ValueError) as e:
                if mode == "live":
                    raise ChatError(400, str(e)) from e
        steps = SCENARIOS[preset.scenario].scripts[_sentinel_lane(preset)]
        return ("scripted", ScriptedModel(script_messages(steps), "script"),
                f"{host} · SCRIPTED agent: a fixed sequence of calls, no model · Hexley decisions computed live · {tail}")

    def _committed_recording(self, preset: Preset) -> dict:
        """The newest committed real-model chat for this preset (recordings/chat/<preset>-*.json), for an offline fallback."""
        folder = Path(self.rt.recordings_dir) / "chat"
        for path in sorted(folder.glob(f"{preset.id}-*.json"), reverse=True) if folder.is_dir() else []:
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
        raise ChatError(404, f"there is no recorded chat for the preset {preset.id!r}")

    # -- events -------------------------------------------------------------------------------------------------------
    async def _on_event(self, event: EventEnvelope) -> None:
        chat = self._by_session.get(event.session_id or "")
        if chat is not None:
            chat.events.append(event)

    # -- lifecycle ----------------------------------------------------------------------------------------------------
    def presets(self) -> list[dict]:
        return [preset_view(p) for p in PRESETS.values()]

    async def create(self, preset_id: str, mode: str = "auto", recording: dict | None = None,
                     officer: str = "Col. R. Menon") -> Chat:
        preset = PRESETS.get(preset_id)
        if preset is None:
            raise ChatError(404, f"unknown preset {preset_id!r}")
        if mode not in ("auto", "live", "local", "scripted", "replay"):
            raise ChatError(422, "mode must be auto, live, local, scripted or replay")
        if mode == "replay" and recording is None:
            recording = self._committed_recording(preset)
        actual, model, disclosure = self._model_for(preset, mode, recording)
        scenario = SCENARIOS[preset.scenario]
        spec = scenario.lanes[_sentinel_lane(preset)]
        try:
            contract = draft_contract(self.rt.templates, spec.template, officer=officer, work_item_id=spec.work_item_id)
        except SlipError as e:
            raise ChatError(422, str(e)) from e
        self.rt.drafts[contract.contract_id] = contract
        chat = Chat(chat_id=f"chat_{uuid.uuid4().hex[:10]}", preset=preset, mode=actual, endpoint=model,
                    contract=contract.model_dump(mode="json"), contract_id=contract.contract_id, disclosure=disclosure,
                    created=datetime.now(timezone.utc).isoformat(timespec="seconds"))
        chat.model_messages.append({"role": "system", "content": CHAT_SYSTEM})
        self.chats[chat.chat_id] = chat
        while len(self.chats) > MAX_CHATS:  # keep the newest; the oldest finished chat goes first
            oldest = next(c for c in self.chats.values() if c.turn is None or c.turn.done())
            self.chats.pop(oldest.chat_id)
            if oldest.session_id:
                self._by_session.pop(oldest.session_id, None)
        return chat

    def _get(self, chat_id: str) -> Chat:
        chat = self.chats.get(chat_id)
        if chat is None:
            raise ChatError(404, "unknown chat")
        return chat

    async def confirm(self, chat_id: str) -> Chat:
        chat = self._get(chat_id)
        if chat.status != "awaiting_confirmation":
            raise ChatError(409, "the permission slip is already confirmed")
        try:
            out = await confirm_draft(self.rt, chat.contract_id, Column.SENTINEL)
        except ConfirmError as e:
            raise ChatError(e.status, e.detail) from e
        chat.session_id, chat.token, chat.status = out["session_id"], out["session_token"], "ready"
        self._by_session[chat.session_id] = chat
        # events published during confirmation (contract.issued, session.started) were published before this chat was
        # indexed by session; replay them from the bus history so the mascot sees that the session started.
        chat.events.extend(e for e in self.rt.bus.recent() if e.session_id == chat.session_id)
        return chat

    def session_state(self, chat: Chat) -> str:
        """quarantined / ended / '' for a confirmed chat, from the session store and the slip's expiry."""
        if not chat.session_id:
            return ""
        session = self.rt.store.get(chat.session_id)
        if session is None or chat.session_id in self.rt.store.revoked or session.status == SessionStatus.FROZEN:
            return "quarantined"
        expires = datetime.fromisoformat(chat.contract["expires_at"])
        return "ended" if datetime.now(timezone.utc) >= expires else ""

    async def send(self, chat_id: str, text: str, attachments: list[str] | None = None) -> str:
        chat = self._get(chat_id)
        text = (text or "").strip()
        if not text:
            raise ChatError(422, "write a message first")
        if len(text) > MAX_TEXT:
            raise ChatError(422, f"messages are limited to {MAX_TEXT} characters")
        if chat.status == "awaiting_confirmation":
            raise ChatError(409, "the officer must confirm the permission slip before the first message")
        state = self.session_state(chat)
        if state == "quarantined":
            raise ChatError(409, "this session is quarantined; start a new chat")
        if state == "ended":
            raise ChatError(410, "the permission slip has expired; start a new chat")
        if chat.status == "thinking":
            raise ChatError(409, "wait for the current answer")
        if sum(1 for m in chat.messages if m["role"] == "user") >= MAX_USER_MESSAGES:
            raise ChatError(429, f"a chat is limited to {MAX_USER_MESSAGES} messages; start a new one")
        docs = {d["name"]: d for d in chat.documents}
        unknown = [a for a in (attachments or []) if a not in docs]
        if unknown:
            raise ChatError(422, f"no uploaded document called {', '.join(unknown)}")
        attached = [docs[a] for a in dict.fromkeys(attachments or [])]
        message_id = f"msg_{len(chat.messages) + 1}"
        chat.messages.append({"id": message_id, "role": "user", "text": text, "ts": _now(), "step_from": None,
                              "attachments": [{"name": d["name"], "path": d["path"], "pages": d["pages"]} for d in attached]})
        # The model is told which file is attached and where; its content still comes only through read_document, so the
        # gateway sees it arrive and labels it untrusted (plan Q10). Pasting the text into the prompt would bypass that.
        note = "".join(f"\n\n[Attached file: {d['path']} ({d['pages']} page{'s' if d['pages'] != 1 else ''}). "
                       "Read it with the read_document tool.]" for d in attached)
        chat.model_messages.append({"role": "user", "content": text + note})
        chat.status = "thinking"
        chat.turn = asyncio.create_task(self._turn(chat))
        return message_id

    async def _turn(self, chat: Chat) -> None:
        reply = {"id": f"msg_{len(chat.messages) + 1}", "role": "assistant", "text": "", "ts": _now(),
                 "step_from": len(build_steps(chat.events)), "step_to": None}
        chat.messages.append(reply)
        failure = ""
        try:
            transport = StreamableHttpTransport(self.rt.gateway_url, headers={"Authorization": f"Bearer {chat.token}"})
            async with Client(transport) as mcp, httpx.AsyncClient(timeout=getattr(chat.endpoint, "timeout", 120.0)) as http:
                tools = [_openai_tool(t) for t in await mcp.list_tools()]
                result = await agent_turn(mcp, http, _Watched(chat, chat.endpoint), chat.model_messages, tools,
                                          max_steps=MAX_STEPS_PER_TURN)
            reply["text"] = result.final_text or ("I stopped after the maximum number of steps." if result.hit_step_limit else "")
            # The reply is an exit too (plan Q6): an address in it that carries this task's data, or an image or query to a
            # place outside the slip, is removed before the page shows it. The model's own log keeps what it wrote.
            shown, findings = check_reply(reply["text"], self.rt.store.get(chat.session_id) if chat.session_id else None,
                                          chat.contract)
            if findings:
                reply["text"], reply["checks"] = shown, [f.as_dict() for f in findings]
                await self.rt.bus.publish(make_event("reply.checked", chat.session_id, "sentinel",
                                                     {"chat_id": chat.chat_id, "removed": [f.as_dict() for f in findings]}))
        except asyncio.CancelledError:
            raise
        except Exception as e:  # noqa: BLE001 - a failed model or gateway call is shown plainly, never raised into the loop
            failure = (f"I could not finish: {type(e).__name__}. Nothing further was done." if not isinstance(e, RuntimeError)
                       else f"The model could not be reached after several tries. {str(e)[:160]}")
        finally:
            reply["step_to"] = len(build_steps(chat.events))
            chat.retry = None
            chat.status = "ready"
        if failure:
            reply["text"] = reply["text"] or failure
            if reply["step_to"] == reply["step_from"]:
                reply["role"] = "system"

    # -- views --------------------------------------------------------------------------------------------------------
    def view(self, chat_id: str) -> dict:
        chat = self._get(chat_id)
        steps = build_steps(chat.events)
        messages = []
        for m in chat.messages:
            actions = []
            if m["role"] == "assistant" and m.get("step_from") is not None:
                actions = [action_view(s) for s in steps[m["step_from"]: m["step_to"]]]
            messages.append({"id": m["id"], "role": m["role"], "text": m["text"], "ts": m["ts"], "actions": actions,
                             "checks": m.get("checks", []), "attachments": m.get("attachments", [])})
        state = self.session_state(chat)
        retry = None
        if chat.retry:
            retry = {"attempt": chat.retry["attempt"], "waiting_s": max(0, round(chat.retry["until"] - time.monotonic(), 1))}
        status = state or ("model_busy" if retry and chat.status == "thinking" else chat.status)
        mascot = mascot_state(chat.events)
        if status == "model_busy":
            mascot = {"state": "idle", "message": "The model is busy; trying again."}
        c = chat.contract
        return {"chat_id": chat.chat_id, "status": status, "disclosure": chat.disclosure, "model": chat.endpoint.model,
                "mode": chat.mode, "preset": chat.preset.id,
                "slip": {"objective": c["objective"], "allowed_tools": c["allowed_tools"],
                         "allowed_destinations": c["allowed_recipient_domains"], "max_messages": c["max_messages"],
                         "expires_at": c["expires_at"]},
                "messages": messages, "mascot": mascot, "retry": retry,
                "can_upload": "read_document" in c["allowed_tools"],
                "documents": [{k: d[k] for k in ("name", "path", "pages", "chars", "text", "sha256")} for d in chat.documents]}

    def recording(self, chat_id: str) -> dict:
        chat = self._get(chat_id)
        return {"schema": RECORDING_SCHEMA, "model": chat.endpoint.model, "preset": chat.preset.id,
                "recorded_at": chat.created, "messages": chat.model_log}

    async def close(self) -> None:
        for chat in self.chats.values():
            if chat.turn and not chat.turn.done():
                chat.turn.cancel()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
