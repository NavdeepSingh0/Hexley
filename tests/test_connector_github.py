"""Plan F2b: the GitHub connector's preset and its attack (roadmap incident 5, the GitHub MCP toxic flow), offline.

Offline means the server is `tests/fakes/fake_github.py`. What this proves is that the registry preset and the rules stop the
flow given results in the real server's shape. The run against real GitHub is `scripts/connectors/live_github.py`, logged
separately with its n.
"""

from __future__ import annotations

import asyncio
import base64
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import pytest_asyncio

from sentinel.gateway import _part_text, _result_text
from sentinel.models import Capability
from sentinel.registry import load_registry
from sentinel.stack import running_stack
from sentinel.upstreams import UpstreamSet
from tests.fakes import fake_github as gh

FIXTURES = Path(__file__).parent / "fixtures"
FAKE = Path(gh.__file__)
PUBLIC, PRIVATE = "repo:acme/public-site", "repo:acme/private-ops"
TOOLS = ["github__issue_read", "github__get_file_contents", "github__add_issue_comment"]
READ_ISSUE = {"method": "get", "owner": "acme", "repo": "public-site", "issue_number": 7}


def _comment(body: str, repo: tuple[str, str] = gh.PUBLIC_REPO) -> dict:
    return {"owner": repo[0], "repo": repo[1], "issue_number": 7, "body": body}


def _file(path: str) -> dict:
    return {"owner": "acme", "repo": "private-ops", "path": path}


