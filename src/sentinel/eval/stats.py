"""Small-sample statistics for the evaluation. Descriptive only: with n this small an interval is the honest summary."""

from __future__ import annotations

import math


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for k successes in n trials. (0, 0) when n is 0."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (round(max(0.0, centre - half), 3), round(min(1.0, centre + half), 3))


def rate(k: int, n: int) -> dict:
    """{k, n, ci95}; the interval is always shown beside a count, never a bare percentage."""
    lo, hi = wilson(k, n)
    return {"k": k, "n": n, "ci95": [lo, hi]}
