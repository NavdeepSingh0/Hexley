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
    # The snippet is what the person asks Claude once connected: the person need not know the tool names, and Claude does (F3c).
    ("claude-web", "Claude.ai with its own connectors (asks first, not enforced)", "web", "tested", "oauth",
     "Run the Hexley tool hexley_setup, listing every connector tool you have in this chat, except Hexley's own, as Connector:tool_name. "
     "Then send me its reply field exactly as written.",
     "/img/real-claude-blocked-by-sentinel.png",
     {"url": "/proof/claude-ai-connectors-20261031.txt",
      "caption": "Claude.ai on 31 Oct 2026, one account, one run per test: a send to an outsider asked first, was refused and did not go; an honest send asked first and went. Advisory: nothing forces the model to ask. The image is an older run, from before the rename, of a send refused for restricted data."}),
    ("claude-code", "Claude Code", "cli", "tested", "header",
     'claude mcp add --transport http sentinel {mcp_url} --header "Authorization: {header_value}"', None,
     {"url": "/proof/claude-code-header-20261029.txt",
      "caption": "A real Claude Code session, 29 Oct 2026, header token: the read and stock checks were allowed, the e-mail with restricted stock figures was denied (R2), nothing was delivered. One session, not a measurement."}),
    # The enforcing route (plan F1): Claude Code's own hook sends every tool call to Sentinel, whichever server it belongs to.
    ("claude-code-hook", "Claude Code with the Hexley hook (other connectors included)", "cli", "tested", "header",
     'python -m sentinel hook-config --api-url {api_url} --skip sentinel > .claude/settings.local.json\n'
     '# then set SENTINEL_TOKEN to the token created above, without the word Bearer',
     None,
     {"url": "/proof/claude-code-connectors-20261031.txt",
      "caption": "Claude Code with Claude's real Gmail, Slack and Notion connectors on test accounts, 31 Oct 2026: honest actions went through and sends off the slip were blocked before reaching the connector. The AI was told to carry out the planted steps, as a stand-in for a fooled model. One run per condition, not a measurement."}),
    # The token is for a slip naming the GitHub tools and repositories, which the officer creates through the API (docs: Connect Antigravity).
    ("antigravity", "Antigravity with GitHub, through its own hook", "ide", "tested", "hook",
     '{ "hexley": { "PreToolUse": [ { "matcher": "*", "hooks": [ { "command": "python /path/to/antigravity_hook.py", "timeout": 30 } ] } ] } }',
     None,
     {"url": "/proof/antigravity-github-20261031.txt",
      "caption": "Real Antigravity and GitHub's own MCP server on test repositories, 31 Oct 2026: an honest comment went through; a poisoned issue's comment on the private repository was blocked, twice. The AI was told to carry the steps out, as a stand-in for a fooled model. Its terminal is not judged."}),
    ("claude-code-vscode", "Claude Code in VS Code, with the Hexley hook", "ide", "tested", "header",
     'python -m sentinel hook-config --api-url {api_url} --skip sentinel > .claude/settings.local.json\n'
     '# then set SENTINEL_TOKEN to the token created above, without the word Bearer, and open this folder in VS Code',
     None,
     {"url": "/proof/claude-code-vscode-20261031.txt",
      "caption": "The real VS Code window with Claude's real Gmail connector on a test account, 31 Oct 2026, one run per test: an honest send went, a send off the slip was blocked (R1). Claude read a poisoned mail and attempted no send, so Hexley stopped nothing there; the same send, asked directly at the decision endpoint, was blocked (R1, R2, R3)."}),
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
    ("local-chat", "A local model (Ollama) in Hexley Chat", "local", "tested", "header", None, None,
     {"url": "/proof/local-ollama-20261029.txt",
      "caption": "A real model on this computer (qwen3 through Ollama) used through the real gateway in Hexley Chat, 29 Oct 2026: nothing the agent read left the machine. Our own host, not a third-party client."}),
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
               "Choose “Sign in now”", "Approve the permission slip with the officer code shown in the Hexley terminal"]
HEADER_STEPS = ["Create a slip and token below", "Add a request header named Authorization with the value shown",
                "The token stops working when its time runs out; create a new one"]


def connect_view(rt: Runtime) -> dict:
    oauth = rt.oauth
    public_url = str(oauth.base_url).rstrip("/") if oauth is not None else None
    mcp_url = f"{public_url}/mcp" if public_url else rt.gateway_url
    methods = [{"id": "header", "status": METHOD_STATUS["header"], "steps": HEADER_STEPS}]
    if oauth is not None:
        steps = OAUTH_STEPS if getattr(oauth, "google", None) is None else [*OAUTH_STEPS[:-1], "Continue with Google, then Allow"]
        methods.insert(0, {"id": "oauth", "status": METHOD_STATUS["oauth"], "steps": steps})
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
