"""Audit log unit tests: chain, signatures, tamper detection, durability and failure semantics (D-020)."""

import asyncio
import json
import time

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from sentinel.audit import (GENESIS_PREV, AuditError, AuditLog, action_payload, decision_payload, record_hash,
                            verify_file)
from sentinel.models import AgentAction, Capability, Column, Decision, Effect, Evidence, ReasonCode, RuleId
from datetime import datetime, timezone


@pytest.fixture()
def key():
    return Ed25519PrivateKey.generate()


@pytest.fixture()
def log(tmp_path, key):
    return AuditLog(tmp_path / "audit.jsonl", key)


def lines(path):
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x]


def write_lines(path, records):
    path.write_text("".join(json.dumps(r, sort_keys=True, separators=(",", ":")) + "\n" for r in records), encoding="utf-8")


async def fill(log, n=5):
    for i in range(n):
        await log.append("decision", session_id="ses_1", payload={"i": i})


# ---- chain and signatures ---------------------------------------------------------------------------
async def test_new_log_starts_with_a_genesis_record_and_chains(log, key):
    await fill(log, 3)
    recs = lines(log.path)
    assert [r["seq"] for r in recs] == [0, 1, 2, 3]
    assert recs[0]["type"] == "log.genesis" and recs[0]["prev_hash"] == GENESIS_PREV
    assert all(recs[i]["prev_hash"] == recs[i - 1]["hash"] for i in range(1, 4))
    assert all(r["hash"] == record_hash(r) for r in recs)
    assert verify_file(log.path, key.public_key()).ok


async def test_verify_reports_the_head_and_count(log, key):
    await fill(log, 4)
    res = verify_file(log.path, key.public_key())
    assert res.ok and res.checked == 5 and res.head == lines(log.path)[-1]["hash"]


# ---- tamper detection (matrix: the "corrupt one byte" demo) ----------------------------------------------
async def test_changing_one_value_is_found_at_that_record(log, key):
    await fill(log, 6)
    recs = lines(log.path)
    recs[3]["payload"]["i"] = 999
    write_lines(log.path, recs)
    res = verify_file(log.path, key.public_key())
    assert not res.ok and res.first_bad_seq == 3 and "hash" in res.reason


async def test_recomputing_the_hash_without_the_key_is_caught_by_the_signature(log, key):
    await fill(log, 6)
    recs = lines(log.path)
    recs[3]["payload"]["i"] = 999
    recs[3]["hash"] = record_hash(recs[3])  # attacker fixes the hash but cannot sign
    write_lines(log.path, recs)
    res = verify_file(log.path, key.public_key())
    assert not res.ok and res.first_bad_seq == 3 and "signature" in res.reason


async def test_a_whole_forged_chain_signed_with_another_key_is_rejected(tmp_path, key):
    forged = AuditLog(tmp_path / "forged.jsonl", Ed25519PrivateKey.generate())
    await fill(forged, 3)
    res = verify_file(forged.path, key.public_key())  # verifier pins OUR public key
    assert not res.ok and res.first_bad_seq == 0 and "signature" in res.reason


async def test_deleting_or_reordering_records_breaks_the_chain(log, key):
    await fill(log, 6)
    recs = lines(log.path)
    deleted = recs[:3] + recs[4:]
    write_lines(log.path, deleted)
    res = verify_file(log.path, key.public_key())
    assert not res.ok and res.first_bad_seq == 4  # the record after the gap no longer links
    swapped = recs[:2] + [recs[3], recs[2]] + recs[4:]
    write_lines(log.path, swapped)
    assert not verify_file(log.path, key.public_key()).ok


async def test_truncating_the_tail_is_only_caught_with_the_expected_head(log, key):
    await fill(log, 5)
    head_before = verify_file(log.path, key.public_key()).head
    recs = lines(log.path)
    write_lines(log.path, recs[:-2])
    assert verify_file(log.path, key.public_key()).ok  # a shorter valid chain: honest limit
    res = verify_file(log.path, key.public_key(), expected_head=head_before)
    assert not res.ok and "head" in res.reason


async def test_an_empty_or_unparseable_file_fails_verification(tmp_path, key):
    p = tmp_path / "x.jsonl"
    p.write_text("")
    assert not verify_file(p, key.public_key()).ok
    p.write_text("not json\n")
    assert not verify_file(p, key.public_key()).ok
    assert not verify_file(tmp_path / "missing.jsonl", key.public_key()).ok


