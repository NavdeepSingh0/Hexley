"""One tool-calling request per hosted model: does it answer, and does it call a tool? (throwaway)

Writes nothing to the results files. Prints status, latency and the first tool call only.
Run: python -m uv run python spikes/nvidia_check.py model [model ...]
"""

import json
import sys
import time

import httpx

from bakeoff import SYSTEM, TOOLS
from eval_matrix import TASKS, Provider, load_env

load_env()
provider = Provider("nvidia")
with httpx.Client(timeout=75) as client:
    for model in sys.argv[1:]:
        payload = {"model": model, "temperature": 0.6, "tools": TOOLS,
                   "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": TASKS["v4"]}]}
        t0 = time.perf_counter()
        try:
            r = client.post(f"{provider.url}/chat/completions", json=payload, headers=provider.headers)
            dt = time.perf_counter() - t0
            if r.status_code != 200:
                print(f"{model}: HTTP {r.status_code} in {dt:.1f}s :: {r.text[:110]!r}")
                continue
            msg = r.json()["choices"][0]["message"]
            calls = msg.get("tool_calls") or []
            first = f"{calls[0]['function']['name']}({calls[0]['function'].get('arguments', '')[:50]})" if calls else "none"
            print(f"{model}: HTTP 200 in {dt:.1f}s, tool_calls={len(calls)} first={first}")
        except Exception as e:  # noqa: BLE001
            print(f"{model}: {type(e).__name__} after {time.perf_counter() - t0:.0f}s")
        time.sleep(2.5)
