"""python -m sentinel {up}

`up` runs the tool server (child process), the gateway and the API. Secrets are generated per run and
passed by environment; nothing is written to disk. M1 prints the API token once on start.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import secrets
import subprocess
import sys
from pathlib import Path

import uvicorn

from .api import create_api
from .gateway import build_gateway
from .runtime import build_runtime


async def _serve(app, port: int) -> None:
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    await server.serve()


async def _up(args: argparse.Namespace) -> None:
    downstream = secrets.token_urlsafe(32)
    api_token = os.environ.get("SENTINEL_API_TOKEN") or secrets.token_urlsafe(24)
    rt = build_runtime(tools_url=f"http://127.0.0.1:{args.tools_port}/mcp",
                       gateway_url=f"http://127.0.0.1:{args.gateway_port}/mcp",
                       downstream_token=downstream, api_token=api_token,
                       audit_dir=Path(args.data_dir), allow_tamper=args.demo)
    env = {**os.environ, "SENTINEL_DOWNSTREAM_TOKEN": downstream, "SENTINEL_TOOLS_PORT": str(args.tools_port)}
    tools = subprocess.Popen([sys.executable, "-m", "sentinel.tools.server"], env=env)
    print(f"Sentinel up. API http://127.0.0.1:{args.api_port}  gateway {rt.gateway_url}  tools pid {tools.pid}")
    print(f"API token (console login): {api_token}")
    try:
        await asyncio.gather(_serve(build_gateway(rt).http_app(), args.gateway_port),
                             _serve(create_api(rt), args.api_port))
    finally:
        tools.terminate()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="sentinel")
    sub = parser.add_subparsers(dest="command", required=True)
    up = sub.add_parser("up", help="start the tool server, gateway and API")
    up.add_argument("--api-port", type=int, default=8000)
    up.add_argument("--gateway-port", type=int, default=8100)
    up.add_argument("--tools-port", type=int, default=8200)
    up.add_argument("--data-dir", default="data/runtime", help="audit log and its signing key (git-ignored)")
    up.add_argument("--demo", action="store_true", help="enable the tamper endpoint used by the demo")
    rec = sub.add_parser("record", help="run a scenario against a model several times and keep every attempt")
    rec.add_argument("--scenario", required=True)
    rec.add_argument("--model", required=True, help="model id, e.g. nvidia/nemotron-3-ultra-550b-a55b")
    rec.add_argument("--provider", default="nvidia", choices=["nvidia", "ollama"])
    rec.add_argument("--attempts", type=int, default=5)
    rec.add_argument("--out", default="recordings")
    rec.add_argument("--source", default="live", choices=["live", "scripted"], help="scripted is for tests and demos of the tooling")
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


if __name__ == "__main__":
    main()
