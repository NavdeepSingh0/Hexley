"""Human approvals (R4), bound to the exact action.

An approval covers a hash of (session, tool, canonical arguments). It is one-time, it expires, and a
call with any different argument gets a different hash and therefore needs its own approval (G-008, D-022).
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Callable


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"
    USED = "used"


class ApprovalError(Exception):
    """The approval cannot be resolved (unknown, already decided, expired)."""


@dataclass
class Approval:
    approval_id: str
    session_id: str
    action_hash: str
    tool: str
    args: dict[str, Any]
    summary: str
    created: float
    expires: float
    status: ApprovalStatus = ApprovalStatus.PENDING
    event: asyncio.Event = field(default_factory=asyncio.Event, repr=False)

    def card(self) -> dict:
        return {"approval_id": self.approval_id, "session_id": self.session_id, "tool": self.tool,
                "args": self.args, "summary": self.summary, "status": self.status.value,
                "expires_in": max(0, int(self.expires - time.time()))}


class ApprovalStore:
    def __init__(self, ttl_seconds: float = 600.0, clock: Callable[[], float] = time.time):
        self.ttl = ttl_seconds
        self._clock = clock
        self._by_id: dict[str, Approval] = {}

    @staticmethod
    def hash_for(session_id: str, tool: str, args: dict[str, Any]) -> str:
        canonical = json.dumps({"session": session_id, "tool": tool, "args": args}, sort_keys=True,
                               separators=(",", ":"), default=str)
        return hashlib.sha256(canonical.encode()).hexdigest()

    def _refresh(self, a: Approval) -> Approval:
        if a.status in (ApprovalStatus.PENDING, ApprovalStatus.APPROVED) and self._clock() >= a.expires:
            a.status = ApprovalStatus.EXPIRED
            a.event.set()
        return a

    def request(self, session_id: str, tool: str, args: dict[str, Any], summary: str) -> Approval:
        """Create a pending approval; an identical request that is still pending is returned instead."""
        h = self.hash_for(session_id, tool, args)
        for a in self._by_id.values():
            if a.action_hash == h and self._refresh(a).status == ApprovalStatus.PENDING:
                return a
        now = self._clock()
        a = Approval(approval_id=f"apr_{uuid.uuid4().hex[:12]}", session_id=session_id, action_hash=h, tool=tool,
                     args=dict(args), summary=summary, created=now, expires=now + self.ttl)
        self._by_id[a.approval_id] = a
        return a

    def get(self, approval_id: str) -> Approval | None:
        a = self._by_id.get(approval_id)
        return self._refresh(a) if a else None

    def pending(self) -> list[Approval]:
        return [a for a in self._by_id.values() if self._refresh(a).status == ApprovalStatus.PENDING]

    def resolve(self, approval_id: str, approve: bool) -> Approval:
        a = self.get(approval_id)
        if a is None:
            raise ApprovalError("unknown approval")
        if a.status != ApprovalStatus.PENDING:
            raise ApprovalError(f"approval is already {a.status.value}")
        a.status = ApprovalStatus.APPROVED if approve else ApprovalStatus.DENIED
        a.event.set()
        return a

    def peek_granted(self, action_hash: str) -> Approval | None:
        """An approved, unexpired, unused approval for exactly this action, or None."""
        for a in self._by_id.values():
            if a.action_hash == action_hash and self._refresh(a).status == ApprovalStatus.APPROVED:
                return a
        return None

    def consume(self, action_hash: str) -> bool:
        """Use up the approval for this exact action. A second call finds nothing to use."""
        a = self.peek_granted(action_hash)
        if a is None:
            return False
        a.status = ApprovalStatus.USED
        return True

    async def wait(self, approval_id: str, timeout: float) -> ApprovalStatus:
        """Wait for the officer. Silence is a denial: a pending approval that times out becomes EXPIRED."""
        a = self._by_id[approval_id]
        try:
            await asyncio.wait_for(a.event.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            if a.status == ApprovalStatus.PENDING:
                a.status = ApprovalStatus.EXPIRED
                a.event.set()
        return self._refresh(a).status
