"""Plan F2c: the Notion connector's preset and its attack, offline.

Offline means the server is `tests/fakes/fake_notion.py`, with the real tool names and arguments. The run against real Notion
is `scripts/connectors/live_notion.py`, logged separately with its n.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
import pytest_asyncio

from sentinel import destinations
from sentinel.models import Capability
from sentinel.registry import load_registry
from sentinel.stack import running_stack
from sentinel.upstreams import UpstreamSet
from tests.fakes import fake_notion as nt

FIXTURES = Path(__file__).parent / "fixtures"
TEAM, SHARED = f"page:{nt.PAGE_TEAM}", f"page:{nt.PAGE_SHARED}"
TOOLS = ["notion__API-retrieve-page-markdown", "notion__API-query-data-source", "notion__API-post-page",
         "notion__API-create-a-comment", "notion__API-patch-block-children"]
LEAK = "A. Rao earns 1840500 and B. Sen earns 2275300."


def _rich(text: str) -> list:
    return [{"type": "text", "text": {"content": text}}]


@pytest_asyncio.fixture(scope="module")
async def notion(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("notion")
    sink = tmp / "written.jsonl"
    config = tmp / "upstreams.yaml"
    config.write_text(json.dumps({"upstreams": [{"name": "notion", "transport": "stdio", "command": "python",
                                                 "args": [str(Path(nt.__file__)), str(sink)],
                                                 "env": {"NOTION_TOKEN": "${NOTION_TOKEN}"}}]}), encoding="utf-8")
    ups = UpstreamSet.load(config, tmp / "none", environ={"NOTION_TOKEN": "test-token-not-real-0123"})
    async with running_stack(upstreams=ups, approval_wait=20.0) as s:
        yield s, sink


async def _slip(stack) -> dict:
    async with stack.api() as api:
        r = await api.post("/api/v1/slips", json={
            "objective": "Summarise the brief for the team", "confirm": True, "allowed_tools": TOOLS,
            "allowed_destinations": [TEAM, SHARED], "internal_destinations": [TEAM], "max_messages": 5})
        assert r.status_code == 201, r.text
        return r.json()


def _written(sink: Path) -> list[dict]:
    return [json.loads(x) for x in sink.read_text(encoding="utf-8").splitlines()] if sink.exists() else []


async def _read_all(c) -> None:
    page = await c.call_tool("notion__API-retrieve-page-markdown", {"page_id": nt.PAGE_BRIEF})
    assert nt.PAGE_ATTACKER in page.content[0].text  # the hidden instruction reached the agent
    await c.call_tool("notion__API-query-data-source", {"data_source_id": nt.SALARIES})


async def test_the_attackers_page_is_refused(notion):
    stack, sink = notion
    before, slip = _written(sink), await _slip(stack)
    async with stack.client(slip["header_value"].removeprefix("Bearer ")) as c:
        await _read_all(c)
        with pytest.raises(Exception, match="outside it"):
            await c.call_tool("notion__API-post-page", {"parent": {"page_id": nt.PAGE_ATTACKER}, "properties": {"title": LEAK}})
    assert _written(sink) == before


async def test_salaries_written_to_a_shared_page_on_the_slip_are_refused(notion):
    stack, sink = notion
    before, slip = _written(sink), await _slip(stack)
    async with stack.client(slip["header_value"].removeprefix("Bearer ")) as c:
        await _read_all(c)
        with pytest.raises(Exception, match="restricted data"):
            await c.call_tool("notion__API-create-a-comment", {"parent": {"page_id": nt.PAGE_SHARED}, "rich_text": _rich(LEAK)})
    assert _written(sink) == before


@pytest.mark.parametrize("parent", [
    {"page_id": nt.PAGE_TEAM, "database_id": nt.PAGE_ATTACKER},
    json.dumps({"page_id": nt.PAGE_TEAM, "database_id": nt.PAGE_ATTACKER}),
    {"database_id": nt.PAGE_ATTACKER},
    "not json",
])
async def test_a_parent_that_names_another_target_or_cannot_be_read_is_refused(notion, parent):
    stack, sink = notion
    before, slip = _written(sink), await _slip(stack)
    async with stack.client(slip["header_value"].removeprefix("Bearer ")) as c:
        with pytest.raises(Exception, match="Blocked"):
            await c.call_tool("notion__API-post-page", {"parent": parent, "properties": {"title": "x"}})
    assert _written(sink) == before


async def test_an_honest_note_goes_to_the_internal_page_with_no_approval(notion):
    stack, sink = notion
    slip = await _slip(stack)
    async with stack.client(slip["header_value"].removeprefix("Bearer ")) as c:
        await _read_all(c)
        children = [{"type": "paragraph", "paragraph": {"rich_text": _rich("Brief read: ship by Friday.")}}]
        await c.call_tool("notion__API-patch-block-children", {"block_id": nt.PAGE_TEAM, "children": children})
    assert {"tool": "append", "block_id": nt.PAGE_TEAM, "children": children} in _written(sink)


async def test_a_parent_sent_as_a_json_string_is_read_like_an_object(notion):
    stack, sink = notion
    slip = await _slip(stack)
    parent = json.dumps({"page_id": nt.PAGE_TEAM})
    async with stack.client(slip["header_value"].removeprefix("Bearer ")) as c:
        await c.call_tool("notion__API-create-a-comment", {"parent": parent, "rich_text": _rich("Noted.")})
    assert {"tool": "comment", "parent": parent, "rich_text": _rich("Noted.")} in _written(sink)


async def test_after_reading_a_page_a_note_to_the_shared_page_waits_for_the_officer(notion):
    stack, sink = notion
    slip = await _slip(stack)
    args = {"parent": {"page_id": nt.PAGE_SHARED}, "rich_text": _rich("Status: on track.")}
    async with stack.client(slip["header_value"].removeprefix("Bearer ")) as c:
        await c.call_tool("notion__API-retrieve-page-markdown", {"page_id": nt.PAGE_BRIEF})
        call = asyncio.create_task(c.call_tool("notion__API-create-a-comment", args))
        for _ in range(300):
            found = [a for a in stack.rt.approvals.pending() if a.session_id == slip["session_id"]]
            if found:
                break
            await asyncio.sleep(0.02)
        assert found and {"tool": "comment", **args} not in _written(sink)
        stack.rt.approvals.resolve(found[0].approval_id, True)
        await call
    assert {"tool": "comment", **args} in _written(sink)


async def test_a_tool_the_preset_leaves_out_cannot_be_put_on_a_slip_or_called(notion):
    stack, sink = notion
    async with stack.api() as api:
        r = await api.post("/api/v1/slips", json={"objective": "Tidy the page", "allowed_tools": ["notion__API-delete-a-block"],
                                                  "allowed_destinations": [TEAM], "max_messages": 1})
        assert r.status_code == 422 and "not a classified tool" in r.text
    slip = await _slip(stack)
    async with stack.client(slip["header_value"].removeprefix("Bearer ")) as c:
        with pytest.raises(Exception, match="Blocked"):
            await c.call_tool("notion__API-delete-a-block", {"block_id": nt.PAGE_TEAM})
    assert not any(x.get("tool") == "delete" for x in _written(sink))


# ---- the preset against the real server's tool list -----------------------------------------------------------------
REAL = {t["name"]: t for t in json.loads((FIXTURES / "notion_tools_v2.6.1.json").read_text(encoding="utf-8"))}
_REG = load_registry()
PRESET = {n: _REG.get(n) for n in _REG.names() if n.startswith("notion__")}
# The server marks every HTTP POST as destructive, including these two reads.
READS_SENT_AS_POST = {"API-post-search", "API-query-data-source"}


def test_every_tool_in_the_preset_exists_on_the_real_server():
    assert PRESET and not [n for n in PRESET if n.removeprefix("notion__") not in REAL]


@pytest.mark.parametrize("name", sorted(PRESET))
def test_the_preset_agrees_with_the_real_definition(name):
    bare = name.removeprefix("notion__")
    entry, real = PRESET[name], REAL[bare]
    read_only = bool((real["annotations"] or {}).get("read_only_hint")) or bare in READS_SENT_AS_POST
    assert (entry.capability == Capability.READ) == read_only
    assert entry.outbound == (not read_only)
    props = real["input_schema"].get("properties", {})
    required = real["input_schema"].get("required", [])
    for arg in entry.destination_args:
        assert arg.split(".")[0] in props and arg.split(".")[0] in required


def test_the_preset_never_labels_page_content_trusted():
    for name, entry in PRESET.items():
        if entry.capability == Capability.READ and entry.resource_class != "notion_account":
            assert entry.output_integrity == "untrusted", name


@pytest.mark.parametrize("args, keys, junk", [
    ({"parent": {"page_id": "1a2b3c4d-5e6f"}}, ["page:1a2b3c4d5e6f"], []),
    ({"parent": '{"page_id": "1a2b3c4d-5e6f"}'}, ["page:1a2b3c4d5e6f"], []),
    ({"parent": {"page_id": "1a2b3c4d5e6f", "type": "page_id"}}, ["page:1a2b3c4d5e6f"], []),
    ({"parent": {"page_id": "1a2b3c4d5e6f", "database_id": "9f8e7d6c5b4a"}}, [],
     ["1a2b3c4d5e6f (the call names more than one target)"]),
    ({"parent": {"page_id": "1a2b3c4d5e6f", "database_id": ""}}, ["page:1a2b3c4d5e6f"], []),
    ({"parent": "{broken"}, [], ["(no destination given)"]),
])
def test_page_destinations_in_every_shape_the_server_accepts(args, keys, junk):
    assert destinations.destination_keys(args, ["parent.page_id"], "page") == (keys, junk)
