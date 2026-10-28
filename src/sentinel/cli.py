"""python -m sentinel {up}

`up` runs the tool server (child process), the gateway and the API. Secrets are generated per run and
passed by environment; nothing is written to disk. M1 prints the API token once on start.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import re
import secrets
import shutil
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

import uvicorn

from .api import SITE_DIST, create_api
from .gateway import build_gateway
from .runtime import build_runtime, rotate_audit_log


async def _serve(app, port: int) -> None:
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    await server.serve()


CLOUDFLARED_DEFAULT = r"C:\Program Files (x86)\cloudflared\cloudflared.exe"


def start_tunnel(gateway_port: int, binary: str | None = None, timeout: float = 40.0) -> tuple[subprocess.Popen, str]:
    """Open a free cloudflared quick tunnel to the gateway and return (process, public https address).

    The address changes on every start, so the AI client's connector must be re-added each time. Only the gateway port
    is exposed; the API and the console stay on this machine."""
    exe = binary or shutil.which("cloudflared") or CLOUDFLARED_DEFAULT
    if not Path(exe).exists() and not shutil.which(exe):
        raise SystemExit(f"cloudflared not found ({exe}). Install it with: winget install Cloudflare.cloudflared")
    proc = subprocess.Popen([exe, "tunnel", "--url", f"http://127.0.0.1:{gateway_port}", "--no-autoupdate"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    deadline = time.monotonic() + timeout
    pattern = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")
    while time.monotonic() < deadline:
        line = proc.stderr.readline()
        if not line and proc.poll() is not None:
            break
        m = pattern.search(line)
        if m:
            return proc, m.group(0)
    proc.terminate()
    raise SystemExit("could not read the tunnel address from cloudflared; try again or pass --public-url")


def print_officer_code(req) -> None:
    print(f"\n*** Sign-in request from {req.client.client_name or 'an AI client'}: OFFICER CODE {req.officer_code} "
          f"(valid 5 minutes; type it on the consent page to approve the permission slip) ***\n", flush=True)


async def _up(args: argparse.Namespace) -> None:
    downstream = secrets.token_urlsafe(32)
    api_token = os.environ.get("SENTINEL_API_TOKEN") or secrets.token_urlsafe(24)
    data_dir = Path(args.data_dir)
    if args.demo:
        # A tampered log is (rightly) refused on the next start. In demo mode start a fresh chain every time, so a
        # rehearsal can never stop the real demo from starting; the old file is kept beside it.
        moved = rotate_audit_log(data_dir)
        if moved:
            print(f"demo mode: previous audit log moved to {moved.name}")
    rt = build_runtime(tools_url=f"http://127.0.0.1:{args.tools_port}/mcp",
                       gateway_url=f"http://127.0.0.1:{args.gateway_port}/mcp",
                       downstream_token=downstream, api_token=api_token,
                       audit_dir=data_dir, allow_tamper=args.demo)
    tunnel = None
    public_url = args.public_url
    if args.tunnel and not public_url:
        tunnel, public_url = start_tunnel(args.gateway_port, args.cloudflared)
    if public_url:
        # OAuth sign-in on the gateway's public address: the AI client signs in, the officer approves the slip here.
        from .oauth import SentinelOAuthProvider

        rt.oauth = SentinelOAuthProvider(rt, base_url=public_url, consent_base_url=args.consent_url,
                                         preset=args.oauth_preset, slip_ttl=args.oauth_ttl, on_request=print_officer_code)
    api_app = create_api(rt)
    rt.runs.pace = args.pace  # type: ignore[union-attr]
    env = {**os.environ, "SENTINEL_DOWNSTREAM_TOKEN": downstream, "SENTINEL_TOOLS_PORT": str(args.tools_port)}
    tools = subprocess.Popen([sys.executable, "-m", "sentinel.tools.server"], env=env)
    console_url = f"http://127.0.0.1:{args.api_port}/console/#token={api_token}"
    site_url = f"http://127.0.0.1:{args.api_port}/#token={api_token}"
    site_built = (SITE_DIST / "index.html").is_file()
    print(f"Sentinel up. API http://127.0.0.1:{args.api_port}  gateway {rt.gateway_url}  tools pid {tools.pid}")
    if site_built:
        print(f"Website and console (the token is in the link, not on screen once it opens): {site_url}")
    else:
        print("The website is not built (npm --prefix site ci && npm --prefix site run build); opening the console only.")
    print(f"Console (the token is in the link, not on screen once it opens): {console_url}")
    if public_url:
        print(f"Connector URL for an AI client: {public_url.rstrip('/')}/mcp   (Sign in, then enter the officer code printed here)")
    if not args.no_browser:
        # Open it ourselves so this terminal, which shows the token, never has to be on the projector.
        asyncio.get_running_loop().call_later(1.5, webbrowser.open, site_url if site_built else console_url)
    try:
        await asyncio.gather(_serve(build_gateway(rt).http_app(), args.gateway_port),
                             _serve(api_app, args.api_port))
    finally:
        tools.terminate()
        if tunnel is not None:
            tunnel.terminate()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="sentinel")
    sub = parser.add_subparsers(dest="command", required=True)
    up = sub.add_parser("up", help="start the tool server, gateway and API")
    up.add_argument("--api-port", type=int, default=8000)
    up.add_argument("--gateway-port", type=int, default=8100)
    up.add_argument("--tools-port", type=int, default=8200)
    up.add_argument("--data-dir", default="data/runtime", help="audit log and its signing key (git-ignored)")
    up.add_argument("--demo", action="store_true",
                    help="enable the tamper endpoint and start a fresh audit log (the old one is kept aside)")
    up.add_argument("--pace", type=float, default=1.2, help="seconds between scripted or replayed steps")
    up.add_argument("--no-browser", action="store_true", help="do not open the console in a browser")
    up.add_argument("--public-url", help="public https address of the gateway (turns on OAuth sign-in for AI clients)")
    up.add_argument("--tunnel", action="store_true", help="open a free cloudflared tunnel to the gateway and use its address")
    up.add_argument("--cloudflared", help="path to cloudflared (default: PATH, then the winget install location)")
    up.add_argument("--consent-url", help="where the officer's consent page lives (default: the gateway's own address)")
    up.add_argument("--oauth-preset", default="quotation_processing", help="slip template approved by an OAuth sign-in")
    up.add_argument("--oauth-ttl", type=int, default=3600, help="seconds an OAuth-approved slip lasts")
    rec = sub.add_parser("record", help="run a scenario against a model several times and keep every attempt")
    rec.add_argument("--scenario", required=True)
    rec.add_argument("--model", required=True, help="model id, e.g. nvidia/nemotron-3-ultra-550b-a55b")
    rec.add_argument("--provider", default="nvidia", choices=["nvidia", "ollama"])
    rec.add_argument("--attempts", type=int, default=5)
    rec.add_argument("--out", default="recordings")
    rec.add_argument("--source", default="live", choices=["live", "scripted"], help="scripted is for tests and demos of the tooling")
    ev = sub.add_parser("eval", help="measure Sentinel against a labelled corpus or real-model recordings")
    ev.add_argument("--agent", default="scripted", choices=["scripted", "recorded", "live"],
                    help="scripted: the labelled corpus, no model. recorded: summarise recordings/ already on disk. "
                         "live: record --n fresh attempts of the poisoned and clean scenarios against --model, then summarise")
    ev.add_argument("--n", type=int, default=5, help="attempts per scenario (live)")
    ev.add_argument("--model", help="model id (live), or a filter on recordings (recorded)")
    ev.add_argument("--provider", default="nvidia", choices=["nvidia", "ollama"])
    ev.add_argument("--recordings", default="recordings", help="where recordings are read (recorded) or written (live)")
    ev.add_argument("--out", default="eval/results")
    args = parser.parse_args(argv)
    if args.command == "up":
        try:
            asyncio.run(_up(args))
        except KeyboardInterrupt:
            pass
    elif args.command == "record":
        from .record import record_scenario

        paths = asyncio.run(record_scenario(args.scenario, {"provider": args.provider, "model": args.model},
                                            args.attempts, Path(args.out), source=args.source))
        print(f"wrote {len(paths)} recording(s) to {args.out}")
    elif args.command == "eval":
        from .eval import harness

        out_dir = Path(args.out)
        if args.agent == "scripted":
            result, js, md = asyncio.run(harness.main_scripted(out_dir))
        else:
            if args.agent == "live":
                if not args.model:
                    parser.error("--agent live needs --model")
                result = asyncio.run(harness.run_live({"provider": args.provider, "model": args.model}, args.n,
                                                      Path(args.recordings)))
            else:
                result = asyncio.run(harness.run_recorded(Path(args.recordings), args.model))
            js, md = harness.write_result(result, out_dir)
        print(md.read_text(encoding="utf-8"))
        print(f"wrote {js} and {md}")


if __name__ == "__main__":
    main()
