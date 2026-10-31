"""Value fingerprinting for R2: which restricted values appear in an outbound argument?

This is value matching, not information-flow tracking. It recognises the representations listed in
docs/ADVERSARIAL_TESTS.md (exact, Unicode folding, other digit scripts, digit grouping, English number
words, unit suffixes, URL/HTML decoding, several date formats). Paraphrase and generalisation are
declared gaps. Pure functions only: no I/O, no clock, no LLM (invariant 1).

A value is never dropped from the index because an untrusted document also contains it: otherwise an
attacker could repeat a guessed number to switch detection off. The price is a false block when a
restricted value happens to equal an ordinary figure; that trade-off is deliberate.
"""

from __future__ import annotations

import hashlib
import html
import re
import unicodedata
import urllib.parse
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any

from .unwrap import with_decoded

MIN_NUMBER = 100  # smaller numbers are too common to be useful fingerprints

FIELD_KINDS = {"quantity": "number", "depot_code": "code", "dispatch_date": "date",
               # generic kinds, for confidential data that is not our stock register (core plan B2)
               "number": "number", "date": "date", "email": "email", "phone": "digits", "account": "digits",
               "id": "id", "text": "text"}
# `fingerprint_fields: [all]` indexes every generic kind. The weak "code" pattern (two to four letters and a short number)
# is deliberately NOT included: on arbitrary text it would index "page 12" and "item 7" and block innocent messages.
ALL_KINDS = frozenset({"number", "date", "email", "digits", "id", "text"})
SHINGLE_WORDS = 7  # a copied passage is recognised by seven consecutive words; shorter runs are common phrases

_UNITS = {w: i for i, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen "
    "sixteen seventeen eighteen nineteen".split())}
_UNITS.update({"twenty": 20, "thirty": 30, "forty": 40, "fourty": 40, "fifty": 50, "sixty": 60,
               "seventy": 70, "eighty": 80, "ninety": 90})
_BIG = {"thousand": 1_000, "lakh": 100_000, "lac": 100_000, "million": 1_000_000, "crore": 10_000_000}
_WORD_RUN = re.compile(r"\b(?:" + "|".join(sorted([*_UNITS, *_BIG, "hundred", "and"], key=len, reverse=True)) +
                       r")\b(?:(?:,?[\s-]+)(?:" + "|".join(sorted([*_UNITS, *_BIG, "hundred", "and"], key=len, reverse=True)) +
                       r")\b)*")  # a comma may sit inside number words: "two thousand, four hundred" (plan Q4)
_SUFFIX = {"k": 1_000, "thousand": 1_000, "hundred": 100, "lakh": 100_000, "lakhs": 100_000, "lac": 100_000,
           "lacs": 100_000, "crore": 10_000_000, "crores": 10_000_000, "million": 1_000_000}
_MONTHS = {m: i + 1 for i, m in enumerate(
    "january february march april may june july august september october november december".split())}
_MONTHS.update({m[:3]: i for m, i in list(_MONTHS.items())} | {"sept": 9})
_MONTH_RE = "|".join(sorted(_MONTHS, key=len, reverse=True))

