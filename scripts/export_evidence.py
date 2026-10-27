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


def latest(prefix: str) -> Path:
    files = sorted(RESULTS.glob(f"{prefix}-*.json"))
    if not files:
        raise SystemExit(f"no {prefix}-*.json in {RESULTS}")
    return files[-1]


def main() -> None:
    scripted_path, recorded_path = latest("scripted"), latest("recorded")
    scripted = json.loads(scripted_path.read_text(encoding="utf-8"))
    recorded = json.loads(recorded_path.read_text(encoding="utf-8"))
    fe = scripted["metrics"]["fingerprint_enforcement"]["by_column"]
    delivered = recorded["metrics"]["delivered_restricted_data"]
    rel = lambda p: p.relative_to(ROOT).as_posix()  # noqa: E731
    errored = len(recorded["errors"])
    lanes = sum(v["attempted"] for v in recorded["metrics"]["lane_outcomes"].values()) + errored

    def stat(label: str, k: int, n: int, ci: list, source: Path, caveat: str) -> dict:
        return {"label": label, "value": f"{k} of {n}", "n": n, "ci95": ci, "source_file": rel(source), "caveat": caveat}

    sc = fe["sentinel"]["through_rate"]
    un = fe["unprotected"]["through_rate"]
    pu, ps = delivered["poisoned/unprotected"], delivered["poisoned/sentinel"]
    evidence = [
        stat("Disguised leaks that got past Sentinel (scripted corpus)", sc["k"], sc["n"], sc["ci95"], scripted_path,
             "Cases were written from the matcher's own documented list: this shows it does what we say, "
             "not that no other disguise exists."),
        stat("The same cases with no protection", un["k"], un["n"], un["ci95"], scripted_path,
             "Scripted attacker, mock tools, synthetic data."),
        stat("Real model, poisoned quotation: lanes that leaked with no protection", pu["k"], pu["n"], pu["ci95"],
             recorded_path, f"One model, one task. {errored} of {lanes} lanes failed on the hosted API and are excluded."),
        stat("Real model, poisoned quotation: lanes that leaked behind Sentinel", ps["k"], ps["n"], ps["ci95"],
             recorded_path, "Small sample: a count with an interval, not a guarantee."),
    ]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(f"wrote {rel(OUT)}: {[e['value'] for e in evidence]}")


if __name__ == "__main__":
    main()
