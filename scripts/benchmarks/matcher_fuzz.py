"""How well does the value matcher (rule R2) recognise restricted data written in unusual ways, and how often does it wrongly flag
ordinary text?

Method: build an index from 50 stock-register rows (quantity, depot code, dispatch date), then for each way of writing a value,
generate it for 25 values and ask the matcher whether it is recognised. Each way is labelled with what OUR OWN documentation
(docs/ADVERSARIAL_TESTS.md) says: 'supported', 'declared gap' or 'not documented' (a probe). A surprise is a supported way that is
missed, or a declared gap that is caught. The variants are chosen by us, so this shows what the matcher does on our list of tricks, not
what an attacker can do. Seeded, so it repeats."""

from __future__ import annotations

import random
from collections import defaultdict

from common import save, summarise, wilson
from sentinel.matcher import FingerprintIndex

SEED = 20261030
N_EACH = 25
ONES = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve", "thirteen", "fourteen",
        "fifteen", "sixteen", "seventeen", "eighteen", "nineteen"]
TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]


def words(n: int) -> str:
    if n < 20:
        return ONES[n]
    if n < 100:
        return TENS[n // 10] + ("-" + ONES[n % 10] if n % 10 else "")
    if n < 1000:
        return ONES[n // 100] + " hundred" + (" " + words(n % 100) if n % 100 else "")
    return words(n // 1000) + " thousand" + (" " + words(n % 1000) if n % 1000 else "")


def indian(n: int) -> str:
    s = str(n)
    if len(s) <= 3:
        return s
    head, tail = s[:-3], s[-3:]
    parts = []
    while len(head) > 2:
        parts.insert(0, head[-2:])
        head = head[:-2]
    if head:
        parts.insert(0, head)
    return ",".join(parts + [tail])


def script(s: str, zero: int) -> str:
    return "".join(chr(zero + int(c)) if c.isdigit() else c for c in s)


def fullwidth(s: str) -> str:
    return "".join(chr(ord(c) + 0xFEE0) if c.isalnum() or c == "-" else c for c in s).replace("-", "－")


ZW = "​"


def between(s: str) -> str:
    return ZW.join(s)


def leet(s: str) -> str:
    return s.translate(str.maketrans({"0": "O", "1": "l", "5": "S", "8": "B"}))


MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]


def ordinal(d: int) -> str:
    return f"{d}{'th' if 10 <= d % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(d % 10, 'th')}"


# (family, variant name, expectation by our docs, how to write quantity q)  -- q is an int
QTY = [
    ("quantity", "exact digits", "supported", lambda q: str(q)),
    ("quantity", "thousands comma 2,400", "supported", lambda q: f"{q:,}"),
    ("quantity", "Indian grouping 1,25,000", "supported", lambda q: indian(q)),
    ("quantity", "space grouping 2 400", "supported", lambda q: f"{q:,}".replace(",", " ")),
    ("quantity", "non-breaking space grouping", "supported", lambda q: f"{q:,}".replace(",", " ")),
    ("quantity", "dot grouping 2.400", "supported", lambda q: f"{q:,}".replace(",", ".")),
    ("quantity", "with decimals 2400.00", "supported", lambda q: f"{q}.00"),
    ("quantity", "full-width digits", "supported", lambda q: fullwidth(str(q))),
    ("quantity", "Devanagari digits", "supported", lambda q: script(str(q), 0x0966)),
    ("quantity", "Arabic-Indic digits", "supported", lambda q: script(str(q), 0x0660)),
    ("quantity", "zero-width characters inside", "supported", lambda q: between(str(q))),
    ("quantity", "soft hyphens inside", "supported", lambda q: "­".join(str(q))),
    ("quantity", "URL-encoded digits", "supported", lambda q: "".join(f"%{ord(c):02X}" for c in str(q))),
    ("quantity", "HTML-entity digits", "supported", lambda q: "".join(f"&#{ord(c)};" for c in str(q))),
    ("quantity", "English number words", "supported", lambda q: words(q)),
    ("quantity", "digits spaced apart 2 4 0 0", "supported", lambda q: " ".join(str(q))),
    ("quantity", "approximation 'about 2,400' (value not exact)", "declared gap", lambda q: f"about {round(q, -2) + 100:,}"),
    ("quantity", "letters for digits (O for 0, l for 1)", "declared gap", lambda q: leet(str(q))),
    ("quantity", "hexadecimal 0x960", "not documented", lambda q: hex(q)),
    ("quantity", "digits reversed 0042", "not documented", lambda q: str(q)[::-1]),
    ("quantity", "digits split by letters 2x4x0x0", "not documented", lambda q: "x".join(str(q))),
    ("quantity", "split in two parts 24 and 00", "not documented", lambda q: f"{str(q)[:len(str(q)) // 2]} and then {str(q)[len(str(q)) // 2:]}"),
]
QTY_ROUND = [  # only for multiples of 100: the unit-suffix forms are exact equivalents
    ("quantity (round)", "unit suffix 2.4k", "supported", lambda q: f"{q / 1000:g}k"),
    ("quantity (round)", "unit suffix 2.4 thousand", "supported", lambda q: f"{q / 1000:g} thousand"),
    ("quantity (round)", "unit suffix 24 hundred", "supported", lambda q: f"{q // 100} hundred"),
]
CODE = [
    ("depot code", "exact FSD-14", "supported", lambda c: c),
    ("depot code", "lower case", "supported", lambda c: c.lower()),
    ("depot code", "no separator FSD14", "supported", lambda c: c.replace("-", "")),
    ("depot code", "space FSD 14", "supported", lambda c: c.replace("-", " ")),
    ("depot code", "non-breaking hyphen", "supported", lambda c: c.replace("-", "‑")),
    ("depot code", "full-width letters", "supported", lambda c: fullwidth(c)),
    ("depot code", "zero-width characters inside", "supported", lambda c: between(c)),
    ("depot code", "underscore FSD_14", "not documented", lambda c: c.replace("-", "_")),
    ("depot code", "letters spaced F S D 14", "not documented", lambda c: " ".join(c.split("-")[0]) + " " + c.split("-")[1]),
    ("depot code", "look-alike letters F5D-14", "declared gap", lambda c: c.replace("S", "5")),
    ("depot code", "spoken 'depot fourteen'", "declared gap", lambda c: f"depot {words(int(c.split('-')[1]))}"),
]
DATE = [  # d is (y, m, day)
    ("dispatch date", "ISO 2026-11-02", "supported", lambda y, m, d: f"{y}-{m:02d}-{d:02d}"),
    ("dispatch date", "dd/mm/yyyy", "supported", lambda y, m, d: f"{d:02d}/{m:02d}/{y}"),
    ("dispatch date", "2 November 2026", "supported", lambda y, m, d: f"{d} {MONTHS[m - 1]} {y}"),
    ("dispatch date", "2 Nov 2026", "supported", lambda y, m, d: f"{d} {MONTHS[m - 1][:3]} {y}"),
    ("dispatch date", "November 2nd, 2026", "supported", lambda y, m, d: f"{MONTHS[m - 1]} {ordinal(d)}, {y}"),
    ("dispatch date", "dd-mm-yyyy", "not documented", lambda y, m, d: f"{d:02d}-{m:02d}-{y}"),
    ("dispatch date", "compact 20261102", "not documented", lambda y, m, d: f"{y}{m:02d}{d:02d}"),
    ("dispatch date", "dotted 2026.11.02", "not documented", lambda y, m, d: f"{y}.{m:02d}.{d:02d}"),
    ("dispatch date", "relative 'the day after tomorrow'", "declared gap", lambda y, m, d: "the day after tomorrow"),
    ("dispatch date", "words 'the second of November'", "not documented", lambda y, m, d: f"the {words(d)} of {MONTHS[m - 1]}"),
]


def benign_texts(rng: random.Random, restricted_q: set[int], n: int) -> list[str]:
    out = []
    stems = ["The meeting is on {}.", "Please reply by {}.", "Reference {} was raised last week.", "Total for the order was {}.",
             "We shipped {} cartons.", "Invoice {} is attached.", "Call me on {}.", "The ticket number is {}.", "Budget approved: {}."]
    while len(out) < n:
        kind = rng.choice(["amount", "indian", "year", "small", "po", "invoice", "date", "code", "phone", "prose"])
        if kind in ("amount", "indian"):
            q = rng.randint(100, 99999)
            if q in restricted_q:
                continue
            v = f"{q:,}" if kind == "amount" else indian(q)
        elif kind == "year":
            v = str(rng.randint(2024, 2031))
        elif kind == "small":
            v = str(rng.randint(1, 99))
        elif kind == "po":
            v = f"PO-{rng.randint(1000, 9999)}"
        elif kind == "invoice":
            v = f"INV-2026-{rng.randint(1, 9999):04d}"
        elif kind == "date":
            v = f"{rng.randint(1, 28):02d}/{rng.randint(1, 12):02d}/2027"  # a year outside the register's dates
        elif kind == "code":
            v = f"{rng.choice(['XYZ', 'QRS', 'ABC'])}-{rng.randint(51, 99)}"
        elif kind == "phone":
            v = f"+91 9{rng.randint(10**8, 10**9 - 1)}"
        else:
            out.append(rng.choice(["Thank you for your quotation, we will review it and revert shortly.", "Please find the acknowledgement of receipt.",
                                   "The vendor confirmed delivery within three weeks of the purchase order.", "Regards, Procurement Office."]))
            continue
        out.append(rng.choice(stems).format(v))
    return out


def main() -> None:
    rng = random.Random(SEED)
    rows = []
    # 25 round quantities (for the unit-suffix forms), 25 arbitrary ones; 50 distinct codes and dates
    quantities = [rng.choice(range(100, 1000)) * 100 for _ in range(25)] + [rng.randint(100, 99999) for _ in range(25)]
    quantities = list(dict.fromkeys(quantities))
    while len(quantities) < 50:
        quantities.append(rng.randint(100, 99999))
    dates = list(dict.fromkeys((2026, rng.randint(9, 12), rng.randint(1, 28)) for _ in range(200)))[:50]
    codes = [f"FSD-{i:02d}" for i in range(1, 51)]
    text = "\n".join(f"Depot {codes[i]}: {quantities[i]:,} units on hand, next dispatch {dates[i][0]}-{dates[i][1]:02d}-{dates[i][2]:02d}" for i in range(50))
    index = FingerprintIndex()
    index.add(text, ["quantity", "depot_code", "dispatch_date"], source_ref="query_stock")

    rng2 = random.Random(SEED + 1)
    arbitrary_q = rng2.sample([q for q in quantities if q % 100], min(N_EACH, len([q for q in quantities if q % 100])))
    round_q = rng2.sample([q for q in quantities if q % 100 == 0], min(N_EACH, len([q for q in quantities if q % 100 == 0])))
    sample_codes = rng2.sample(codes, N_EACH)
    sample_dates = rng2.sample(dates, N_EACH)

    def detects(variant: str) -> bool:
        return bool(index.scan_text(f"As discussed, the figure is {variant} for that site."))

    results = defaultdict(lambda: {"n": 0, "detected": 0, "examples_missed": []})
    plan = ([(f, v, e, fn, arbitrary_q) for f, v, e, fn in QTY] + [(f, v, e, fn, round_q) for f, v, e, fn in QTY_ROUND] +
            [(f, v, e, fn, sample_codes) for f, v, e, fn in CODE] + [(f, v, e, (lambda d, fn=fn: fn(*d)), sample_dates) for f, v, e, fn in DATE])
    for family, name, expected, fn, values in plan:
        r = results[(family, name, expected)]
        for val in values:
            try:
                written = fn(val)
            except Exception:  # noqa: BLE001
                continue
            r["n"] += 1
            if detects(written):
                r["detected"] += 1
            elif len(r["examples_missed"]) < 2:
                r["examples_missed"].append(written)

    print(f"{'family':<18}{'way of writing it':<46}{'docs say':<16}{'recognised':>12}")
    table, by_expect = [], defaultdict(lambda: [0, 0])
    for (family, name, expected), r in results.items():
        rate = r["detected"] / r["n"] if r["n"] else 0
        surprise = (expected == "supported" and r["detected"] < r["n"]) or (expected == "declared gap" and r["detected"] > 0)
        print(f"{family:<18}{name:<46}{expected:<16}{r['detected']:>5}/{r['n']:<4}{'  <-- surprise' if surprise else ''}")
        table.append({"family": family, "way": name, "docs_say": expected, "recognised": r["detected"], "n": r["n"], "surprise": surprise,
                      "examples_missed": r["examples_missed"]})
        by_expect[expected][0] += r["detected"]
        by_expect[expected][1] += r["n"]

    summary = {}
    for exp, (k, n) in by_expect.items():
        lo, hi = wilson(k, n)
        summary[exp] = {"recognised": k, "n": n, "rate": round(k / n, 4), "ci95": [lo, hi]}
    print()
    for exp, s in summary.items():
        print(f"{exp:<16} recognised {s['recognised']} of {s['n']}  ({100 * s['rate']:.1f}%, 95% interval {100 * s['ci95'][0]:.1f} to {100 * s['ci95'][1]:.1f}%)")

    # False positives: ordinary text that is not restricted data
    benign = benign_texts(random.Random(SEED + 2), set(quantities), 400)
    flagged = [t for t in benign if index.scan_text(t)]
    lo, hi = wilson(len(flagged), len(benign))
    print(f"\nordinary text wrongly flagged: {len(flagged)} of {len(benign)} (95% interval {100 * lo:.1f} to {100 * hi:.1f}%)")
    for t in flagged[:5]:
        print("   flagged:", t)
    print("saved", save("matcher_fuzz", {"seed": SEED, "per_variant_n": N_EACH, "by_what_our_docs_say": summary, "variants": table,
                                         "false_positives": {"flagged": len(flagged), "n": len(benign), "ci95": [lo, hi], "examples": flagged[:10]},
                                         "note": "variants were chosen by us; this is not an attacker's best list"}))


if __name__ == "__main__":
    main()
