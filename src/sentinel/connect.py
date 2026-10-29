"""What the site's Connect page shows, and the header-token route (docs/contracts/API.md).

Statuses are what we have actually run, nothing else: a client is `tested` only after a real session through it was
checked (docs/PHASE_LOG.md); `should_work` means it follows the MCP standard but we have not run it. Update this list
only with evidence."""

from __future__ import annotations

from .confirm import confirm_draft
from .contracts import SlipError, draft_contract
from .models import Column
from .runtime import Runtime

# (id, name, kind, status, method, snippet, screenshot, transcript)
# `screenshot` is an image of a real session; `transcript` is {"url", "caption"} for a captured text record. Only a tested
# client may carry either (docs/PHASE_LOG.md, F8).
CLIENTS = [
    ("claude-web", "Claude.ai (web)", "web", "tested", "oauth", None, "/img/real-claude-blocked-by-sentinel.png", None),
    ("claude-code", "Claude Code", "cli", "tested", "header",
     'claude mcp add --transport http sentinel {mcp_url} --header "Authorization: {header_value}"', None,
     {"url": "/proof/claude-code-header-20261029.txt",
      "caption": "A real Claude Code session, 29 Oct 2026, header token: the read and stock checks were allowed, the e-mail with restricted stock figures was denied (R2), nothing was delivered. One session, not a measurement."}),
    ("vscode", "VS Code (MCP)", "ide", "should_work", "header",
     '{ "servers": { "sentinel": { "type": "http", "url": "{mcp_url}", "headers": { "Authorization": "{header_value}" } } } }',
     None, None),
    # Gemini CLI: connected to the gateway with this exact settings block and listed Sentinel's tools (29 Oct 2026); no session was
    # run because its own Google sign-in had expired. Codex CLI: connected state not shown, its model needed a newer CLI. Both
    # therefore stay "should work" until a session is run.
    ("gemini-cli", "Gemini CLI", "cli", "should_work", "header",
     '{ "mcpServers": { "sentinel": { "httpUrl": "{mcp_url}", "headers": { "Authorization": "{header_value}" } } } }', None, None),
    ("codex-cli", "Codex CLI", "cli", "should_work", "header",
     '[mcp_servers.sentinel]\nurl = "{mcp_url}"\nhttp_headers = { Authorization = "{header_value}" }', None, None),
    ("local-chat", "A local model (Ollama) in Sentinel Chat", "local", "tested", "header", None, None,
     {"url": "/proof/local-ollama-20261029.txt",
      "caption": "A real model on this computer (qwen3 through Ollama) used through the real gateway in Sentinel Chat, 29 Oct 2026: nothing the agent read left the machine. Our own host, not a third-party client."}),
    ("local", "A local model through a third-party MCP client", "local", "planned", "header", None, None, None),
    ("other-agents", "Agents that do not use MCP", "other", "planned", "none", None, None, None),
]

# What we have verified for each way of connecting (update when a live check passes).
# oauth: verified 27 Oct 2026 with a real Claude.ai free account (Sign in now + automatic registration): the slip was
# approved with the officer code, a send containing restricted data was denied (R2), nothing was delivered.
# header: the token route was tested with a real client on 29 Oct 2026 (Claude Code: the exact `claude mcp add` command from
# this list reported Connected, and a real session was decided by the gateway; site/public/proof/). It was "should_work"
# until then (corrected 28 Oct 2026, D-041; moved to tested in F8, D-044).
METHOD_STATUS = {"oauth": "tested", "header": "tested"}

OAUTH_STEPS = ["Open Customize → Connectors → Add custom connector", "Paste the connector URL",
               "Choose “Sign in now”", "Approve the permission slip with the officer code shown in the Sentinel terminal"]
HEADER_STEPS = ["Create a slip and token below", "Add a request header named Authorization with the value shown",
                "The token stops working when its time runs out; create a new one"]


def connect_view(rt: Runtime) -> dict:
    oauth = rt.oauth
    public_url = str(oauth.base_url).rstrip("/") if oauth is not None else None
    mcp_url = f"{public_url}/mcp" if public_url else rt.gateway_url
    methods = [{"id": "header", "status": METHOD_STATUS["header"], "steps": HEADER_STEPS}]
    if oauth is not None:
        methods.insert(0, {"id": "oauth", "status": METHOD_STATUS["oauth"], "steps": OAUTH_STEPS})
    return {"public_url": public_url, "mcp_url": mcp_url, "methods": methods,
            "clients": [{"id": i, "name": n, "kind": k, "status": s, "method": m, "snippet": sn,
                         "screenshot": sc if s == "tested" else None,
                         "transcript": tr if s == "tested" else None} for i, n, k, s, m, sn, sc, tr in CLIENTS]}


async def issue_header_token(rt: Runtime, preset: str, work_item_id: str | None = "Q-1043", officer: str = "Col. R. Menon") -> dict:
    """The officer confirms a slip and receives a bearer token to paste into a client. Raises SlipError / ConfirmError."""
    if preset not in rt.templates:
        raise SlipError(f"unknown slip preset {preset!r}")
    needs_item = bool(rt.templates[preset].get("requires_work_item")) or preset == "quotation_processing"
    contract = draft_contract(rt.templates, preset, officer=officer, work_item_id=work_item_id if needs_item else None)
    rt.drafts[contract.contract_id] = contract
    out = await confirm_draft(rt, contract.contract_id, Column.SENTINEL)
    return {"header_value": f"Bearer {out['session_token']}", "expires_at": out["expires_at"],
            "slip": {"objective": contract.objective, "allowed_tools": contract.allowed_tools,
                     "allowed_destinations": contract.allowed_recipient_domains, "max_messages": contract.max_messages}}
