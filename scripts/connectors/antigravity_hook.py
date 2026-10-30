"""Antigravity's PreToolUse hook: ask Hexley before a GitHub connector tool runs (plan F2, D-059).

Antigravity runs this as a command, sends the call as JSON on stdin and reads {"decision": ...} from stdout. Anything that goes wrong is
a deny, because a check that fails open is no check. Standard library only, so it needs nothing installed. It keeps a log of tool names,
never of arguments or tokens, because Antigravity's documentation does not say how MCP tools are named or whether this hook sees them
at all: that log is how we find out.

Limits, from Antigravity's documentation as read on 31 Oct 2026: its hook list names only built-in tools, and its after-tool hook is not
documented as carrying the result, so Hexley cannot learn from what a tool returned. The slip therefore sets `unseen_context`.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HOME = Path(os.environ.get("HEXLEY_HOOK_HOME") or Path.home() / ".hexley")
API = os.environ.get("HEXLEY_API", "https://hexley.site")
GITHUB = re.compile(r"github[_./:\-]+(.+)$", re.IGNORECASE)


def log(line: str) -> None:
    try:
        HOME.mkdir(parents=True, exist_ok=True)
        with (HOME / "antigravity_hook.log").open("a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%H:%M:%S')} {line}\n")
    except OSError:
        pass


def answer(decision: str, reason: str = "") -> None:
    print(json.dumps({"decision": decision, **({"reason": reason} if reason else {})}))


def main() -> None:
    # Bytes, because on Windows stdin is not UTF-8 by default, and a byte-order mark must not turn every call into a deny.
    call = json.loads(sys.stdin.buffer.read().decode("utf-8-sig") or "{}").get("toolCall") or {}
    name = str(call.get("name", ""))
    found = GITHUB.search(name)
    if not found:
        log(f"not judged: {name}")
        answer("allow")  # this hook covers the GitHub connector only; the coverage is stated, not implied
        return
    token = (HOME / "antigravity_token").read_text(encoding="utf-8").strip()
    body = json.dumps({"tool_name": f"mcp__github__{found.group(1)}", "tool_input": call.get("args") or {}, "wait_s": 10}).encode("utf-8")
    request = urllib.request.Request(f"{API}/api/v1/check/call", data=body, method="POST",
                                     headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=25) as response:
        reply = json.load(response)
    effect = reply.get("effect")
    log(f"judged: {name} -> {reply.get('tool')} {effect}")
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
