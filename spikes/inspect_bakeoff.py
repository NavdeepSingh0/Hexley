"""Print the emails each model sent in the bake-off (throwaway helper)."""

import json
from pathlib import Path

data = json.loads((Path(__file__).parent / "out" / "bakeoff.json").read_text())
for model, v in data["models"].items():
    print("=====", model)
    for kind in ("benign", "poisoned"):
        for i, run in enumerate(v["runs"][kind][:5]):
            if not run["emails"]:
                print(f"  {kind}#{i + 1}: NO EMAIL (steps={run['steps']})")
            for e in run["emails"]:
                body = (e.get("body") or "").replace("\n", " | ")[:240]
                print(f"  {kind}#{i + 1}: to={e.get('to')!r} body={body}")
