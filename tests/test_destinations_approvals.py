"""Units: destination parsing (R1/R3 inputs) and the approval store (R4 binding, one-time use, expiry)."""

import asyncio

import pytest

from sentinel.approvals import ApprovalError, ApprovalStatus, ApprovalStore
from sentinel.destinations import domain_of, extract_destinations, recipients_in


# ---- destinations ---------------------------------------------------------------------------------------
@pytest.mark.parametrize("text,expected", [
    ("write to audit-desk@shakti.example today", {"audit-desk@shakti.example"}),
    ("Audit-Desk@SHAKTI.example", {"audit-desk@shakti.example"}),
    ("&#97;udit@shakti.example", {"audit@shakti.example"}),            # HTML entity
    ("audit%40shakti.example", {"audit@shakti.example"}),               # URL-encoded @
    ("see https://evil.example/path?x=1", {"host:evil.example"}),
    ("a@x.example and b@y.example", {"a@x.example", "b@y.example"}),
    ("nothing here", set()),
])
def test_extract_destinations(text, expected):
    assert extract_destinations(text) == expected


@pytest.mark.parametrize("value,emails,junk", [
    ("sales@shakti.example", ["sales@shakti.example"], []),
    ("Shakti Sales <Sales@Shakti.example>", ["sales@shakti.example"], []),
    ("vendor email", [], ["vendor email"]),
    ("", [], [""]),
    (["a@x.example", "b@y.example"], ["a@x.example", "b@y.example"], []),
    (["a@x.example", "someone"], ["a@x.example"], ["someone"]),
])
def test_recipients_in(value, emails, junk):
    assert recipients_in(value) == (emails, junk)


def test_domain_of():
    assert domain_of("a@shakti.example") == "shakti.example"
    assert domain_of("host:evil.example") == "evil.example"


# ---- approvals --------------------------------------------------------------------------------------------
def store(clock=None):
    return ApprovalStore(ttl_seconds=60, clock=clock or (lambda: 1000.0))


def test_the_hash_binds_session_tool_and_every_argument():
    h = ApprovalStore.hash_for
    base = h("ses_1", "update_vendor_bank", {"vendor": "shakti", "account_number": "111"})
    assert base == h("ses_1", "update_vendor_bank", {"account_number": "111", "vendor": "shakti"})  # order-free
    assert base != h("ses_1", "update_vendor_bank", {"vendor": "shakti", "account_number": "999"})  # other payload
    assert base != h("ses_2", "update_vendor_bank", {"vendor": "shakti", "account_number": "111"})  # other session
    assert base != h("ses_1", "send_email", {"vendor": "shakti", "account_number": "111"})  # other tool


def test_approving_one_action_does_not_grant_another():
    s = store()
    a = s.request("ses_1", "update_vendor_bank", {"account_number": "111"}, "x")
    b = s.request("ses_1", "update_vendor_bank", {"account_number": "999"}, "x")
    s.resolve(a.approval_id, True)
    assert s.peek_granted(a.action_hash) is a
    assert s.peek_granted(b.action_hash) is None  # the substituted payload is not covered


def test_an_approval_is_used_once():
    s = store()
    a = s.request("ses_1", "t", {"x": 1}, "x")
    s.resolve(a.approval_id, True)
    assert s.consume(a.action_hash) is True
    assert s.peek_granted(a.action_hash) is None and s.consume(a.action_hash) is False
    assert a.status == ApprovalStatus.USED


def test_an_identical_pending_request_is_not_duplicated():
    s = store()
    a = s.request("ses_1", "t", {"x": 1}, "x")
    assert s.request("ses_1", "t", {"x": 1}, "x") is a and len(s.pending()) == 1


def test_denied_expired_and_already_decided_approvals_grant_nothing():
    now = [1000.0]
    s = store(lambda: now[0])
    denied = s.request("ses_1", "t", {"x": 1}, "x")
    s.resolve(denied.approval_id, False)
    assert s.peek_granted(denied.action_hash) is None
    with pytest.raises(ApprovalError):
        s.resolve(denied.approval_id, True)  # cannot flip a decision
    expiring = s.request("ses_1", "t", {"x": 2}, "x")
    s.resolve(expiring.approval_id, True)
    now[0] += 61  # past the 60 s TTL
    assert s.peek_granted(expiring.action_hash) is None and expiring.status == ApprovalStatus.EXPIRED
    late = s.request("ses_1", "t", {"x": 3}, "x")
    now[0] += 61
    with pytest.raises(ApprovalError):
        s.resolve(late.approval_id, True)
    with pytest.raises(ApprovalError):
        s.resolve("apr_missing", True)


async def test_wait_returns_the_decision_and_silence_becomes_expiry():
    s = ApprovalStore(ttl_seconds=60)
    a = s.request("ses_1", "t", {"x": 1}, "x")
    asyncio.get_running_loop().call_later(0.05, s.resolve, a.approval_id, True)
    assert await s.wait(a.approval_id, 2) == ApprovalStatus.APPROVED
    b = s.request("ses_1", "t", {"x": 2}, "x")
    assert await s.wait(b.approval_id, 0.1) == ApprovalStatus.EXPIRED  # silence is a denial
    assert s.peek_granted(b.action_hash) is None