_ISO = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
_DMY = re.compile(r"\b(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{4})\b")  # 02/11/2026, 02.11.2026, 02-11-2026
_YMD_DOT = re.compile(r"\b(\d{4})[./](\d{2})[./](\d{2})\b")  # 2026.11.02, 2026/11/02
_YMD_COMPACT = re.compile(r"(?<!\d)(20\d{2})(\d{2})(\d{2})(?!\d)")  # 20261102; a date only if it is a valid one
_D_MON_Y = re.compile(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+({_MONTH_RE})\.?,?\s+(\d{{4}})\b")
_MON_D_Y = re.compile(rf"\b({_MONTH_RE})\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?,?\s+(\d{{4}})\b")
_CODE = re.compile(r"\b([a-z]{2,4})[-_\s]?(\d{1,3})\b")  # FSD-14, fsd14, FSD 14, FSD_14
_NUMBER = re.compile(r"(\d{1,2}(?:,\d{2})+,\d{3}|\d{1,3}(?:[,.\s]\d{3})+|\d+(?:\.\d+)?)"
                     r"(?:\s*(k|thousand|hundred|lakhs?|lacs?|crores?|million)\b)?")  # Indian grouping first (plan Q4)
_SPACED_DIGITS = re.compile(r"(?<![\d.,])\d(?: \d){3,}(?![\d.,])")  # 2 4 0 0: four or more single digits, one space apart


def normalise(text: str) -> str:
    """Decode URL and HTML escapes, fold Unicode, map every decimal-digit script to ASCII, lower-case."""
    t = text
    for _ in range(3):  # a few passes cover double encoding
        decoded = html.unescape(urllib.parse.unquote(t))
        if decoded == t:
            break
        t = decoded
    t = unicodedata.normalize("NFKC", t)
    t = "".join(str(unicodedata.digit(c)) if unicodedata.category(c) == "Nd" else c for c in t)
    t = re.sub(r"[­​-‏⁠﻿]", "", t)
    t = re.sub(r"[‐-―−]", "-", t)
    return t.lower()


@dataclass(frozen=True)
class Candidate:
    kind: str  # number | code | date
    canonical: str
    snippet: str


def _mask(text: str, span: tuple[int, int]) -> str:
    return text[:span[0]] + " " * (span[1] - span[0]) + text[span[1]:]


def _valid_date(y: int, m: int, d: int) -> str | None:
    if 1 <= m <= 12 and 1 <= d <= 31 and 1900 <= y <= 2200:
        return f"{y:04d}-{m:02d}-{d:02d}"
    return None


def _words_value(run: str) -> int | None:
    tokens = [w for w in re.split(r"[\s,-]+", run) if w and w != "and"]
    if not tokens:
        return None
    total = current = 0
    for w in tokens:
        if w in _UNITS:
            current += _UNITS[w]
        elif w == "hundred":
            current = (current or 1) * 100
        elif w in _BIG:
            total += (current or 1) * _BIG[w]
            current = 0
    return total + current


def _num_str(value: Decimal) -> str | None:
    if value != value.to_integral_value():
        return None
    return str(int(value))


def candidates(norm: str, known_codes: frozenset[str] | None = None) -> list[Candidate]:
    """Every date, code and number in already-normalised text. Spans are masked so digits are not reused.

    `known_codes` limits code detection to codes in the index. Without it, ordinary text such as
    "have 2,400" would be read as a code "have2" and swallow part of a number."""
    found: list[Candidate] = []
    text = norm
    date_forms = ((_ISO, lambda m: (m[1], m[2], m[3])), (_YMD_DOT, lambda m: (m[1], m[2], m[3])),
                  (_DMY, lambda m: (m[3], m[2], m[1])), (_YMD_COMPACT, lambda m: (m[1], m[2], m[3])),
                  (_D_MON_Y, lambda m: (m[3], _MONTHS[m[2]], m[1])), (_MON_D_Y, lambda m: (m[3], _MONTHS[m[1]], m[2])))
    for pattern, parts in date_forms:
        for m in list(pattern.finditer(text)):
            y, mo, d = (int(x) for x in parts(m))
            iso = _valid_date(y, mo, d)
            if iso:
                found.append(Candidate("date", iso, m.group()))
            text = _mask(text, m.span())
    for m in list(_CODE.finditer(text)):
        canonical = f"{m[1]}{int(m[2]):02d}" if len(m[2]) == 1 else f"{m[1]}{m[2]}"
        if known_codes is not None and canonical not in known_codes:
            continue  # not one of ours: leave the text alone so its digits can still be read as a number
        found.append(Candidate("code", canonical, m.group()))
        text = _mask(text, m.span())
    for m in list(_WORD_RUN.finditer(text)):
        if not any(w in _UNITS for w in re.split(r"[\s,-]+", m.group())):
            continue  # "thousand" or "hundred" alone is a unit suffix for a digit string, not a number phrase
        value = _words_value(m.group())
        if value is not None:
            found.append(Candidate("number", str(value), m.group()))
        text = _mask(text, m.span())
    for m in list(_SPACED_DIGITS.finditer(text)):
        found.append(Candidate("number", str(int(m.group().replace(" ", ""))), m.group()))
        text = _mask(text, m.span())
    for m in _NUMBER.finditer(text):
        raw, suffix = m.group(1), m.group(2)
        try:
            if suffix:
                value = Decimal(re.sub(r"[,\s]", "", raw)) * _SUFFIX[suffix]
                canonical = _num_str(value)
                if canonical:
                    found.append(Candidate("number", canonical, m.group()))
            else:
                grouped = re.fullmatch(r"\d{1,3}(?:[,.\s]\d{3})+|\d{1,2}(?:,\d{2})+,\d{3}", raw)
                value = Decimal(re.sub(r"[,.\s]", "", raw)) if grouped else Decimal(raw)
                canonical = _num_str(value)
                if canonical:
                    found.append(Candidate("number", canonical, m.group()))
        except InvalidOperation:
            continue
    return found


@dataclass(frozen=True)
class Match:
    kind: str
    canonical: str
    source_ref: str
    snippet: str
    path: str = ""
    source_action: str | None = None  # the call whose result first held this value


_EMAIL_RE = re.compile(r"[a-z0-9._%+\-]+@[a-z0-9\-]+(?:\.[a-z0-9\-]+)+")
_DIGITS_RUN = re.compile(r"(?<!\d)\+?\d(?:[\s().\-]?\d){8,14}(?!\d)")  # 9 to 15 digits, however separated (phones, accounts)
_ID_RE = re.compile(r"\b([a-z]{2,6})[-_ ]?(\d{3,}(?:[ -]\d{3,})*)\b")  # CUST-00123, emp 4471, ACCT_99231, zqx 1000 451
# A machine name: warehouse_prod, svc_inventory_rw, s3://bucket-eu1, a path or an internal address. Plain hyphenated words are not one.
_MACHINE_NAME = re.compile(r"(?<![\w.@-])[a-z0-9]+(?:(?:[_./-]|://)+[a-z0-9]+)+(?![\w@-])")


def _digits_key(run: str) -> str:
    d = re.sub(r"\D", "", run)
    return d[-10:] if len(d) >= 10 else d  # +91 98765 43210 and 9876543210 are the same number


def _id_key(letters: str, number: str) -> str:
    return f"{letters}{int(re.sub(r'[ -]', '', number))}"  # leading zeros and digit groups do not make a different identifier


def _machine_names(norm: str) -> list[str]:
    names = (m.group() for m in _MACHINE_NAME.finditer(norm))
    # An underscore, a digit, a scheme, two slashes or a file ending says machine; "read/write" says English.
    return list(dict.fromkeys(n for n in names if len(n) >= 7 and (re.fullmatch(r"\d{1,3}(?:\.\d{1,3}){3}", n)  # an internal address
                                                                  or (re.search(r"[a-z]", n) and re.search(r"_|\d|://|/.*/|\.[a-z]{1,5}$", n)))))


def _shingles(norm: str) -> list[str]:
    words = re.findall(r"[a-z0-9']+", norm)
    return [" ".join(words[i:i + SHINGLE_WORDS]) for i in range(len(words) - SHINGLE_WORDS + 1)]


def _shingle_key(shingle: str) -> str:
    return hashlib.sha1(shingle.encode()).hexdigest()[:16]  # the index keeps hashes, not copies of confidential prose


def _generic_candidates(norm: str, kinds: set[str]) -> list[Candidate]:
    out: list[Candidate] = []
    if "email" in kinds:
        out += [Candidate("email", m, m) for m in dict.fromkeys(_EMAIL_RE.findall(norm))]
    if "digits" in kinds:
        out += [Candidate("digits", _digits_key(m.group()), m.group().strip()) for m in _DIGITS_RUN.finditer(norm)]
    if "id" in kinds:
        out += [Candidate("id", _id_key(m[1], m[2]), m.group()) for m in _ID_RE.finditer(norm)]
        out += [Candidate("id", name, name) for name in _machine_names(norm)]
    if "text" in kinds:
        out += [Candidate("text", _shingle_key(s), s) for s in dict.fromkeys(_shingles(norm))]
    return out


@dataclass
class FingerprintIndex:
    """Per-session set of restricted values seen in tool results, each with where it came from."""

    entries: dict[tuple[str, str], str] = field(default_factory=dict)
    actions: dict[tuple[str, str], str | None] = field(default_factory=dict)  # (kind, value) -> the call that produced it
    origins: dict[tuple[str, str], set[str]] = field(default_factory=dict)  # (kind, value) -> the repositories, channels or pages it was read from

    def add(self, result_text: str, fields: list[str], source_ref: str, action_id: str | None = None, origin: str | None = None) -> None:
        wanted = set(ALL_KINDS) if "all" in fields else {FIELD_KINDS[f] for f in fields if f in FIELD_KINDS}
        norm = normalise(result_text)
        # Without "code" among the wanted kinds, switch the weak code pattern off entirely: left on, "owes 48,500" is read
        # as the code "owes48" and the number is indexed as 500. (`candidates` skips codes that are not in the known set.)
        known_codes = None if "code" in wanted else frozenset()
        for c in [*candidates(norm, known_codes), *_generic_candidates(norm, wanted)]:
            if c.kind not in wanted:
                continue
            if c.kind == "number" and int(c.canonical) < MIN_NUMBER:
                continue
            if (c.kind, c.canonical) not in self.entries:
                self.entries[(c.kind, c.canonical)] = source_ref
                self.actions[(c.kind, c.canonical)] = action_id
            if origin:
                self.origins.setdefault((c.kind, c.canonical), set()).add(origin)

    def already_at(self, kind: str, canonical: str, places: list[str]) -> bool:
        """Every place named here is somewhere this value was read from, so sending it there tells that place nothing new."""
        return bool(places) and set(places) <= self.origins.get((kind, canonical), set())

    def scan_text(self, text: str, path: str = "") -> list[Match]:
        codes = frozenset(canonical for kind, canonical in self.entries if kind == "code")
        norm = normalise(with_decoded(text))
        present = {kind for kind, _ in self.entries}
        found = [*candidates(norm, codes), *_generic_candidates(norm, present & ALL_KINDS)]
        return [Match(c.kind, c.canonical, self.entries[(c.kind, c.canonical)], c.snippet[:60], path,
                      self.actions.get((c.kind, c.canonical)))
                for c in found if (c.kind, c.canonical) in self.entries]

    def scan_args(self, value: Any, path: str = "") -> list[Match]:
        """Walk every field of the arguments (strings, numbers, nested dicts and lists)."""
        if isinstance(value, str):
            return self.scan_text(value, path)
        if isinstance(value, bool) or value is None:
            return []
        if isinstance(value, (int, float)):
            return self.scan_text(str(value), path)
        if isinstance(value, dict):
            return [m for k, v in value.items() for m in self.scan_args(v, f"{path}.{k}" if path else str(k))]
        if isinstance(value, (list, tuple)):
            return [m for i, v in enumerate(value) for m in self.scan_args(v, f"{path}[{i}]" if path else f"[{i}]")]
        return self.scan_text(str(value), path)
