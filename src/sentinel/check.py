"""Calls a client reports instead of sending through the gateway (plan F1; docs/plans/PRODUCT_ROADMAP.md, W1.4).

An MCP gateway decides only what goes through it. A client that has other connectors, or tools of its own, can still reach them.
Many clients can run a check before every tool call and report the result after (Claude Code's PreToolUse and PostToolUse
hooks). This module is what those reports talk to. It adds no rule: it names the tool the way the registry does, hands the call
to the gateway's own `mediate`, and turns the decision into a reply the client can act on. So a call reported by a hook and the
same call sent through the gateway are decided by the same code, recorded in the same audit log, and counted against the same
slip.

What this route cannot do, stated once: the client decides whether to call it. A hook that the client's own settings can remove,
or a tool the hook's matcher does not name, is not mediated. `coverage` says which tools Sentinel saw, never which it did not.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from fastmcp.exceptions import ToolError

from .contracts import Session, SessionError, verify_session_token
from .gateway import SentinelMiddleware
from .models import Effect
from .runtime import Runtime

log = logging.getLogger("sentinel.check")

# Built-in tools of a coding client that are the same thing as another built-in tool: they are decided under one name.
ALIASES = {"MultiEdit": "Edit", "NotebookEdit": "Edit", "PowerShell": "Bash"}


class CheckError(Exception):
    """The caller could not be authenticated or the report is unusable. `status` is the HTTP status to answer with."""

    def __init__(self, status: int, detail: str):
        super().__init__(detail)
        self.status, self.detail = status, detail


def session_from_authorization(rt: Runtime, authorization: str) -> Session:
    """The session behind a bearer token: the same token an MCP client sends to the gateway. A token for a frozen, expired
    or unknown session is refused, as at the gateway."""
    token = authorization.removeprefix("Bearer ").strip() if authorization.startswith("Bearer ") else ""
    if not token:
        raise CheckError(401, "missing session token")
    try:
        claims = verify_session_token(token, rt.key.public_key(), revoked=rt.store.revoked)
    except SessionError as e:
        raise CheckError(401, f"this session is not valid ({e})") from e
    session = rt.store.get(claims.session_id)
    if session is None or not rt.store.is_usable(claims.session_id):
        raise CheckError(403, "this session is frozen or unknown")
    return session


def canonical_tool(raw: str) -> tuple[str, str, str | None]:
    """(name the registry uses, kind, server). An MCP tool `mcp__github__issue_write` is `github.issue_write`. The name is cut
    at the first `__` after the prefix. The dot is deliberate: joined with an underscore, a server called `send` offering a tool
    called `email` would be named `send_email` and inherit the labels of ours. There is no fallback to the bare tool name for
    the same reason. An unreadable name stays as it is, which the registry does not know, so it is refused (R1)."""
    if raw.startswith("mcp__"):
        server, sep, tool = raw[len("mcp__"):].partition("__")
        if not sep or not server or not tool:
            return raw, "mcp", None
        return f"{server}.{tool}", "mcp", server
    return ALIASES.get(raw, raw), "builtin", None


def response_text(response: Any) -> str:
    """The text of a tool's result as a client reports it: a string, or MCP content blocks, or any JSON."""
    if response is None:
        return ""
    if isinstance(response, str):
        return response
    if isinstance(response, dict) and isinstance(response.get("content"), list):
        parts = [b.get("text", "") for b in response["content"] if isinstance(b, dict) and isinstance(b.get("text"), str)]
        rest = {k: v for k, v in response.items() if k != "content"}
        if rest:
            parts.append(json.dumps(rest, default=str))
        return "\n".join(p for p in parts if p)
    if isinstance(response, list) and all(isinstance(b, dict) for b in response):
        parts = [b.get("text", "") if isinstance(b.get("text"), str) else json.dumps(b, default=str) for b in response]
        return "\n".join(p for p in parts if p)
    return json.dumps(response, default=str)


def _reply(effect: str, reason: str, *, tool: str, mediated: bool = True, **extra: Any) -> dict:
    return {"effect": effect, "mediated": mediated, "tool": tool, "reason": reason, **extra}


