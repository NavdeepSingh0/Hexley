"""One real Claude Code session using Claude's own connectors, judged by Hexley through the hook (plan F2/F3, D-057).

Hexley runs on the deployed server and holds no connector credential. The slip is made on the server with the officer's token, which
never leaves it. What ran is read from Hexley's own coverage and decisions, not from what the model says.

Usage: python scripts/connectors/live_hook.py --claude PATH --ssh-key PATH --host user@ip --slip slip.json --prompt "..." --allow TOOL [--allow TOOL]
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
import time
from pathlib import Path

import httpx

from sentinel.check import claude_code_settings

MAKE_SLIP = """#!/bin/bash
set -a; . /etc/hexley/hexley.env; set +a
curl -s -X POST http://127.0.0.1:10000/api/v1/slips -H "Authorization: Bearer $SENTINEL_API_TOKEN" \\
  -H 'Content-Type: application/json' -d @/tmp/hexley-slip.json
rm -f /tmp/hexley-slip.json
"""


def make_slip(key: str, host: str, slip: dict, work: Path) -> dict:
    """The officer's token stays on the server; only the session token comes back."""
    body, script = work / "slip.json", work / "mk.sh"
    body.write_text(json.dumps(slip), encoding="utf-8", newline="\n")
    script.write_text(MAKE_SLIP, encoding="utf-8", newline="\n")
    ssh = ["-i", key, "-o", "ConnectTimeout=20", "-o", "BatchMode=yes"]
    subprocess.run(["scp", *ssh, str(body), f"{host}:/tmp/hexley-slip.json"], check=True, capture_output=True)
    subprocess.run(["scp", *ssh, str(script), f"{host}:/tmp/hexley-mk.sh"], check=True, capture_output=True)
    out = subprocess.run(["ssh", *ssh, host, "sudo bash /tmp/hexley-mk.sh; rm -f /tmp/hexley-mk.sh"], check=True, capture_output=True, text=True)
    doc = json.loads(out.stdout)
    if "header_value" not in doc:
        raise SystemExit(f"the slip was refused: {out.stdout[:400]}")
    return doc


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--claude", required=True)
    p.add_argument("--ssh-key", required=True)
    p.add_argument("--host", required=True)
    p.add_argument("--api", default="https://hexley.site")
    p.add_argument("--slip", required=True, help="the slip as a JSON file")
    p.add_argument("--prompt", required=True)
    p.add_argument("--allow", action="append", required=True, help="a tool Claude Code may use without asking")
    p.add_argument("--timeout", type=int, default=240)
    p.add_argument("--then-ask", action="append", default=[], help="a JSON file {tool_name, tool_input}: ask Hexley about this call afterwards, nothing runs")
    a = p.parse_args()
    with tempfile.TemporaryDirectory(prefix="hexley-live-") as tmp:
        work = Path(tmp)
        slip = make_slip(a.ssh_key, a.host, json.loads(Path(a.slip).read_text(encoding="utf-8")), work)
        token = slip["header_value"].removeprefix("Bearer ")
        settings = work / "settings.json"
        settings.write_text(json.dumps(claude_code_settings(a.api, env_var="SENTINEL_TOKEN", skip=(), wait=15.0)), encoding="utf-8")
        started = time.monotonic()
        proc = subprocess.run([a.claude, "-p", a.prompt, "--output-format", "json", "--settings", str(settings), "--setting-sources", "",
                               "--restricted", "--no-session-persistence", "--allowedTools", *a.allow],
                              cwd=tmp, env={**os.environ, "SENTINEL_TOKEN": token}, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=a.timeout)
        try:
            doc = json.loads(proc.stdout)
        except ValueError:
            doc = {}
        print(f"exit {proc.returncode} in {time.monotonic() - started:.0f} s; models {sorted((doc.get('modelUsage') or {}).keys())}")
        print("REPLY:", str(doc.get("result", proc.stdout[:400])).strip()[:1500])
        if proc.stderr.strip():
            print("STDERR:", proc.stderr.strip()[:400])
        for raw in a.then_ask:
            # Put a call straight to Hexley's decision, in this session, once the model has finished. Nothing runs: no connector is
            # involved, so it can only show what Hexley would answer, given what this session really read.
            ask = json.loads(Path(raw).read_text(encoding="utf-8"))
            r = httpx.post(f"{a.api}/api/v1/check/call", headers={"Authorization": f"Bearer {token}"}, json={**ask, "wait_s": 0.1}, timeout=60)
            body = r.json() if r.status_code == 200 else {"status": r.status_code, "text": r.text[:300]}
            print(f"ASKED ({Path(raw).name}): effect={body.get('effect')} rules={body.get('rule_ids')} reason={str(body.get('reason'))[:220]}")
        ssh = ["ssh", "-i", a.ssh_key, "-o", "ConnectTimeout=20", "-o", "BatchMode=yes", a.host]
        read = (f"sudo bash -c 'set -a; . /etc/hexley/hexley.env; set +a; curl -s -H \"Authorization: Bearer $SENTINEL_API_TOKEN\" "
                f"http://127.0.0.1:10000/api/v1/sessions/{slip['session_id']}/coverage'")
        out = subprocess.run([*ssh, read], capture_output=True, text=True)
        try:
            print("COVERAGE:", json.dumps(json.loads(out.stdout).get("tools")))
        except ValueError:
            print("COVERAGE could not be read:", out.stdout[:200], out.stderr[:200])


if __name__ == "__main__":
    main()
