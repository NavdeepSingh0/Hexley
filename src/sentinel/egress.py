"""Structured egress (hardened mode, D-019/D-028/D-029): validate a narrow request, resolve the recipient, render
the message. Pure functions: no I/O, no clock, no LLM (invariant 1).

The agent supplies only the template's slots (here: the quotation id). Sentinel chooses the recipient from the
vendor resolved for the slip's work item, and writes the message itself, so there is no field in which restricted
data could be carried. This narrows the attack surface; it does not remove every covert channel (calls, timing,
retries and other tools remain; stated on the limits slide).
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any

from .models import EgressTemplate, TaskContract

# What an `equals_session` validator may refer to. Anything else is refused (fail closed).
SESSION_VALUES = {"work_item_id"}


@dataclass(frozen=True)
class RenderedMessage:
    template_id: str
    to: str
    subject: str
    body: str
    message_sha256: str  # over (to, subject, body): recorded before sending, re-checked at the moment of sending


def find_template(contract: TaskContract, template_id: str) -> EgressTemplate | None:
    return next((t for t in contract.egress_templates if t.template_id == template_id), None)


def validate(template: EgressTemplate, args: dict[str, Any], contract: TaskContract) -> list[str]:
    """Every reason the request does not fit the template. Empty means it fits exactly.
    Messages name fields and rules, never values, because they are shown to the agent."""
    errors: list[str] = []
    expected = set(template.slots)
    extra = sorted(set(args) - expected)
    missing = sorted(expected - set(args))
    if extra:
        errors.append(f"unexpected field(s): {', '.join(extra)}")
    if missing:
        errors.append(f"missing field(s): {', '.join(missing)}")
    if contract.resolved_vendor is None or not contract.resolved_vendor.get("email"):
        errors.append("no vendor was resolved for this slip")
    for name, slot in template.slots.items():
        if name not in args:
            continue
        value = args[name]
        if not isinstance(value, str):
            errors.append(f"'{name}' must be text")
            continue
        if slot.pattern is not None and not re.fullmatch(slot.pattern, value):
            errors.append(f"'{name}' does not have the required format")
        if slot.enum is not None and value not in slot.enum:
            errors.append(f"'{name}' is not one of the allowed values")
        if slot.equals_session is not None:
            if slot.equals_session not in SESSION_VALUES:
                errors.append(f"'{name}' refers to an unsupported session value")
            elif value != getattr(contract, slot.equals_session, None):
                errors.append(f"'{name}' does not match the work item this slip was confirmed for")
    return errors


def render(template: EgressTemplate, args: dict[str, Any], contract: TaskContract) -> RenderedMessage:
    """Render the fixed message. Raises ValueError if the request does not fit the template."""
    errors = validate(template, args, contract)
    if errors:
        raise ValueError("; ".join(errors))
    assert contract.resolved_vendor is not None  # validate() guarantees it
    to = contract.resolved_vendor["email"]
    subject = template.subject.format(**args)
    body = template.body.format(**args)
    digest = hashlib.sha256(json.dumps({"to": to, "subject": subject, "body": body}, sort_keys=True,
                                       separators=(",", ":")).encode()).hexdigest()
    return RenderedMessage(template.template_id, to, subject, body, digest)