async def check_call(rt: Runtime, session: Session, raw_tool: str, tool_input: Any, tool_use_id: str | None = None,
                     wait: float = 20.0, skip_servers: frozenset[str] = frozenset()) -> dict:
    """Decide one call the client is about to make. The reply is what the agent may be told: never which rule fired or what
    matched (the gateway withholds the same detail). `effect` is ALLOW, BLOCK, ASK (held for the officer, not yet answered) or
    FREEZE. Fail-closed: anything unexpected is a BLOCK."""
    tool, kind, server = canonical_tool(raw_tool)
    args = tool_input if isinstance(tool_input, dict) else {}
    if raw_tool == "PowerShell" and isinstance(args.get("command"), str):
        # In a Bash command an unquoted backslash is an escape; in PowerShell it is a path separator. Read it as the path it is,
        # for the decision only: the client runs its own command unchanged.
        args = {**args, "command": args["command"].replace("\\", "/")}
    if (server is not None and server in skip_servers) or (kind == "builtin" and not rt.registry.is_known(tool)):
        # Goes through the gateway itself (a server named in `skip`), or a built-in tool Sentinel does not decide on (Read,
        # Glob, Grep...). Recorded, so the coverage report shows it was seen and not mediated.
        session.note_tool(tool, "hook", mediated=False)
        why = "this tool goes through Sentinel's own gateway" if server is not None else "Sentinel does not decide on this built-in tool"
        return _reply("ALLOW", why, tool=tool, mediated=False)
    try:
        decision, action, entry = await SentinelMiddleware(rt).mediate(session, tool, args, wait=wait, route="hook")
    except ToolError as e:  # a frozen or revoked session
        return _reply("BLOCK", str(e), tool=tool)
    except Exception:  # noqa: BLE001 - invariant 2: anything unexpected in the decision path is a BLOCK
        log.exception("hook check failed; failing closed")
        return _reply("BLOCK", "Blocked: Sentinel could not evaluate this action safely, so it should not run.", tool=tool)
    base = dict(action_id=action.action_id, decision_id=decision.decision_id, rule_ids=[str(r) for r in decision.rule_ids])
    if decision.effect == Effect.ALLOW:
        if tool_use_id:
            session.hook_calls[tool_use_id] = (action.action_id, tool, decision)
        return _reply("ALLOW", decision.summary_plain, tool=tool, **base)
    reason = decision.agent_summary or decision.summary_plain
    if decision.effect == Effect.ASK:
        pending = next((a for a in rt.approvals.pending() if a.session_id == session.session_id and a.tool == tool
                        and a.action_hash == rt.approvals.hash_for(session.session_id, tool, args)), None)
        return _reply("ASK", f"{reason} The officer can approve this exact request in Sentinel; then try it again.", tool=tool,
                      approval_id=pending.approval_id if pending else None, **base)
    return _reply(str(decision.effect), reason, tool=tool, **base)


async def report_result(rt: Runtime, session: Session, raw_tool: str, tool_use_id: str | None, tool_response: Any) -> dict:
    """What a tool the hook allowed returned. Sentinel learns from it as it does from a gateway result: a credential in it is
    remembered, restricted values are indexed, untrusted content taints the session. A report with no matching earlier check
    (a tool Sentinel does not mediate) is ignored, never guessed at."""
    tool, _, _ = canonical_tool(raw_tool)
    found = session.hook_calls.pop(tool_use_id, None) if tool_use_id else None
    if found is None or found[1] != tool:
        return {"recorded": False, "reason": "no matching check for this call"}
    action_id, _, decision = found
    entry = rt.registry.get(tool)
    try:
        await SentinelMiddleware(rt).note_result(session, entry, tool, action_id, decision, response_text(tool_response))
    except ToolError as e:
        return {"recorded": False, "reason": str(e)}
    return {"recorded": True}


def coverage_view(rt: Runtime, session: Session) -> dict:
    tools = [{"tool": t, "routes": c["routes"], "mediated": c["mediated"], "calls": c["calls"]}
             for t, c in sorted(session.coverage.items())]
    return {"session_id": session.session_id, "tools": tools,
            "mediated": [t["tool"] for t in tools if t["mediated"]],
            "seen_not_mediated": [t["tool"] for t in tools if not t["mediated"]],
            # tools Sentinel saw and refused because nobody has classified them: the officer's to-do list
            "unclassified": [t["tool"] for t in tools if t["mediated"] and not rt.registry.is_known(t["tool"])],
            "unseen_context": session.contract.unseen_context,
            "note": "Only calls that reached Sentinel are listed. A tool the client never reported is not here, and Sentinel "
                    "cannot know it exists. To see more, make the client's hook match every tool."}



# What Claude Code's hook should cover. The MCP connectors are the point; Bash, Write, Edit and WebFetch are the built-in tools
# Sentinel can read the effect of (a protected path, a destructive command, a web address outside the slip).
HOOK_MATCHER = "mcp__.*|Bash|PowerShell|Write|Edit|WebFetch"


def claude_code_settings(api_url: str, *, env_var: str = "SENTINEL_TOKEN", skip: tuple[str, ...] = (), wait: float = 15.0,
                         matcher: str = HOOK_MATCHER) -> dict:
    """The `hooks` block for Claude Code's settings.json (code.claude.com/docs/en/hooks): both events go to Sentinel over HTTP, the
    session token is read from an environment variable and never written to the file, and `onFailure: block` means a Sentinel
    that is down or too slow stops the call (needs Claude Code 2.1.295 or newer; before that a failed hook lets the call run).
    `skip` names MCP servers that already go through Sentinel's gateway, so their calls are not decided twice."""
    if not re.fullmatch(r"https?://[A-Za-z0-9.\-]+(?::\d+)?(?:/[A-Za-z0-9._~/\-]*)?", api_url or ""):
        raise ValueError("the API address must look like http://127.0.0.1:8000")
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", env_var):
        raise ValueError("the environment variable name may use letters, digits and underscores only")
    if not all(re.fullmatch(r"[A-Za-z0-9_\-]+", s) for s in skip):
        raise ValueError("a server name to skip may use letters, digits, hyphens and underscores only")
    if not 1 <= wait <= 55:
        raise ValueError("the wait for the officer must be between 1 and 55 seconds")
    url = f"{api_url.rstrip('/')}/api/v1/hooks/claude-code?wait={wait:g}" + (f"&skip={','.join(skip)}" if skip else "")
    hook = {"type": "http", "url": url, "timeout": 60, "onFailure": "block",
            "headers": {"Authorization": f"Bearer ${env_var}"}, "allowedEnvVars": [env_var]}
    group = [{"matcher": matcher, "hooks": [hook]}]
    return {"hooks": {"PreToolUse": group, "PostToolUse": group}}
