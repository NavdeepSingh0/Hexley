"""Where is data going? Extract and normalise recipients and hosts. Pure functions (invariant 1).

Used by R1 (is the recipient inside the slip?) and R3 (did the recipient come only from untrusted content?).
This is value matching on addresses, not general provenance: an address the model assembles from fragments
is not recognised (declared limit, ARCHITECTURE.md 5b).
"""

from __future__ import annotations

import re
from typing import Any

from .matcher import normalise

_EMAIL = re.compile(r"[a-z0-9._%+\-]+@[a-z0-9\-]+(?:\.[a-z0-9\-]+)+")
_URL_HOST = re.compile(r"https?://([a-z0-9\-]+(?:\.[a-z0-9\-]+)+)")


def extract_destinations(text: str) -> set[str]:
    """Every e-mail address and URL host in `text`, after decoding URL/HTML escapes and Unicode folding."""
    t = normalise(text)
    return set(_EMAIL.findall(t)) | {f"host:{h}" for h in _URL_HOST.findall(t)}


def domain_of(address: str) -> str:
    return address.rsplit("@", 1)[-1] if "@" in address else address.removeprefix("host:")


def recipients_in(value: Any) -> tuple[list[str], list[str]]:
    """Addresses in a destination argument (a string, or a list of strings), plus any strings that held none.

    `Shakti Sales <Sales@Shakti.example>` yields `sales@shakti.example`. A string with no address in it
    ("vendor email") is returned in the second list so R1 can refuse it."""
    if isinstance(value, (list, tuple)):
        emails: list[str] = []
        junk: list[str] = []
        for v in value:
            e, j = recipients_in(v)
            emails += e
            junk += j
        return emails, junk
    text = str(value)
    found = list(dict.fromkeys(_EMAIL.findall(normalise(text))))
    return (found, []) if found else ([], [text])
