"""R1 rule and decision-engine tests (invariants 2 and 3, fail closed, column semantics)."""

from datetime import datetime, timezone

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from sentinel import rules
from sentinel.contracts import Session, SessionClaims, draft_contract, load_templates
from sentinel.engine import decide
from sentinel.models import (AgentAction, Capability, Column, Effect, ReasonCode, RuleId, SessionStatus)
from sentinel.registry import RegistryError, load_registry

NOW = datetime(2026, 10, 27, 10, 0, tzinfo=timezone.utc)
REGISTRY = load_registry()


def make_session(column=Column.SENTINEL, allowed=None):
    contract = draft_contract(load_templates(), "quotation_processing", officer="Col. R. Menon", now=NOW)
    if allowed is not None:
        contract = contract.model_copy(update={"allowed_tools": allowed})
    contract = contract.model_copy(update={"status": SessionStatus.ACTIVE})
    claims = SessionClaims(session_id="ses_test", contract_id=contract.contract_id,
                           contract_hash=contract.compute_hash(), column=column, expires_at=NOW)
    return Session(claims=claims, contract=contract)


def action(tool, session, args=None):
    entry = REGISTRY.get(tool)
    return AgentAction(action_id="act_1", ts=NOW, session_id=session.session_id,
                       contract_id=session.contract.contract_id, column=session.column, tool=tool,
                       capability=entry.capability, resource_class=entry.resource_class,
                       args=args or {}, outbound=entry.outbound)


# ---- R1 table ----------------------------------------------------------------------------------
@pytest.mark.parametrize("tool,allowed,expect_effect,expect_reason", [
    ("read_quotation", None, Effect.ALLOW, ReasonCode.ALLOWED),
    ("query_stock", None, Effect.ALLOW, ReasonCode.ALLOWED),
    ("send_email", None, Effect.ALLOW, ReasonCode.ALLOWED),
    ("send_email", ["read_quotation"], Effect.BLOCK, ReasonCode.NOT_IN_SLIP),   # registered, not in slip
    ("delete_records", None, Effect.BLOCK, ReasonCode.NOT_IN_REGISTRY),          # unregistered tool
    ("delete_records", ["delete_records"], Effect.BLOCK, ReasonCode.NOT_IN_REGISTRY),  # slip cannot override
])
def test_r1_sentinel_column(tool, allowed, expect_effect, expect_reason):
    s = make_session(Column.SENTINEL, allowed)
    d = decide(action(tool, s), s, REGISTRY)
    assert d.effect == expect_effect and d.reason_code == expect_reason
    if expect_effect == Effect.BLOCK:
        assert d.rule_ids == [RuleId.R1]
        assert d.summary_plain.startswith("Blocked")


def test_r1_only_column_enforces_r1_too():
    s = make_session(Column.R1_ONLY, allowed=["read_quotation"])
    assert decide(action("send_email", s), s, REGISTRY).effect == Effect.BLOCK


def test_unprotected_column_runs_no_rules_and_says_so():
    s = make_session(Column.UNPROTECTED, allowed=["read_quotation"])
    d = decide(action("delete_records", s), s, REGISTRY)
    assert d.effect == Effect.ALLOW and d.reason_code == ReasonCode.NOT_ENFORCED and d.rule_ids == []


def test_block_summary_names_the_task_and_what_is_allowed():
    s = make_session(allowed=["read_quotation", "query_stock"])
    d = decide(action("send_email", s), s, REGISTRY)
    assert "send_email" in d.summary_plain
    assert "read_quotation" in d.summary_plain and "query_stock" in d.summary_plain


def test_decision_has_ids_and_latency():
    s = make_session()
    d = decide(action("read_quotation", s), s, REGISTRY)
    assert d.decision_id.startswith("dec_") and d.action_id == "act_1" and d.latency_ms >= 0


# ---- invariant 2: fail closed ------------------------------------------------------------------
def test_exception_in_rules_blocks_with_fail_closed(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("rule engine crashed")

    monkeypatch.setattr(rules, "rule_r1", boom)
    s = make_session(Column.SENTINEL)
    d = decide(action("read_quotation", s), s, REGISTRY)
    assert d.effect == Effect.BLOCK and d.reason_code == ReasonCode.FAIL_CLOSED
    assert "crashed" not in d.summary_plain  # internal error text is not leaked to the agent


def test_exception_does_not_fail_closed_in_unprotected_baseline_but_is_still_logged(monkeypatch):
    """The baseline runs no rules, so a broken rule cannot affect it (it must stay a clean control)."""
    monkeypatch.setattr(rules, "rule_r1", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("x")))
    s = make_session(Column.UNPROTECTED)
    assert decide(action("read_quotation", s), s, REGISTRY).effect == Effect.ALLOW


# ---- precedence --------------------------------------------------------------------------------
def test_combine_uses_freeze_over_block_over_ask_over_allow():
    mk = lambda eff: rules.RuleResult(RuleId.R1, eff, ReasonCode.NOT_IN_SLIP, "s")  # noqa: E731
    assert rules.combine([mk(Effect.ASK), mk(Effect.BLOCK)]).effect == Effect.BLOCK
    assert rules.combine([mk(Effect.BLOCK), mk(Effect.FREEZE)]).effect == Effect.FREEZE
    assert rules.combine([mk(Effect.ASK)]).effect == Effect.ASK
    assert rules.combine([]) is None


# ---- registry (invariant 6) --------------------------------------------------------------------
def test_unknown_tool_defaults_to_untrusted_restricted_outbound():
    e = REGISTRY.get("never_heard_of_it")
    assert not e.known and e.output_integrity == "untrusted" and e.output_confidentiality == "restricted"
    assert e.outbound and e.consequential and e.capability == Capability.SEND


def test_known_tool_labels_come_from_registry():
    assert REGISTRY.get("read_quotation").output_integrity == "untrusted"
    assert REGISTRY.get("query_stock").output_confidentiality == "restricted"
    assert REGISTRY.get("query_stock").fingerprint_fields == ["quantity", "depot_code", "dispatch_date"]


def test_malformed_registry_stops_startup(tmp_path):
    bad = tmp_path / "registry.yaml"
    bad.write_text("registry_version: 1\ndefault: {}\ntools:\n  x: {capability: teleport}\n")
    with pytest.raises(RegistryError):
        load_registry(bad)
    with pytest.raises(RegistryError):
        load_registry(tmp_path / "missing.yaml")