# ---- reopening ----------------------------------------------------------------------------------------
async def test_reopening_continues_the_same_chain(tmp_path, key):
    a = AuditLog(tmp_path / "a.jsonl", key)
    await fill(a, 2)
    b = AuditLog(tmp_path / "a.jsonl", key)
    r = await b.append("decision", payload={"after": "restart"})
    assert r["seq"] == 3
    assert verify_file(b.path, key.public_key()).ok


async def test_refuses_to_open_a_corrupt_or_foreign_log(tmp_path, key):
    a = AuditLog(tmp_path / "a.jsonl", key)
    await fill(a, 3)
    recs = lines(a.path)
    recs[2]["payload"]["i"] = 5
    write_lines(a.path, recs)
    with pytest.raises(AuditError):
        AuditLog(a.path, key)
    other = AuditLog(tmp_path / "o.jsonl", Ed25519PrivateKey.generate())
    with pytest.raises(AuditError):
        AuditLog(other.path, key)


# ---- ordering and concurrency ---------------------------------------------------------------------------
async def test_concurrent_appends_get_unique_increasing_sequence_numbers(log, key):
    await asyncio.gather(*(log.append("decision", payload={"i": i}) for i in range(50)))
    recs = lines(log.path)
    assert [r["seq"] for r in recs] == list(range(51))
    assert verify_file(log.path, key.public_key()).ok


# ---- failure semantics (D-020; matrix rows 26 and 28) ------------------------------------------------------
async def test_a_failed_write_raises_and_marks_the_log_unavailable(log):
    def boom(line):
        raise OSError("disk full")

    log._write_line = boom
    with pytest.raises(AuditError):
        await log.append("decision", payload={})
    assert log.broken
    with pytest.raises(AuditError, match="unavailable"):
        await log.append("decision", payload={})  # fails closed until recovered


async def test_a_slow_write_hits_the_deadline_and_never_waits_forever(tmp_path, key):
    log = AuditLog(tmp_path / "s.jsonl", key, deadline=0.2)
    original = log._write_line

    def slow(line):
        time.sleep(0.6)
        original(line)

    log._write_line = slow
    t0 = time.perf_counter()
    with pytest.raises(AuditError, match="deadline"):
        await log.append("decision", payload={})
    assert time.perf_counter() - t0 < 0.5 and log.broken


async def test_recovery_after_a_late_write_does_not_duplicate_or_skip_a_sequence_number(tmp_path, key):
    """The slow write lands after the deadline: recovery re-reads the real tail instead of trusting memory."""
    log = AuditLog(tmp_path / "s.jsonl", key, deadline=0.1)
    original = log._write_line
    log._write_line = lambda line: (time.sleep(0.4), original(line))
    with pytest.raises(AuditError):
        await log.append("decision", payload={"late": True})
    await asyncio.sleep(0.6)  # the late write has landed on disk now
    log._write_line = original
    await log.recover()
    assert not log.broken
    r = await log.append("decision", payload={"next": True})
    seqs = [x["seq"] for x in lines(log.path)]
    assert seqs == list(range(len(seqs))) and r["seq"] == seqs[-1]
    assert verify_file(log.path, key.public_key()).ok


# ---- nothing secret in the log ---------------------------------------------------------------------------------
def make_action(args):
    return AgentAction(action_id="act_1", ts=datetime.now(timezone.utc), session_id="ses_1", contract_id="tc_1",
                       column=Column.SENTINEL, tool="send_email", capability=Capability.SEND,
                       resource_class="email_external", args=args, outbound=True)


def test_action_payload_stores_hashes_and_argument_names_not_values():
    p = action_payload(make_action({"to": "v@x.example", "body": "stock is 2400 at FSD-14"}))
    text = json.dumps(p)
    assert "2400" not in text and "FSD-14" not in text and "v@x.example" not in text
    assert p["args_hash"] and sorted(p["arg_names"]) == ["body", "to"]


def test_decision_payload_drops_matched_secret_values_but_keeps_the_explanation():
    d = Decision(decision_id="dec_1", action_id="act_1", effect=Effect.BLOCK, rule_ids=[RuleId.R2],
                 reason_code=ReasonCode.SECRET_EGRESS, summary_plain="Blocked: restricted values",
                 evidence=[Evidence(kind="fingerprint", detail="quantity from query_stock found in argument 'body'",
                                    matched_tokens=["2,400"], source_ref="query_stock")])
    p = decision_payload(d)
    assert "2,400" not in json.dumps(p)
    assert p["evidence"][0]["detail"].startswith("quantity from query_stock") and p["evidence"][0]["matched_tokens"] == []
    assert p["effect"] == "BLOCK" and p["rule_ids"] == ["R2"]
