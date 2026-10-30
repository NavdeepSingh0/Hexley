"""Antigravity's PreToolUse hook: ask Hexley before any MCP tool runs (plan F2, D-059).

Antigravity runs this as a command, sends the call as JSON on stdin and reads {"decision": ...} from stdout. Anything that goes wrong is
a deny, because a check that fails open is no check. Standard library only, so it needs nothing installed. It keeps a log of tool names,
never of arguments or tokens. Antigravity's documentation does not say how MCP tools reach this hook: it was read from the log of a real run,
where every MCP call arrives as the built-in tool `call_mcp_tool`.

Limits, from Antigravity's documentation as read on 31 Oct 2026: its hook list names only built-in tools, and its after-tool hook is not
documented as carrying the result, so Hexley cannot learn from what a tool returned. The slip therefore sets `unseen_context`.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HOME = Path(os.environ.get("HEXLEY_HOOK_HOME") or Path.home() / ".hexley")
API = os.environ.get("HEXLEY_API", "https://hexley.site")
MCP_CALL = "call_mcp_tool"  # Antigravity sends every MCP call through this one built-in tool (seen in its hook, 31 Oct; not documented)


def log(line: str) -> None:
    try:
        HOME.mkdir(parents=True, exist_ok=True)
        with (HOME / "antigravity_hook.log").open("a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%H:%M:%S')} {line}\n")
    except OSError:
        pass


def answer(decision: str, reason: str = "") -> None:
    print(json.dumps({"decision": decision, **({"reason": reason} if reason else {})}))


def mcp_call(args: dict) -> tuple[str, dict]:
    """The name Hexley uses for this call, and its arguments. Exactly the shape seen in real Antigravity on 31 Oct: with aliases, two
    fields could name different tools and the check could read the wrong one. Anything else raises ValueError, which is a deny."""
    if set(args) != {"Arguments", "ServerName", "ToolName"}:
        raise ValueError("unreadable MCP call")
    server, tool, inner = args["ServerName"], args["ToolName"], args["Arguments"]
    if isinstance(inner, str):
        inner = json.loads(inner)
    if not (isinstance(server, str) and isinstance(tool, str) and server and tool and isinstance(inner, dict)):
        raise ValueError("unreadable MCP call")
    server = "github" if server == "github-mcp-server" else server  # the name Antigravity reports for GitHub's server
    return f"mcp__{server}__{tool}", inner


def main() -> None:
    # Bytes, because on Windows stdin is not UTF-8 by default, and a byte-order mark must not turn every call into a deny.
    call = json.loads(sys.stdin.buffer.read().decode("utf-8-sig") or "{}").get("toolCall") or {}
    name = str(call.get("name", ""))
    args = call.get("args") or {}
    if name != MCP_CALL:
        log(f"not judged: {name}")
        answer("allow")  # this hook covers MCP tools; a built-in tool such as the terminal is outside it, and that is stated, not implied
        return
    log(f"mcp call, argument names: {sorted(args)}")  # names only, never values
    tool, tool_input = mcp_call(args)
    token = (HOME / "antigravity_token").read_text(encoding="utf-8").strip()
    body = json.dumps({"tool_name": tool, "tool_input": tool_input, "wait_s": 10}).encode("utf-8")
    request = urllib.request.Request(f"{API}/api/v1/check/call", data=body, method="POST",
                                     headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=25) as response:
        reply = json.load(response)
    effect = reply.get("effect")
    log(f"judged: {tool} -> {reply.get('tool')} {effect}")
    if effect == "ALLOW":
        answer("allow")
    else:
        answer("deny", str(reply.get("reason") or "Hexley did not allow this call."))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, urllib.error.URLError) as e:
        log(f"failed closed: {type(e).__name__}")
        answer("deny", "Hexley could not be reached or could not decide, so this call did not run.")
