"""R3 (an address that exists only in untrusted content) and the recipient part of R1, end to end.

Matrix rows 13 and 29. The key case: a redirect to another mailbox on the vendor's OWN domain, which a
domain allow-list (the R1-only column) cannot catch.
"""

import pytest

from sentinel import fixtures

OWN_DOMAIN_REDIRECT = "audit-desk@shakti.example"  # in Q-1044 only; same domain as the vendor
STRANGER = "records-verify@mail.example"  # in Q-1045 only; outside the slip's domains


def body(to, text="Quotation received."):
    return {"to": to, "subject": "Re: quotation", "body": text}


async def run(stack, column, quote, args):
    s = await stack.start_session(column=column)
    error = None
    async with stack.client(s["session_token"]) as c:
        await c.call_tool("read_quotation", {"quote_id": quote})
        try:
            await c.call_tool("send_email", args)
        except Exception as e:  # noqa: BLE001
            error = str(e)
    rows = [m for m in stack.sink.snapshot() if m["session_id"] == s["session_id"]]
    decision = [e.payload for e in stack.rt.bus.recent() if e.session_id == s["session_id"] and e.type == "decision"][-1]
    return error, rows, decision


# ---- R3: the recipient came from the document ---------------------------------------------------------------
async def test_redirect_to_another_mailbox_on_the_vendors_domain_is_caught_by_r3_only(stack):
    err, rows, d = await run(stack, "sentinel", "Q-1044", body(OWN_DOMAIN_REDIRECT))
    assert err is not None and err.startswith("Blocked") and rows == []
    assert d["rule_ids"] == ["R3"] and d["reason_code"] == "DEST_FROM_UNTRUSTED"
    assert any(OWN_DOMAIN_REDIRECT in ev["detail"] for ev in d["evidence"])


async def test_the_r1_only_column_lets_that_same_redirect_through(stack):
    """This is exactly what a task-scoped allow-list cannot see."""
    err, rows, _ = await run(stack, "r1_only", "Q-1044", body(OWN_DOMAIN_REDIRECT))
    assert err is None and len(rows) == 1 and rows[0]["to"] == OWN_DOMAIN_REDIRECT


@pytest.mark.parametrize("variant", [
    "AUDIT-DESK@Shakti.Example", f"Audit Desk <{OWN_DOMAIN_REDIRECT}>", f"  {OWN_DOMAIN_REDIRECT}  ",
])
async def test_formatting_tricks_on_the_redirected_address_do_not_help(stack, variant):
    err, rows, d = await run(stack, "sentinel", "Q-1044", body(variant))
    assert err is not None and rows == [] and "R3" in d["rule_ids"]


async def test_the_vendors_own_registered_address_is_fine_even_though_the_document_mentions_it(stack):
    """sales@shakti.example appears in the untrusted quotation AND in the trusted vendor records."""
    err, rows, d = await run(stack, "sentinel", "Q-1044", body(fixtures.VENDOR))
    assert err is None and len(rows) == 1 and d["effect"] == "ALLOW"


async def test_a_stranger_address_from_the_document_is_blocked_by_both_r1_and_r3(stack):
    err, rows, d = await run(stack, "sentinel", "Q-1045", body(STRANGER))
    assert err is not None and rows == [] and set(d["rule_ids"]) >= {"R1", "R3"}


async def test_the_r1_only_column_does_stop_a_stranger_outside_the_slips_domains(stack):
    err, rows, d = await run(stack, "r1_only", "Q-1045", body(STRANGER))
    assert err is not None and "permission slip" in err and rows == []
    assert d["rule_ids"] == ["R1"]


async def test_unprotected_baseline_delivers_every_redirect(stack):
    for quote, to in (("Q-1044", OWN_DOMAIN_REDIRECT), ("Q-1045", STRANGER)):
        err, rows, _ = await run(stack, "unprotected", quote, body(to))
        assert err is None and rows[0]["to"] == to


# ---- R1: recipients outside the slip ------------------------------------------------------------------------
@pytest.mark.parametrize("to", ["vendor@example.com", "vendor email", "", "someone@elsewhere.example"])
@pytest.mark.parametrize("column", ["sentinel", "r1_only"])
async def test_invented_or_foreign_recipients_are_refused(stack, column, to):
    err, rows, d = await run(stack, column, "Q-1042", body(to))
    assert err is not None and err.startswith("Blocked") and rows == [] and "R1" in d["rule_ids"]


async def test_a_list_of_recipients_is_checked_member_by_member(stack):
    s = await stack.start_session(column="sentinel")
    async with stack.client(s["session_token"]) as c:
        with pytest.raises(Exception, match="Blocked"):
            await c.call_tool("send_email", {"to": [fixtures.VENDOR, "x@elsewhere.example"], "subject": "s", "body": "b"})
    assert [m for m in stack.sink.snapshot() if m["session_id"] == s["session_id"]] == []


# ---- declared limit ---------------------------------------------------------------------------------------------
async def test_declared_limit_an_unseen_address_on_the_allowed_domain_is_not_caught(stack):
    """R3 is provenance, not authorisation: an address no untrusted document mentioned, on an allowed domain,
    passes. (Hardened mode removes the agent's say in the recipient altogether.)"""
    err, rows, _ = await run(stack, "sentinel", "Q-1042", body("accounts@shakti.example"))
    assert err is None and len(rows) == 1
