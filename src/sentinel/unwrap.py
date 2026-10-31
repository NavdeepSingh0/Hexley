"""What a message says once simple wrappers are taken off. Base64 or hex costs an attacker one line; it should not hide a value from a check.

Only for text about to leave, so a scan sees the original and the decoded form together. It is not a decoder of everything: a split value, a custom
cipher or a paraphrase is still a declared gap (docs/THREAT_MODEL.md).
"""

from __future__ import annotations

import base64
import binascii
import re

_BASE64 = re.compile(r"[A-Za-z0-9+/_\-]{12,}={0,2}")
_HEX = re.compile(r"\b(?:[0-9a-fA-F]{2}){8,}\b")


def _printable(raw: bytes) -> str | None:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return None
    return text if text and all(c.isprintable() or c in "\r\n\t" for c in text) else None


def _decoded(text: str) -> list[str]:
    out = []
    for m in _BASE64.finditer(text):
        token = m.group().replace("-", "+").replace("_", "/")
        try:
            piece = _printable(base64.b64decode(token + "=" * (-len(token) % 4)))
        except (binascii.Error, ValueError):
            continue
        if piece:
            out.append(piece)
    for m in _HEX.finditer(text):
        piece = _printable(bytes.fromhex(m.group()))
        if piece:
            out.append(piece)
    return out


def with_decoded(text: str) -> str:
    """The text, followed by whatever its base64 and hex runs decode to."""
    pieces = _decoded(text)
    return "\n".join([text, *pieces]) if pieces else text
