"""Agents that drive the gateway: a real model, or a fixed script (scripted attacker and replay).

Both go through the same MCP client path, so a scripted or replayed run exercises exactly the code a live run does.
The script agent never sees the policy: it issues calls, and the observer compares what happened.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Protocol

from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

from .agent.runner import ModelEndpoint, Step, Transcript, run_agent


class Agent(Protocol):
    async def run(self, gateway_url: str, token: str, task: str) -> Transcript: ...


@dataclass
class ScriptStep:
    tool: str
    args: dict[str, Any]
    note: str = ""  # a human label, e.g. "reads the poisoned quotation"
    expect: dict[str, Any] | None = None  # recorded {"effect", "rule_ids"}; present only in a replay


class ReplayDiverged(Exception):
    """The live decision for a replayed step differs from the recorded one. The lane stops; nothing is replayed blind."""

    def __init__(self, index: int, recorded: dict, live: dict):
        super().__init__(f"step {index}: recorded {recorded}, live {live}")
        self.index, self.recorded, self.live = index, recorded, live


Observer = Callable[[int, ScriptStep, bool, str], Awaitable[None]]


@dataclass
class ScriptAgent:
    steps: list[ScriptStep]
    pace: float = 0.0  # seconds between steps (replay is time-compressed; the console shows it as such)
    observer: Observer | None = field(default=None, repr=False)

    async def run(self, gateway_url: str, token: str, task: str) -> Transcript:
        t = Transcript(model="script", task=task)
        t0 = time.perf_counter()
        transport = StreamableHttpTransport(gateway_url, headers={"Authorization": f"Bearer {token}"})
        try:
            async with Client(transport) as mcp:
                for i, step in enumerate(self.steps):
                    if i and self.pace:
                        await asyncio.sleep(self.pace)
                    try:
                        result = await mcp.call_tool(step.tool, step.args)
                        out, allowed = " ".join(getattr(p, "text", "") for p in result.content), True
                    except Exception as e:  # noqa: BLE001 - a gateway refusal surfaces as a tool error
                        out, allowed = str(e), False
                    t.steps.append(Step(step.tool, step.args, allowed, out))
                    if self.observer is not None:
                        await self.observer(i, step, allowed, out)
        except ReplayDiverged as d:
            t.diverged = {"step": d.index, "recorded": d.recorded, "live": d.live}
        except Exception as e:  # noqa: BLE001 - recorded, never raised, so a run can report it
            t.error = f"{type(e).__name__}: {e}"[:300]
        t.seconds = round(time.perf_counter() - t0, 1)
        return t


@dataclass
class ModelAgent:
    endpoint: ModelEndpoint  # shared by every lane of a run, so one throttle covers them all

    async def run(self, gateway_url: str, token: str, task: str) -> Transcript:
        return await run_agent(gateway_url, token, task, self.endpoint)
