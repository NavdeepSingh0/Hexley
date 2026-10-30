"""The model's reply is an exit too (plan Q6, PRODUCT_AUDIT §7 P5).

Seven of the 28 real incidents leaked through the reply, not a tool call: the model writes a Markdown image or link whose
address carries data (EchoLeak, ForcedLeak, GeminiJack, AgentFlayer, Slack AI), and the client fetches it while rendering.
A tool gateway never sees that. So before a reply is shown, Sentinel reads every address in it:
- an address that carries a restricted value or a found credential from this task is removed;
- an image or link to a place outside the slip's destinations is removed (an image would load by itself);
- anything else is left as written.
The reply keeps its words; a removed address is replaced by a short note saying what was removed and why.

Pure functions over the session's own index and slip. No model, no network (invariant 1).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from . import destinations

# Markdown image ![alt](url "title"), Markdown link [text](url), reference definition [id]: url, HTML <img src="url">,
# and bare addresses. Images are listed first: they load without a click.
_MD_IMAGE = re.compile(r"!\[[^\]]*\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
_MD_LINK = re.compile(r"(?<!!)\[[^\]]*\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
_MD_REF = re.compile(r"(?m)^\s{0,3}\[[^\]]+\]:\s*<?(\S+?)>?(?:\s+\"[^\"]*\")?\s*$")
_HTML_IMG = re.compile(r"(?i)<img\b[^>]*\bsrc\s*=\s*[\"']?([^\"'\s>]+)")
_BARE = re.compile(r"\b(?:https?|ftp)://[^\s<>\"')\]]+", re.I)


@dataclass(frozen=True)
class Finding:
    url: str
    host: str
    kind: str  # image | link
    reasons: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {"host": self.host, "kind": self.kind, "reasons": list(self.reasons)}


def _addresses(text: str) -> list[tuple[str, str, tuple[int, int]]]:
    """(url, kind, span of the whole construct to replace)."""
    out, taken = [], []
    for pattern, kind in ((_MD_IMAGE, "image"), (_HTML_IMG, "image"), (_MD_LINK, "link"), (_MD_REF, "link"), (_BARE, "link")):
        for m in pattern.finditer(text):
            span = m.span() if pattern is not _BARE else m.span()
            if any(s <= span[0] < e for s, e in taken):
                continue
            taken.append(span)
            out.append((m.group(1) if pattern is not _BARE else m.group(0), kind, span))
    return sorted(out, key=lambda x: x[2][0])


def check_reply(text: str, session: Any, contract: Any) -> tuple[str, list[Finding]]:
    """Return the reply as it may be shown, and what was removed. `session` may be None (nothing read yet)."""
    if not text:
        return text, []
    raw = contract.get("allowed_recipient_domains") if isinstance(contract, dict) else getattr(contract, "allowed_recipient_domains", None)
    allowed_list = sorted({d.lower() for d in raw or []})
    findings: list[Finding] = []
    pieces: list[str] = []
    last = 0
    for url, kind, (start, end) in _addresses(text):
        keys, bad = destinations.keys_in([url], "url")
        host = destinations.domain_of(keys[0]) if keys else "an unreadable address"
        reasons = []
        if session is not None:
            if session.index.scan_text(url) or session.secrets.scan_text(url):
                reasons.append("it carries data read in this task")
        outside = bool(bad) or not keys or not all(destinations.allowed(k, allowed_list) for k in keys)
        if outside and kind == "image":
            reasons.append("an image there would load by itself, to a place outside this task's slip")
        elif outside and "?" in url:
            reasons.append("it sends a query to a place outside this task's slip")
        if not reasons:
            continue
        findings.append(Finding(url, host, kind, tuple(reasons)))
        pieces.append(text[last:start])
        pieces.append(f"[{kind} to {host} removed by Hexley: {reasons[0]}]")
        last = end
    if not findings:
        return text, []
    pieces.append(text[last:])
    return "".join(pieces), findings
