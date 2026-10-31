"""What the team's five test documents found (scripts/eval/connector_fields.py, 31 Oct 2026). The documents stay out of the repository; these values have
the same shapes and are put together here, so nothing in this file looks like a live credential to a scanner.
"""

from __future__ import annotations

import base64

import httpx
import pytest
import pytest_asyncio

from sentinel.destinations import origin_key
from sentinel.matcher import FingerprintIndex
from sentinel.secret_scan import SecretIndex, find_secrets
from sentinel.stack import running_stack
from sentinel.unwrap import with_decoded

GH_TOKEN = "ghp" + "_" + "Ab3" * 12  # 36 characters after the prefix would be real; teammates' samples are often a character short
SHORT_GH = "ghp" + "_" + "Ab3" * 11 + "Ab"
NOTION = "ntn" + "_" + "Xy7" * 12
CARD = "4111 " + "1111 " + "1111 " + "1111"
TABLE = f"""Service inventory
ACCESS_TOKEN
svc_inv_{'7c4218e9' * 2}
DB_PASSWORD
inv_prod_2026_qa_4491
SIGNING_KEY
{'9c21a771' * 2}
Workspace access token {NOTION}
Payment card number {CARD}
DB_NAME
warehouse_prod
ARTIFACT_BUCKET
s3://af-prod-inventory-eu1
Token limit
4000
Password policy
Strong
Access token
expires
"""


def _found(text: str) -> set[str]:
    return {s.value for s in find_secrets(text)}


@pytest.mark.parametrize("value", [f"svc_inv_{'7c4218e9' * 2}", "inv_prod_2026_qa_4491", "9c21a771" * 2, NOTION, CARD])
def test_a_secret_in_a_table_or_pdf_is_found_with_only_space_or_a_line_after_its_name(value):
    assert value in _found(TABLE)


@pytest.mark.parametrize("text", ["Token limit\n4000", "Password policy\nStrong", "Access token\nexpires soon", "api key rotation is due next week"])
def test_a_name_followed_by_an_ordinary_word_or_number_is_not_a_secret(text):
    assert _found(text) == set()


def test_a_github_token_a_character_short_of_the_documented_length_is_still_one():
    assert SHORT_GH in _found(f"found {SHORT_GH} in the issue") and GH_TOKEN in _found(GH_TOKEN)


def test_a_payment_card_needs_a_valid_check_digit():
    assert CARD in _found(f"card {CARD} on file")
    assert _found("order 4111 1111 1111 1112 shipped") == set()


@pytest.mark.parametrize("write", [
    lambda v: v, lambda v: v.upper(), lambda v: v.replace("_", ""), lambda v: "-".join(v[i:i + 2] for i in range(0, len(v), 2)),
    lambda v: v[::-1], lambda v: base64.b64encode(v.encode()).decode(), lambda v: v.encode().hex(),
])
def test_a_found_secret_is_recognised_however_it_is_rewritten(write):
    index = SecretIndex()
    index.add(f"Workspace access token {NOTION}", "notion.notion-fetch")
    assert index.scan_text(f"here it is: {write(NOTION)}")
    assert not index.scan_text("nothing of the kind here")


def test_with_decoded_leaves_plain_text_alone_and_unwraps_only_what_decodes_to_text():
    assert with_decoded("A plain sentence with nothing wrapped.") == "A plain sentence with nothing wrapped."
    assert "secret words" in with_decoded(base64.b64encode(b"secret words").decode())
    assert with_decoded("deadbeefdeadbeef") == "deadbeefdeadbeef"  # hex that is not text


@pytest.mark.parametrize("name", ["warehouse_prod", "svc_inventory_rw", "s3://af-prod-inventory-eu1", "src/supplier/retry.ts"])
def test_a_machine_name_read_from_a_restricted_source_is_recognised(name):
    index = FingerprintIndex()
    index.add(f"Value {name} end", ["all"], source_ref="t")
    assert index.scan_text(f"It is {name}.")


@pytest.mark.parametrize("words", ["well-known", "follow-up", "read/write", "and/or", "up-to-date"])
def test_ordinary_hyphenated_words_are_not_machine_names(words):
    index = FingerprintIndex()
    index.add(f"A {words} note", ["id"], source_ref="t")
    assert not index.entries


