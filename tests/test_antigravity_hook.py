"""The Antigravity hook as a program: real stdin and stdout, against a stand-in for Hexley's decision endpoint (plan F2, D-059)."""

from __future__ import annotations

import json
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

HOOK = Path(__file__).parent.parent / "scripts" / "connectors" / "antigravity_hook.py"


@pytest.fixture
def hexley(tmp_path):
    seen, replies = [], {}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            seen.append({"auth": self.headers["Authorization"], **body})
            out = json.dumps(replies.get(body["tool_name"], {"effect": "BLOCK", "reason": "Blocked: not on the slip.", "tool": body["tool_name"]})).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(out)

        def log_message(self, *_):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    (tmp_path / "antigravity_token").write_text("session-token", encoding="utf-8")
    yield f"http://127.0.0.1:{server.server_port}", tmp_path, seen, replies
    server.shutdown()


def run(hexley, payload) -> dict:
    url, home, _, _ = hexley
    text = payload if isinstance(payload, bytes) else json.dumps(payload).encode("utf-8")
    p = subprocess.run([sys.executable, str(HOOK)], input=text, capture_output=True, timeout=30,
                       env={"HEXLEY_API": url, "HEXLEY_HOOK_HOME": str(home), "SYSTEMROOT": __import__("os").environ.get("SYSTEMROOT", "")})
    return json.loads(p.stdout)


def mcp(args) -> dict:
    return {"toolCall": {"name": "call_mcp_tool", "args": args}}


ISSUE = {"owner": "acme", "repo": "site", "issue_number": 1, "method": "get"}


@pytest.mark.parametrize("args", [
    {"ServerName": "github-mcp-server", "ToolName": "issue_read", "Arguments": ISSUE},
    {"ServerName": "github-mcp-server", "ToolName": "issue_read", "Arguments": json.dumps(ISSUE)},
])
def test_an_mcp_call_goes_to_hexley_under_its_real_name_with_its_arguments(hexley, args):
    _, _, seen, replies = hexley
    replies["mcp__github__issue_read"] = {"effect": "ALLOW", "reason": "ok", "tool": "github.issue_read"}
    assert run(hexley, mcp(args)) == {"decision": "allow"}
    assert seen[-1]["tool_name"] == "mcp__github__issue_read" and seen[-1]["tool_input"] == ISSUE
    assert seen[-1]["auth"] == "Bearer session-token"


def test_a_refusal_is_a_deny_with_hexleys_reason(hexley):
    out = run(hexley, mcp({"ServerName": "github", "ToolName": "add_issue_comment", "Arguments": {}}))
    assert out == {"decision": "deny", "reason": "Blocked: not on the slip."}


def test_a_held_call_is_a_deny_and_says_why(hexley):
    _, _, _, replies = hexley
    replies["mcp__github__add_issue_comment"] = {"effect": "ASK", "reason": "Approval needed.", "tool": "github.add_issue_comment"}
    assert run(hexley, mcp({"ServerName": "github", "ToolName": "add_issue_comment", "Arguments": {}})) == {"decision": "deny", "reason": "Approval needed."}


@pytest.mark.parametrize("payload", [
    mcp({}), mcp({"ServerName": "github"}), mcp({"ToolName": "issue_read"}), mcp({"ServerName": "github", "ToolName": "x", "Arguments": "not json"}),
    mcp({"ServerName": "github", "ToolName": "x", "Arguments": {}, "toolName": "other"}), mcp({"server": "github", "tool": "x", "args": {}}),
    mcp({"ServerName": "github", "ToolName": "x", "Arguments": [1]}), b"not json", b"",
])
def test_anything_it_cannot_read_is_a_deny(hexley, payload):
    if payload == b"":
        assert run(hexley, payload) == {"decision": "allow"}  # no tool at all: an empty call names nothing to judge
    else:
        assert run(hexley, payload)["decision"] == "deny"


def test_no_hexley_means_deny(hexley, tmp_path):
    _, home, _, _ = hexley
    dead = ("http://127.0.0.1:1", home, [], {})
    assert run(dead, mcp({"ServerName": "github", "ToolName": "x", "Arguments": {}}))["decision"] == "deny"


def test_a_missing_token_means_deny(hexley):
    url, home, seen, replies = hexley
    (home / "antigravity_token").unlink()
    assert run(hexley, mcp({"ServerName": "github", "ToolName": "x", "Arguments": {}}))["decision"] == "deny" and not seen


def test_a_built_in_tool_is_not_judged_and_the_log_holds_names_never_values(hexley):
    _, home, seen, _ = hexley
    assert run(hexley, {"toolCall": {"name": "view_file", "args": {"path": "secret-value"}}}) == {"decision": "allow"} and not seen
    run(hexley, mcp({"ServerName": "github", "ToolName": "x", "Arguments": {"body": "secret-value"}}))
    log = (home / "antigravity_hook.log").read_text(encoding="utf-8")
    assert "view_file" in log and "ServerName" in log and "secret-value" not in log and "session-token" not in log


def test_a_byte_order_mark_does_not_turn_a_call_into_a_deny(hexley):
    assert run(hexley, b"\xef\xbb\xbf" + json.dumps({"toolCall": {"name": "view_file"}}).encode()) == {"decision": "allow"}
