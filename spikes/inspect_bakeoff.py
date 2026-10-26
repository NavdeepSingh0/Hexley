"""Print the emails each model sent in the bake-off (throwaway helper)."""

import json
import sys
from pathlib import Path

name = sys.argv[1] if len(sys.argv) > 1 else "bakeoff.json"
data = json.loads((Path(__file__).parent / "out" / name).read_text())
for model, v in data["models"].items():
    print("=====", model)
    for kind in ("benign", "poisoned"):
        for i, run in enumerate(v["runs"][kind][:5]):
            if not run["emails"]:
                print(f"  {kind}#{i + 1}: NO EMAIL (steps={run['steps']})")
            for e in run["emails"]:
                body = (e.get("body") or "").replace("\n", " | ")[:240]
                print(f"  {kind}#{i + 1}: to={e.get('to')!r} body={body}")
