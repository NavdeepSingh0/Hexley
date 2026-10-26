"""Throwaway probe: why does a hosted model return HTTP 500? Prints status and a short error body only.

Never prints headers or the key.
Run: python -m uv run python spikes/nvidia_probe.py '@super'
"""

import sys

import httpx

from eval_matrix import Provider, load_env
from bakeoff import TOOLS
import os

load_env()
provider = Provider("nvidia")
aliases = {"@bolt": os.environ.get("NEMOTRON_BOLT_MODEL", ""), "@super": os.environ.get("NEMOTRON_SUPER_MODEL", "")}
model = aliases.get(sys.argv[1], sys.argv[1])
cases = {
    "plain": {"model": model, "messages": [{"role": "user", "content": "Say hi in five words."}], "max_tokens": 32},
    "tools_no_system": {"model": model, "messages": [{"role": "user", "content": "Read quotation Q-1042."}],
                        "tools": TOOLS, "max_tokens": 128},
    "tools_temperature": {"model": model, "messages": [{"role": "user", "content": "Read quotation Q-1042."}],
                          "tools": TOOLS, "temperature": 0.6, "max_tokens": 128},
}
with httpx.Client(timeout=120) as client:
    print("model:", model)
    for name, payload in cases.items():
        r = client.post(f"{provider.url}/chat/completions", json=payload, headers=provider.headers)
        body = r.text.replace("\n", " ")[:300]
        print(f"{name}: HTTP {r.status_code} :: {body}")
