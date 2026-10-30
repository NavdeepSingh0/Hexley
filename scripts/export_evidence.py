"""Generate site/public/evidence.json from the committed result files in eval/results/.

The website never types a number by hand: every figure on it comes from this file, with its sample size, interval,
source file and caveat. Re-run after any new evaluation, then commit both.

Run from the repo root:  python -m uv run python scripts/export_evidence.py
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "eval" / "results"
OUT = ROOT / "site" / "public" / "evidence.json"


def latest(prefix: str, results: Path = RESULTS) -> Path:
    files = sorted(results.glob(f"{prefix}-*.json"))
    if not files:
        raise SystemExit(f"no {prefix}-*.json in {results}")
    return files[-1]


def build_evidence(results: Path = RESULTS, root: Path = ROOT) -> list[dict]:
    """The four figures the website shows, read from the newest scripted and recorded result files in `results`.

    Each entry carries its sample size, interval, source file and caveat; `group`, `group_title` and `arm` tell the home
    page which two figures sit on one card. A missing or malformed metric raises: a partial file is never written."""
    scripted_path, recorded_path = latest("scripted", results), latest("recorded", results)
    scripted = json.loads(scripted_path.read_text(encoding="utf-8"))
    recorded = json.loads(recorded_path.read_text(encoding="utf-8"))
    fe = scripted["metrics"]["fingerprint_enforcement"]["by_column"]
    delivered = recorded["metrics"]["delivered_restricted_data"]
    rel = lambda p: p.relative_to(root).as_posix()  # noqa: E731
    errored = len(recorded["errors"])
    lanes = sum(v["attempted"] for v in recorded["metrics"]["lane_outcomes"].values()) + errored

    def stat(group: str, title: str, arm: str, label: str, rate: dict, source: Path, caveat: str) -> dict:
        k, n = rate["k"], rate["n"]
        if not (isinstance(n, int) and n > 0 and isinstance(k, int) and 0 <= k <= n and len(rate["ci95"]) == 2):
            raise SystemExit(f"{rel(source)}: '{label}' has no usable k, n and interval ({rate!r})")
        return {"group": group, "group_title": title, "arm": arm, "label": label, "value": f"{k} of {n}", "n": n,
                "ci95": rate["ci95"], "source_file": rel(source), "caveat": caveat}

    return [
        stat("scripted", "Scripted attacks", "protected", "Attempts to get secrets out that got past Hexley (scripted corpus)",
             fe["sentinel"]["through_rate"], scripted_path,
             "Cases were written by us from the matcher's documented list and the routes we built: this shows it does what "
             "we say, not that no other route exists. Our own mock tools."),
        stat("scripted", "Scripted attacks", "unprotected", "The same cases with no protection",
             fe["unprotected"]["through_rate"], scripted_path, "Scripted attacker, mock tools, synthetic data."),
        stat("real-model", "A real model, one poisoned task", "unprotected",
             "Real model, poisoned quotation: lanes that leaked with no protection", delivered["poisoned/unprotected"],
             recorded_path, f"One model, one task. {errored} of {lanes} lanes failed on the hosted API and are excluded."),
        stat("real-model", "A real model, one poisoned task", "protected",
             "Real model, poisoned quotation: lanes that leaked behind Hexley", delivered["poisoned/sentinel"],
             recorded_path, "Small sample: a count with an interval, not a guarantee."),
    ]


def main() -> None:
    evidence = build_evidence()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(evidence, indent=2) + chr(10), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT).as_posix()}: {[e['value'] for e in evidence]}")


if __name__ == "__main__":
    main()
