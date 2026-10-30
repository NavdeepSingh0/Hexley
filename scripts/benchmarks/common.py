"""Shared helpers for the benchmark scripts (plan: numbers for round 2). Run them from the repository folder:
    python -m uv run python scripts/benchmarks/perf.py          (speed)
    python -m uv run python scripts/benchmarks/matcher_fuzz.py  (value matching on generated variants)
    python -m uv run python scripts/benchmarks/incidents.py     (incident-shaped scenarios through the real engine)
Each writes a JSON file with its numbers, the commit and the machine to eval/benchmarks/."""

from __future__ import annotations

import json
import math
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "eval" / "benchmarks"
API_TOKEN = "bench-api-token"
DOWNSTREAM_TOKEN = "bench-downstream-secret"


def pct(sorted_values: list[float], p: float) -> float:
    if not sorted_values:
        return float("nan")
    k = max(0, min(len(sorted_values) - 1, math.ceil(p / 100 * len(sorted_values)) - 1))
    return sorted_values[k]


def summarise(values: list[float], unit: str) -> dict:
    s = sorted(values)
    return {"n": len(s), "unit": unit, "p50": round(pct(s, 50), 3), "p95": round(pct(s, 95), 3), "p99": round(pct(s, 99), 3),
            "max": round(s[-1], 3), "mean": round(sum(s) / len(s), 3)}


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson interval for k successes out of n (the same kind of interval the rest of the project reports)."""
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (round(max(0.0, centre - half), 4), round(min(1.0, centre + half), 4))


def machine() -> dict:
    def git(*a: str) -> str:
        try:
            return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True, timeout=20).stdout.strip()
        except Exception:  # noqa: BLE001
            return "unknown"
    return {"date": datetime.now(timezone.utc).isoformat(timespec="seconds"), "commit": git("rev-parse", "--short", "HEAD"),
            "dirty": bool(git("status", "--porcelain")), "python": sys.version.split()[0], "os": platform.platform(),
            "cpu": platform.processor()}


def save(name: str, data: dict) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    path = OUT / f"{name}-{stamp}.json"
    path.write_text(json.dumps({"machine": machine(), **data}, indent=1, default=str), encoding="utf-8")
    return path
