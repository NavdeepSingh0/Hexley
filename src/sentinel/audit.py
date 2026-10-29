"""Tamper-evident audit log: SHA-256 hash chain, Ed25519 signatures, durable append, bounded deadline.

What it proves: a record that was changed, removed from the middle, reordered, or forged without the key
is detected, and verification points at the first bad record. What it does NOT prove: that the events it
records were true, or that the whole log was not replaced or truncated. Truncation is only caught when the
verifier supplies the expected chain head (shown on the console). See docs/DECISIONS.md D-020.

Nothing secret is stored: arguments and tool results are kept as hashes, and the matched secret values are
removed from decision evidence (a hash of a four-digit number is trivially guessable, so values are dropped,
not hashed).
"""

from __future__ import annotations

import asyncio
import copy
import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from .models import AgentAction, Decision

GENESIS_PREV = "0" * 64
KID = "audit-1"


class AuditError(Exception):
    """The audit log could not durably record something. Callers in a protected column must fail closed."""


def canonical(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode()


def sha256_hex(data: bytes | str) -> str:
    return hashlib.sha256(data.encode() if isinstance(data, str) else data).hexdigest()


def record_hash(record: dict) -> str:
    """SHA-256 over the canonical JSON of the record without `hash` and `sig`."""
    return sha256_hex(canonical({k: v for k, v in record.items() if k not in ("hash", "sig")}))


# ---- payload builders (what is allowed into the log) ----------------------------------------------------------
def action_payload(action: AgentAction) -> dict:
    return {"tool": action.tool, "capability": action.capability.value, "resource_class": action.resource_class,
            "outbound": action.outbound, "column": action.column.value,
            "args_hash": sha256_hex(canonical(action.args)), "arg_names": sorted(action.args)}


def decision_payload(decision: Decision) -> dict:
    p = decision.model_dump(mode="json")
    for ev in p["evidence"]:
        ev["matched_tokens"] = []  # the console sees the values live; the permanent log never does
    return p


def result_payload(tool: str, text: str) -> dict:
    return {"tool": tool, "result_hash": sha256_hex(text), "size": len(text)}


# ---- verification ---------------------------------------------------------------------------------------
@dataclass(frozen=True)
class VerifyResult:
    ok: bool
    checked: int
    head: str | None
    first_bad_seq: int | None = None
    reason: str | None = None


def verify_records(records: list[dict], public_key: Ed25519PublicKey, expected_head: str | None = None) -> VerifyResult:
    if not records:
        return VerifyResult(False, 0, None, None, "log is empty (no genesis record)")
    prev = GENESIS_PREV
    for i, r in enumerate(records):
        seq = r.get("seq", i)
        try:
            if r.get("seq") != i:
                return VerifyResult(False, i, None, seq, f"sequence number {r.get('seq')} where {i} was expected")
            if r.get("prev_hash") != prev:
                return VerifyResult(False, i, None, seq, "chain broken: previous hash does not match")
            if record_hash(r) != r.get("hash"):
                return VerifyResult(False, i, None, seq, "record hash does not match its content (record was altered)")
            try:
                public_key.verify(bytes.fromhex(r["sig"]), bytes.fromhex(r["hash"]))
            except (InvalidSignature, ValueError, KeyError):
                return VerifyResult(False, i, None, seq, "signature invalid (not signed by the log's key)")
        except Exception as e:  # noqa: BLE001 - any malformed record is a verification failure
            return VerifyResult(False, i, None, seq, f"malformed record: {type(e).__name__}")
        prev = r["hash"]
    head = records[-1]["hash"]
    if expected_head is not None and head != expected_head:
        return VerifyResult(False, len(records), head, None, "chain head does not match the expected head (log was replaced or truncated)")
    return VerifyResult(True, len(records), head)


def read_records(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(json.loads(line))
    return out


def verify_file(path: Path, public_key: Ed25519PublicKey, expected_head: str | None = None) -> VerifyResult:
    try:
        records = read_records(path)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as e:
        return VerifyResult(False, 0, None, None, f"log could not be read: {type(e).__name__}")
    return verify_records(records, public_key, expected_head)


# ---- the log ----------------------------------------------------------------------------------------------
class AuditLog:
    def __init__(self, path: Path, key: Ed25519PrivateKey, deadline: float = 2.0):
        self.path = Path(path)
        self.key = key
        self.deadline = deadline
        self.broken = False
        self._altered: dict[int, dict] = {}  # DEMO ONLY: the original payload of every record tamper() changed, so it can be put back
        self._lock = asyncio.Lock()
        self._seq = -1
        self._prev = GENESIS_PREV
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists() and self.path.stat().st_size > 0:
            self._load_tail()
        else:
            self._append_genesis()

    @property
    def public_key(self) -> Ed25519PublicKey:
        return self.key.public_key()

    @property
    def head(self) -> str:
        return self._prev

    def _load_tail(self) -> None:
        try:
            records = read_records(self.path)
        except (OSError, json.JSONDecodeError) as e:
            raise AuditError(f"audit log could not be read: {e}") from e
        res = verify_records(records, self.public_key)
        if not res.ok:
            raise AuditError(f"refusing to use a corrupt or foreign audit log: {res.reason} (record {res.first_bad_seq})")
        self._seq, self._prev = records[-1]["seq"], records[-1]["hash"]

    def _append_genesis(self) -> None:
        rec = self._build("log.genesis", None, None, None, {"note": "Sentinel audit log"})
        self._write_line(json.dumps(rec, sort_keys=True, separators=(",", ":")))
        self._seq, self._prev = rec["seq"], rec["hash"]

    def _build(self, type: str, session_id: str | None, action_id: str | None, decision_id: str | None,
               payload: dict) -> dict:
        rec = {"seq": self._seq + 1, "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
               "type": type, "session_id": session_id, "action_id": action_id, "decision_id": decision_id,
               "payload": payload, "payload_hash": sha256_hex(canonical(payload)), "prev_hash": self._prev, "kid": KID}
        rec["hash"] = record_hash(rec)
        rec["sig"] = self.key.sign(bytes.fromhex(rec["hash"])).hex()
        return rec

    def _write_line(self, line: str) -> None:
        """Durable append: write, flush, fsync. (Replaced in tests to inject slow or failing storage.)"""
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
            f.flush()
            os.fsync(f.fileno())

    async def append(self, type: str, *, session_id: str | None = None, action_id: str | None = None,
                     decision_id: str | None = None, payload: dict | None = None) -> dict:
        """Append one record durably within the deadline, or raise AuditError. Never retries on its own."""
        async with self._lock:
            if self.broken:
                raise AuditError("audit log is unavailable: an earlier write failed and it has not been recovered")
            rec = self._build(type, session_id, action_id, decision_id, payload or {})
            line = json.dumps(rec, sort_keys=True, separators=(",", ":"))
            try:
                await asyncio.wait_for(asyncio.to_thread(self._write_line, line), timeout=self.deadline)
            except asyncio.TimeoutError as e:
                self.broken = True  # the write may still land later: memory no longer matches disk
                raise AuditError(f"audit write missed its {self.deadline}s deadline") from e
            except Exception as e:  # noqa: BLE001 - any storage failure
                self.broken = True
                raise AuditError(f"audit write failed: {e.__class__.__name__}") from e  # `type` is a parameter here
            self._seq, self._prev = rec["seq"], rec["hash"]
            return rec

    async def recover(self) -> None:
        """Re-read the real tail from disk after a failure, so a write that landed late is not duplicated."""
        async with self._lock:
            self._load_tail()
            self.broken = False

    def verify(self, expected_head: str | None = None) -> VerifyResult:
        return verify_file(self.path, self.public_key, expected_head)

    def export_lines(self) -> str:
        return self.path.read_text(encoding="utf-8") if self.path.exists() else ""

    def latest_block_seq(self) -> int:
        """Sequence number of the most recent BLOCK or FREEZE decision: the one the audience just watched."""
        for r in reversed(read_records(self.path)):
            if r["type"] == "decision" and r["payload"].get("decision", {}).get("effect") in ("BLOCK", "FREEZE"):
                return r["seq"]
        raise AuditError("no blocked action has been recorded yet")

    def tamper(self, seq: int) -> str | None:
        """DEMO ONLY: alter one record on disk without re-signing it, so the console can show detection.
        Returns the action id of the altered record, if it has one. The original is remembered for restore()."""
        records = read_records(self.path)
        if not 1 <= seq < len(records):
            raise AuditError("no such record to tamper with")
        self._altered.setdefault(seq, copy.deepcopy(records[seq]["payload"]))
        records[seq]["payload"]["tampered"] = True
        self._replace_file(records)
        return records[seq].get("action_id")

    def restore(self) -> list[int]:
        """DEMO ONLY: put back every record tamper() altered, exactly as it was, so the log verifies again and the demo can go
        on. Returns the sequence numbers restored. It cannot repair any other damage: a log altered by anything else stays bad."""
        if not self._altered:
            raise AuditError("no record was altered by the demo, so there is nothing to put back")
        records = read_records(self.path)
        done = sorted(seq for seq in self._altered if seq < len(records))
        for seq in done:
            records[seq]["payload"] = self._altered[seq]
        self._replace_file(records)
        self._altered.clear()
        return done

    @property
    def altered(self) -> list[int]:
        """DEMO ONLY: the records tamper() has changed and restore() would put back."""
        return sorted(self._altered)

    def _replace_file(self, records: list[dict]) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text("".join(json.dumps(r, sort_keys=True, separators=(",", ":")) + "\n" for r in records), encoding="utf-8")
        os.replace(tmp, self.path)

    # The demo's rewrite takes the same lock as an append, so a decision being recorded can never be lost between the read and
    # the replace of the file (that would break the chain for good, and restore() could not repair it).
    async def tamper_locked(self, seq: int) -> str | None:
        async with self._lock:
            return await asyncio.to_thread(self.tamper, seq)

    async def restore_locked(self) -> list[int]:
        async with self._lock:
            return await asyncio.to_thread(self.restore)
