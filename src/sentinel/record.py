"""`python -m sentinel record`: run a scenario several times against a model and keep EVERY attempt.

The recordings are what REPLAY later re-issues through the live gateway. Keeping every attempt (not just the best
one) is what stops a replay from being a cherry-picked success; the console shows "attempt i of N".
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import re
import subprocess
from pathlib import Path

from .runs import SCENARIOS, RunManager
from .stack import Stack, running_stack


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True,
                              timeout=10).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


async def _wait_finished(manager: RunManager, run_id: str, timeout: float) -> None:
    deadline = asyncio.get_running_loop().time() + timeout
    while manager.runs[run_id].status == "running":
        if asyncio.get_running_loop().time() > deadline:
            await manager.cancel(run_id)
            return
        await asyncio.sleep(0.25)


async def record_scenario(scenario_id: str, model: dict, attempts: int, out_dir: Path, source: str = "live",
                          timeout: float = 600.0, stack: Stack | None = None) -> list[Path]:
    """Run `attempts` attempts of one scenario and write one recording file per attempt. Returns the paths.

    Starts its own stack unless one is passed (tests pass theirs; see the note in stack.py about nesting)."""
    if scenario_id not in SCENARIOS:
        raise SystemExit(f"unknown scenario {scenario_id!r}; choose from {', '.join(SCENARIOS)}")
    out_dir.mkdir(parents=True, exist_ok=True)
    commit = _commit()
    async with contextlib.AsyncExitStack() as exit_stack:
        if stack is None:
            stack = await exit_stack.enter_async_context(running_stack())
            stack.rt.runs.pace = 0.0  # type: ignore[union-attr]
            stack.rt.approval_wait = 3.0  # a recording has no officer: an approval-held step ends as a denial
        manager: RunManager = stack.rt.runs  # type: ignore[assignment]
        written: list[Path] = []
        for i in range(1, attempts + 1):
            run = await manager.create(scenario_id, source, officer="recording", model=model)
            await manager.confirm(run.run_id)
            await _wait_finished(manager, run.run_id, timeout)
            rec = await manager.build_recording(run, i, attempts, commit)
            path = out_dir / f"{scenario_id}-{_slug(model.get('model', 'model'))}-{rec['recorded_at'][:19].replace(':', '')}-a{i}.json"
            path.write_text(json.dumps(rec, indent=2), encoding="utf-8")
            written.append(path)
            print(f"attempt {i}/{attempts}: {[l['outcome']['lane_outcome'] for l in rec['lanes']]} -> {path.name}", flush=True)
    return written