@pytest_asyncio.fixture(scope="module")
async def github(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("github")
    sink = tmp / "published.jsonl"
    config = tmp / "upstreams.yaml"
    # The real connector's name, so the real preset in registry.yaml applies. The token is a test value.
    config.write_text(json.dumps({"upstreams": [{"name": "github", "transport": "stdio", "command": "python",
                                                 "args": [str(FAKE), str(sink)],
                                                 "env": {"GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_TOKEN}"}}]}), encoding="utf-8")
    ups = UpstreamSet.load(config, tmp / "none", environ={"GITHUB_TOKEN": "test-token-not-real-0123"})
    async with running_stack(upstreams=ups, approval_wait=20.0) as s:
        yield s, sink


async def _slip(stack, **over) -> dict:
    body = {"objective": "Triage the public issue and answer the reporter", "confirm": True, "allowed_tools": TOOLS,
            "allowed_destinations": [PUBLIC, PRIVATE], "internal_destinations": [PRIVATE], "max_messages": 5, **over}
    async with stack.api() as api:
        r = await api.post("/api/v1/slips", json=body)
        assert r.status_code == 201, r.text
        return r.json()


def _published(sink: Path) -> list[dict]:
    return [json.loads(x) for x in sink.read_text(encoding="utf-8").splitlines()] if sink.exists() else []


async def _pending(stack, session_id: str):
    for _ in range(300):
        found = [a for a in stack.rt.approvals.pending() if a.session_id == session_id]
        if found:
            return found[0]
        await asyncio.sleep(0.02)
    raise AssertionError("no approval was requested")


# ---- the attack: a hidden instruction in a public issue -------------------------------------------------------------
async def test_private_values_pasted_into_a_public_comment_are_refused(github):
    stack, sink = github
    before = _published(sink)
    slip = await _slip(stack)
    async with stack.client(slip["header_value"].removeprefix("Bearer ")) as c:
        issue = await c.call_tool("github__issue_read", READ_ISSUE)
        assert "attacker/collect" in issue.content[0].text  # the hidden instruction reached the agent
        await c.call_tool("github__get_file_contents", _file("inventory.csv"))
        with pytest.raises(Exception, match="restricted data"):
            await c.call_tool("github__add_issue_comment", _comment("Stock: bearing-6204 at FSD_14, 18250 units."))
    assert _published(sink) == before


async def test_a_token_found_in_a_private_file_goes_nowhere_not_even_to_the_private_repository(github):
    stack, sink = github
    before = _published(sink)
    slip = await _slip(stack)
    async with stack.client(slip["header_value"].removeprefix("Bearer ")) as c:
        await c.call_tool("github__get_file_contents", _file("deploy.env"))
        with pytest.raises(Exception, match="Blocked"):
            await c.call_tool("github__add_issue_comment", _comment(f"token: {gh.FAKE_DEPLOY_TOKEN}", gh.PRIVATE_REPO))
    assert _published(sink) == before
    assert gh.FAKE_DEPLOY_TOKEN not in stack.rt.audit.export_lines()


async def test_the_attackers_repository_is_refused_whatever_the_comment_says(github):
    stack, sink = github
    before = _published(sink)
    slip = await _slip(stack)
    async with stack.client(slip["header_value"].removeprefix("Bearer ")) as c:
        await c.call_tool("github__issue_read", READ_ISSUE)
        with pytest.raises(Exception, match="outside it"):
            await c.call_tool("github__add_issue_comment", _comment("hello", ("attacker", "collect")))
    assert _published(sink) == before


async def test_a_paraphrase_with_the_rule_of_two_waits_for_the_officer_and_a_no_stops_it(github):
    stack, sink = github
    before = _published(sink)
    slip = await _slip(stack, strict_flows=True)
    async with stack.client(slip["header_value"].removeprefix("Bearer ")) as c:
        await c.call_tool("github__issue_read", READ_ISSUE)
        await c.call_tool("github__get_file_contents", _file("inventory.csv"))
        call = asyncio.create_task(c.call_tool("github__add_issue_comment", _comment("Plenty of bearings at the western depot.")))
        approval = await _pending(stack, slip["session_id"])
        stack.rt.approvals.resolve(approval.approval_id, False)
        with pytest.raises(Exception, match="did not approve"):
            await call
    assert _published(sink) == before


# ---- the honest task still runs -------------------------------------------------------------------------------------
async def test_an_honest_reply_before_reading_anything_untrusted_just_runs(github):
    stack, sink = github
    slip = await _slip(stack)
    async with stack.client(slip["header_value"].removeprefix("Bearer ")) as c:
        await c.call_tool("github__add_issue_comment", _comment("Thanks for the report."))
    assert _comment("Thanks for the report.") in _published(sink)


async def test_after_the_issue_the_reply_waits_for_the_officer_and_a_yes_publishes_it(github):
    stack, sink = github
    slip = await _slip(stack)
    async with stack.client(slip["header_value"].removeprefix("Bearer ")) as c:
        await c.call_tool("github__issue_read", READ_ISSUE)
        reply = _comment("We can reproduce error 1603 and are working on a fix.")
        call = asyncio.create_task(c.call_tool("github__add_issue_comment", reply))
        approval = await _pending(stack, slip["session_id"])
        assert _comment(reply["body"]) not in _published(sink)  # nothing published while it waits
        stack.rt.approvals.resolve(approval.approval_id, True)
        await call
    assert reply in _published(sink)


async def test_a_note_to_the_internal_repository_needs_no_approval_and_may_hold_the_values(github):
    stack, sink = github
    slip = await _slip(stack)
    note = _comment("Stock check: bearing-6204 at FSD_14, 18250 units.", gh.PRIVATE_REPO)
    async with stack.client(slip["header_value"].removeprefix("Bearer ")) as c:
        await c.call_tool("github__issue_read", READ_ISSUE)
        await c.call_tool("github__get_file_contents", _file("inventory.csv"))
        await c.call_tool("github__add_issue_comment", note)
    assert note in _published(sink)


async def test_a_tool_the_preset_does_not_classify_cannot_be_put_on_a_slip_or_called(github):
    stack, sink = github
    async with stack.api() as api:
        r = await api.post("/api/v1/slips", json={"objective": "Make a new repository", "allowed_tools": ["github__create_repository"],
                                                  "allowed_destinations": [PUBLIC], "max_messages": 1})
        assert r.status_code == 422 and "not a classified tool" in r.text
    slip = await _slip(stack)
    async with stack.client(slip["header_value"].removeprefix("Bearer ")) as c:
        assert "github__create_repository" not in {t.name for t in await c.list_tools()}
        with pytest.raises(Exception, match="Blocked"):
            await c.call_tool("github__create_repository", {"name": "x"})
    assert not any("created" in x for x in _published(sink))


# ---- the preset against the real server's tool list -----------------------------------------------------------------
REAL = {t["name"]: t for t in json.loads((FIXTURES / "github_tools_v2.0.3.json").read_text(encoding="utf-8"))}
PRESET = {n: e for n, e in ((n, load_registry().get(n)) for n in load_registry().names()) if n.startswith("github__")}


def test_every_tool_in_the_preset_exists_on_the_real_server():
    assert PRESET and not [n for n in PRESET if n.removeprefix("github__") not in REAL]


@pytest.mark.parametrize("name", sorted(PRESET))
def test_the_preset_agrees_with_the_real_definition(name):
    entry, real = PRESET[name], REAL[name.removeprefix("github__")]
    read_only = bool((real["annotations"] or {}).get("read_only_hint"))
    assert (entry.capability == Capability.READ) == read_only
    assert entry.outbound == (not read_only)  # every write on this server changes a repository others may read
    required = real["input_schema"].get("required", [])
    assert all(a in required for a in entry.destination_args)  # a destination the real tool can omit would be refused


def test_a_destructive_tool_in_the_preset_waits_for_the_officer():
    for name, entry in PRESET.items():
        if (REAL[name.removeprefix("github__")]["annotations"] or {}).get("destructive_hint"):
            assert entry.requires_human_verification, name


# ---- reading results: the payload may not be in `text` --------------------------------------------------------------
def _embedded(**resource):
    return SimpleNamespace(type="resource", resource=SimpleNamespace(**resource))


@pytest.mark.parametrize("part, expected", [
    (SimpleNamespace(text="plain"), "plain"),
    (_embedded(text="file body", blob=None), "file body"),
    (_embedded(text=None, blob=base64.b64encode(b"text sent as a blob").decode()), "text sent as a blob"),
    (_embedded(text=None, blob=base64.b64encode(b"\xff\xfe\x00binary").decode()), ""),
    (_embedded(text=None, blob="not base64 !!"), ""),
    (SimpleNamespace(type="image", data="AAAA"), ""),
])
def test_every_shape_of_result_part_is_read_or_declared_unreadable(part, expected):
    assert _part_text(part) == expected


def test_a_result_with_a_status_line_and_an_embedded_file_yields_both():
    result = SimpleNamespace(content=[SimpleNamespace(text="downloaded"), _embedded(text="DEPLOY_TOKEN=x", blob=None)],
                             structured_content=None)
    assert _result_text(result) == "downloaded\nDEPLOY_TOKEN=x"