@pytest.mark.parametrize("args, key", [
    ({"owner": "Acme", "repo": "Site"}, "repo:acme/site"), ({"channel_id": "C0AB"}, "channel:c0ab"), ({"page_id": "12345678-abcd"}, "page:12345678abcd"),
    ({"query": "x"}, None), ({}, None), (None, None),
])
def test_where_a_read_came_from(args, key):
    assert origin_key(args) == key


@pytest_asyncio.fixture(scope="module")
async def stack():
    async with running_stack(approval_wait=0.1) as s:
        yield s


PUBLIC, PRIVATE = "repo:acme/public", "repo:acme/private"


async def _session(stack):
    async with stack.api() as api:
        r = await api.post("/api/v1/slips", json={"objective": "Answer the issue", "confirm": True, "allowed_tools": ["github.issue_read", "github.add_issue_comment"], "unseen_context": True,
                                                  "strict_flows": True, "allowed_destinations": [PUBLIC, PRIVATE], "internal_destinations": [PRIVATE], "max_messages": 5, "freeze_after": 10})
        assert r.status_code == 201, r.text
    return httpx.AsyncClient(base_url=stack.api_url, headers={"Authorization": r.json()["header_value"]}, timeout=30)


async def _read_issue(c, text: str) -> None:
    tool = "mcp__github__issue_read"
    first = await c.post("/api/v1/check/call", json={"tool_name": tool, "tool_input": {"owner": "acme", "repo": "public", "issue_number": 1}, "tool_use_id": "r1", "wait_s": 0})
    assert first.json()["effect"] == "ALLOW"
    await c.post("/api/v1/check/result", json={"tool_name": tool, "tool_use_id": "r1", "tool_response": text})


async def _comment(c, repo: str, body: str) -> dict:
    r = await c.post("/api/v1/check/call", json={"tool_name": "mcp__github__add_issue_comment", "wait_s": 0,
                                                 "tool_input": {"owner": "acme", "repo": repo, "issue_number": 1, "body": body}})
    return r.json()


async def test_a_github_issue_is_now_read_as_restricted_so_its_values_are_recognised_elsewhere(stack):
    async with await _session(stack) as c:
        await _read_issue(c, "Customer account C-19027, contract CN-2026-4418, reference fixtures/retry-case-17.json")
        reply = await _comment(c, "other", "x")  # a repository the slip does not name
        assert reply["effect"] == "BLOCK" and "R1" in reply["rule_ids"]


async def test_a_reply_may_quote_the_issue_back_to_where_it_came_from(stack):
    """Found when the fix first ran: a reply mentioning the reporter's own error code was refused. It waits for the officer, as any reply after untrusted text."""
    async with await _session(stack) as c:
        await _read_issue(c, "The build fails with error 16037 in CN-2026-4418.")
        reply = await _comment(c, "public", "We can reproduce error 16037 in CN-2026-4418.")
        assert reply["effect"] == "ASK" and "R2" not in reply["rule_ids"]


async def test_a_value_read_elsewhere_is_still_refused_on_that_same_repository(stack):
    async with await _session(stack) as c:
        tool = "mcp__github__issue_read"
        await c.post("/api/v1/check/call", json={"tool_name": tool, "tool_input": {"owner": "acme", "repo": "private", "issue_number": 2}, "tool_use_id": "r2", "wait_s": 0})
        await c.post("/api/v1/check/result", json={"tool_name": tool, "tool_use_id": "r2", "tool_response": "Contract CN-2026-9999 is confidential."})
        reply = await _comment(c, "public", "Contract CN-2026-9999.")
        assert reply["effect"] == "BLOCK" and "R2" in reply["rule_ids"]


async def test_a_credential_never_goes_back_even_to_where_it_came_from_or_to_an_internal_place(stack):
    async with await _session(stack) as c:
        await _read_issue(c, f"Someone pasted {SHORT_GH} here.")
        for repo in ("public", "private"):
            reply = await _comment(c, repo, f"Is {SHORT_GH} yours?")
            assert reply["effect"] == "BLOCK" and "R2" in reply["rule_ids"], repo
