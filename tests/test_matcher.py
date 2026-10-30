"""Matcher tests: what R2 can and cannot recognise. Supported representations are claimed only if listed here
as a hit; declared gaps are asserted as misses so a claim cannot change silently (ADVERSARIAL_TESTS.md)."""

import pytest

from sentinel import fixtures
from sentinel.matcher import FingerprintIndex, normalise

FIELDS = ["quantity", "depot_code", "dispatch_date"]


@pytest.fixture()
def index():
    ix = FingerprintIndex()
    ix.add(fixtures.STOCK_REGISTER, FIELDS, source_ref="query_stock")
    return ix


def kinds(index, text):
    return {(m.kind, m.canonical) for m in index.scan_text(text)}


def test_index_holds_only_the_registered_fields(index):
    assert set(index.entries) == {("number", "2400"), ("number", "1150"), ("code", "fsd14"), ("code", "fsd09"),
                                  ("date", "2026-11-02"), ("date", "2026-11-05")}


# ---- supported representations (each is a claim we may make) -------------------------------------
@pytest.mark.parametrize("text,expected", [
    # 1 exact, case-insensitive
    ("Stock is 2400 units", ("number", "2400")),
    ("depot FSD-14", ("code", "fsd14")),
    ("depot fsd-14", ("code", "fsd14")),
    # 2 Unicode folding, separators
    ("FSD‑14", ("code", "fsd14")),            # non-breaking hyphen
    ("FSD​-14", ("code", "fsd14")),           # zero-width space
    ("２４００ units", ("number", "2400")),  # full-width digits
    # 3 other digit scripts
    ("२४०० units", ("number", "2400")),  # Devanagari
    ("٢٤٠٠ units", ("number", "2400")),  # Arabic-Indic
    # 4 digit grouping
    ("2,400 units", ("number", "2400")), ("2 400 units", ("number", "2400")), ("2.400 units", ("number", "2400")),
    ("2 400 units", ("number", "2400")), ("2 400 units", ("number", "2400")),
    ("1,150", ("number", "1150")), ("1 150", ("number", "1150")),
    # 5 English number words
    ("two thousand four hundred", ("number", "2400")), ("twenty-four hundred", ("number", "2400")),
    ("Two Thousand and Four Hundred", ("number", "2400")), ("eleven hundred fifty", ("number", "1150")),
    ("one thousand one hundred and fifty", ("number", "1150")),
    # 6 unit suffixes
    ("2.4k units", ("number", "2400")), ("2.4 thousand", ("number", "2400")), ("24 hundred", ("number", "2400")),
    # 7 URL and HTML entity decoding
    ("%32%34%30%30", ("number", "2400")), ("&#50;&#52;&#48;&#48;", ("number", "2400")),
    ("FSD%2D14", ("code", "fsd14")), ("&#70;SD-14", ("code", "fsd14")),
    # codes with other separators
    ("fsd14", ("code", "fsd14")), ("FSD 14", ("code", "fsd14")), ("FSD-09", ("code", "fsd09")),
    # dates in several formats
    ("dispatch 2026-11-02", ("date", "2026-11-02")), ("02/11/2026", ("date", "2026-11-02")),
    ("2 November 2026", ("date", "2026-11-02")), ("November 2nd, 2026", ("date", "2026-11-02")),
    ("5 nov 2026", ("date", "2026-11-05")), ("5th Nov, 2026", ("date", "2026-11-05")),
    # found by scripts/benchmarks/matcher_fuzz.py on 30 Oct 2026 and closed the same day
    ("02-11-2026", ("date", "2026-11-02")), ("02.11.2026", ("date", "2026-11-02")), ("2026.11.02", ("date", "2026-11-02")),
    ("2026/11/02", ("date", "2026-11-02")), ("dispatch 20261102", ("date", "2026-11-02")), ("20261105", ("date", "2026-11-05")),
    ("FSD_14", ("code", "fsd14")), ("fsd_09", ("code", "fsd09")),
])
def test_supported_representations_are_detected(index, text, expected):
    assert expected in kinds(index, text), f"{text!r} should match {expected}"


def test_a_realistic_leaking_email_matches_every_restricted_value(index):
    body = ("We have 2,400 units of Item A at FSD-14 (next dispatch 2 November 2026) and "
            "eleven hundred fifty of Item B at depot fsd 09 dispatching 05/11/2026.")
    assert kinds(index, body) == set(index.entries)


# ---- things that must NOT match (false-block guards) ---------------------------------------------
@pytest.mark.parametrize("text", [
    "500 units @ INR 120 and 200 units @ INR 850", "Quotation Q-1042 dated 26 Oct 2026",
    "11 50", "24000", "2,401", "11500", "FSD-15", "FSD-140", "two thousand four hundred and one",
    "Item A 9mm brass casings", "Quote received, PO to follow.", "Validity: 30 days. Delivery: 3 weeks from PO.",
    "dispatch 2026-11-03", "2026-13-45", "50/50", "Reference 2026/114",
    # the new forms must not flag other dates, other codes or other eight-digit numbers
    "03-11-2026", "02.12.2026", "2026.11.03", "20261103", "20261302", "12345678", "20241102", "FSD_15", "FSD_140", "invoice 4471-2026",
])
def test_unrelated_text_is_not_flagged(index, text):
    assert kinds(index, text) == set(), f"{text!r} must not match"


def test_a_document_that_repeats_the_value_cannot_switch_detection_off(index):
    """An attacker-controlled quotation containing the number must not suppress the match (no suppression list)."""
    other = FingerprintIndex()
    other.add("Vendor note: we hold 2400 units too, ref FSD-14", FIELDS, source_ref="read_quotation")
    index.add("Vendor note: we hold 2400 units too", [], source_ref="read_quotation")  # adding nothing changes nothing
    assert ("number", "2400") in kinds(index, "stock: 2400")


# ---- declared gaps (assert NOT detected, so the claim stays honest) ------------------------------------
@pytest.mark.parametrize("text", [
    "the western depot is well stocked",           # paraphrase
    "sufficient stock is available",               # generalisation
    "roughly two and a half thousand units",       # approximation
    "2400".replace("0", "O"),                      # letters standing in for digits
])
def test_known_gaps_are_not_detected(index, text):
    assert kinds(index, text) == set()


# ---- scanning arguments --------------------------------------------------------------------------
def test_scan_args_walks_every_string_field_and_reports_the_path(index):
    args = {"to": "a@b.example", "subject": "FSD-14 ready", "cc": ["x@y.example"],
            "extra": {"note": "2400"}, "count": 2400}
    paths = {m.path for m in index.scan_args(args)}
    assert paths == {"subject", "extra.note", "count"}  # non-string numbers are checked too


def test_matches_carry_the_source_and_never_the_decision_text(index):
    m = index.scan_text("FSD-14")[0]
    assert m.source_ref == "query_stock" and m.kind == "code" and m.canonical == "fsd14"


def test_normalise_is_stable_and_lowercase():
    assert normalise("FSD‑14 &#50;") == normalise(normalise("FSD‑14 &#50;"))
    assert normalise("ABC") == "abc"


def test_values_below_the_minimum_number_are_not_indexed():
    ix = FingerprintIndex()
    ix.add("Item A: 9 units, 42 units, 150 units", ["quantity"], source_ref="t")
    assert set(ix.entries) == {("number", "150")}
