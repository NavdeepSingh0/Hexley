"""The website's numbers come from scripts/export_evidence.py, never from a page (core plan F6)."""

import importlib.util
import json
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("export_evidence", ROOT / "scripts" / "export_evidence.py")
export = importlib.util.module_from_spec(spec)
spec.loader.exec_module(export)

COMMITTED = ROOT / "site" / "public" / "evidence.json"
REQUIRED = {"group", "group_title", "arm", "label", "value", "n", "ci95", "source_file", "caveat"}


def test_the_committed_file_is_exactly_what_the_script_produces_from_the_committed_results():
    """If someone edits evidence.json by hand, or adds a result file without re-running the script, this fails."""
    assert json.loads(COMMITTED.read_text(encoding="utf-8")) == export.build_evidence()


def test_every_entry_has_its_sample_size_interval_source_and_caveat():
    for e in export.build_evidence():
        assert REQUIRED <= set(e), e
        assert e["arm"] in ("protected", "unprotected")
        assert isinstance(e["n"], int) and e["n"] > 0
        lo, hi = e["ci95"]
        assert 0.0 <= lo <= hi <= 1.0
        assert e["caveat"].strip()
        assert (ROOT / e["source_file"]).is_file(), e["source_file"]


def test_the_shown_value_is_the_counts_in_the_source_file():
    for e in export.build_evidence():
        k, n = (int(x) for x in e["value"].split(" of "))
        assert n == e["n"] and 0 <= k <= n
    scripted = json.loads((ROOT / "eval/results" / Path(export.build_evidence()[0]["source_file"]).name).read_text(encoding="utf-8"))
    sentinel = scripted["metrics"]["fingerprint_enforcement"]["by_column"]["sentinel"]
    first = export.build_evidence()[0]
    assert first["value"] == f"{sentinel['through']} of {sentinel['supported_attempts']}"


def test_each_group_pairs_a_protected_and_an_unprotected_figure():
    groups: dict[str, set[str]] = {}
    for e in export.build_evidence():
        groups.setdefault(e["group"], set()).add(e["arm"])
    assert groups and all(arms == {"protected", "unprotected"} for arms in groups.values())


def _copy_results(tmp_path):
    results = tmp_path / "eval" / "results"
    results.mkdir(parents=True)
    for name in ("scripted-20261028T103528.json", "recorded-20261026T195255.json"):
        shutil.copy(ROOT / "eval" / "results" / name, results / name)
    return tmp_path, results


def test_a_metric_with_no_sample_size_stops_the_export_instead_of_writing_a_partial_file(tmp_path):
    root, results = _copy_results(tmp_path)
    path = results / "scripted-20261028T103528.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["metrics"]["fingerprint_enforcement"]["by_column"]["sentinel"]["through_rate"]["n"] = 0
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(SystemExit, match="no usable k, n and interval"):
        export.build_evidence(results, root)


def test_a_missing_result_file_stops_the_export(tmp_path):
    root, results = _copy_results(tmp_path)
    (results / "recorded-20261026T195255.json").unlink()
    with pytest.raises(SystemExit, match="recorded"):
        export.build_evidence(results, root)


def test_the_newest_result_file_wins(tmp_path):
    root, results = _copy_results(tmp_path)
    older = results / "scripted-20200101T000000.json"
    older.write_text("{}", encoding="utf-8")
    assert export.latest("scripted", results).name == "scripted-20261028T103528.json"
