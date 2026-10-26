"""Throwaway: list model ids visible to the key (ids only, never the key).

Run: python -m uv run python spikes/nvidia_models.py [substring ...]
"""

import sys

import httpx

from eval_matrix import Provider, load_env

load_env()
provider = Provider("nvidia")
r = httpx.get(f"{provider.url}/models", headers=provider.headers, timeout=60)
print("HTTP", r.status_code)
ids = sorted(m["id"] for m in r.json().get("data", [])) if r.status_code == 200 else []
needles = [a.lower() for a in sys.argv[1:]]
shown = [i for i in ids if not needles or any(n in i.lower() for n in needles)]
print(f"{len(ids)} models visible; showing {len(shown)}")
for i in shown:
    print(" ", i)
