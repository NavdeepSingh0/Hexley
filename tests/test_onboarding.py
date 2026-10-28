"""Tool onboarding (core plan B2): a tool nobody has classified is invisible to agents and refused by R1 until the officer
labels it. The officer's labels live in an overlay that can only ADD tools and can never change a built-in entry."""

import httpx
import pytest
import pytest_asyncio
import yaml

from sentinel.models import ToolEntry
from sentinel.registry import Registry, RegistryError, load_registry, save_overlay, suggest_classification
from sentinel.stack import running_stack

NEW_TOOL = "update_vendor_bank"  # an upstream tool we will treat as "new": forgotten from the registry in the fixture
LABELS = {"capability": "write", "outbound": False, "consequential": True, "output_integrity": "trusted",
          "output_confidentiality": "restricted", "requires_human_verification": True}


def forget(rt, name: str) -> None:
    """Make a tool look as if nobody had ever classified it."""
    rt.registry._tools.pop(name)
    rt.registry._base = frozenset(rt.registry._base - {name})


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def istack():
    async with running_stack() as s:
        forget(s.rt, NEW_TOOL)
        yield s


async def attempt(c, tool, args):
    try:
        await c.call_tool(tool, args)
    except Exception as e:  # noqa: BLE001
        return str(e)
    return None


# ---- suggestions ------------------------------------------------------------------------------------------------------
def test_a_sending_tool_is_suggested_as_outbound_with_its_destination_argument():
    s = suggest_classification("post_to_webhook", "Post a JSON body to a webhook URL", {"properties": {"url": {}, "body": {}}})
    assert s["capability"] == "send" and s["outbound"] and s["consequential"]
    assert s["destination_args"] == ["url"] and s["destination_kind"] == "url"


def test_a_database_reader_is_suggested_as_confidential_and_fingerprinted():
    """The NAME leads: the description's "Run a SQL query" must not turn a query tool into a writer."""
    s = suggest_classification("query_customers", "Run a SQL query on the customer database", {"properties": {"sql": {}}})
    assert s["capability"] == "read" and not s["outbound"] and not s["consequential"]
    assert s["output_confidentiality"] == "restricted" and s["fingerprint_fields"] == ["all"]
    assert any("free-form SQL" in r for r in s["reasons"])  # but it tells the officer what to check


def test_a_tool_that_takes_a_program_is_flagged_as_able_to_do_more_than_its_name_says():
    s = suggest_classification("helper", "Does a thing", {"properties": {"script": {}}})
    assert s["capability"] == "write" and s["consequential"] and any("free-form command" in r for r in s["reasons"])


def test_a_deletion_tool_is_suggested_as_consequential():
    s = suggest_classification("delete_records", "Delete all rows from a table", {"properties": {"table": {}}})
    assert s["capability"] == "write" and s["consequential"] and not s["outbound"]


def test_a_writer_or_runner_is_suggested_as_consequential_and_a_reader_of_content_as_untrusted():
    w = suggest_classification("run_command", "Execute a shell command", {"properties": {"command": {}}})
    assert w["capability"] == "write" and w["consequential"]
    r = suggest_classification("read_document", "Read a PDF from the reports folder", {"properties": {"path": {}}})
    assert r["capability"] == "read" and r["output_integrity"] == "untrusted"


def test_an_outbound_looking_tool_without_a_clear_destination_says_so():
    s = suggest_classification("send_report", "Send the report", {"properties": {"report": {}}})
    assert s["outbound"] and s["destination_args"] == [] and any("no argument clearly names the destination" in r for r in s["reasons"])


# ---- the overlay -----------------------------------------------------------------------------------------------------
def test_the_overlay_can_never_shadow_or_weaken_a_built_in_entry(tmp_path):
    overlay = tmp_path / "registry.local.yaml"
    overlay.write_text(yaml.safe_dump({"tools": {"send_email": {**LABELS, "resource_class": "x", "outbound": False}}}), encoding="utf-8")
    with pytest.raises(RegistryError, match="built-in"):
        load_registry(overlay=overlay)


@pytest.mark.parametrize("extra", [{"local": True}, {"egress_template": "quote_ack_v1"}])
def test_the_overlay_cannot_make_a_tool_gateway_local_or_give_it_an_egress_template(tmp_path, extra):
    overlay = tmp_path / "o.yaml"
    overlay.write_text(yaml.safe_dump({"tools": {"new_tool": {**LABELS, "resource_class": "x", **extra}}}), encoding="utf-8")
    with pytest.raises(RegistryError):
        load_registry(overlay=overlay)


def test_a_damaged_overlay_stops_startup_instead_of_being_half_applied(tmp_path):
    overlay = tmp_path / "o.yaml"
    overlay.write_text("tools: [this is not a mapping", encoding="utf-8")
    with pytest.raises(RegistryError, match="overlay"):
        load_registry(overlay=overlay)
    overlay.write_text(yaml.safe_dump({"tools": {"t": {"capability": "write"}}}), encoding="utf-8")  # fields missing
    with pytest.raises(RegistryError):
        load_registry(overlay=overlay)


def test_the_overlay_round_trips_and_a_missing_one_is_fine(tmp_path):
    overlay = tmp_path / "o.yaml"
    assert load_registry(overlay=overlay).names() == load_registry().names()
    reg = load_registry()
    reg.add(ToolEntry(name="new_tool", resource_class="docs", **{**LABELS, "requires_human_verification": False}))
    save_overlay(reg, overlay)
    again = load_registry(overlay=overlay)
    assert again.get("new_tool") == reg.get("new_tool") and again.is_known("new_tool") and not again.is_builtin("new_tool")
    assert again.is_builtin("send_email")


def test_a_registry_refuses_to_replace_a_builtin_entry():
    reg = load_registry()
    with pytest.raises(RegistryError):
        reg.add(ToolEntry(name="send_email", resource_class="x", **LABELS))


# ---- through the API and the gateway ------------------------------------------------------------------------------------
async def test_an_unclassified_tool_is_listed_with_a_suggestion_and_invisible_to_agents(istack):
    async with istack.api() as api:
        v = (await api.get("/api/v1/tools")).json()
    tool = next(t for t in v["tools"] if t["name"] == NEW_TOOL)
    # delete_records is offered by the tool server and deliberately never classified: it must stay blocked throughout
    assert {t["name"] for t in v["tools"] if not t["classified"]} == {NEW_TOOL, "delete_records"} and v["unclassified"] == 2
    assert not tool["classified"] and tool["labels"] is None
    assert tool["suggested"]["capability"] == "write" and tool["suggested"]["consequential"]
    assert next(t for t in v["tools"] if t["name"] == "send_email")["builtin"] is True
    # a slip that would allow it (vendor_maintenance) still cannot use it: hidden from the list, refused by R1
    s = await istack.start_session(template="vendor_maintenance")
    async with istack.client(s["session_token"]) as c:
        assert NEW_TOOL not in {t.name for t in await c.list_tools()}
        err = await attempt(c, NEW_TOOL, {"vendor": "shakti", "account_number": "111-222-333"})
    assert err is not None and err.startswith("Blocked") and "not a registered tool" in err
    last = [e.payload for e in istack.rt.bus.recent() if e.session_id == s["session_id"] and e.type == "decision"][-1]
    assert last["rule_ids"] == ["R1"] and last["reason_code"] == "NOT_IN_REGISTRY"


async def test_the_slip_builder_refuses_a_tool_nobody_classified(istack):
    async with istack.api() as api:
        r = await api.post("/api/v1/slips", json={"objective": "Change a vendor's bank details", "allowed_tools": [NEW_TOOL]})
    assert r.status_code == 422 and "not a classified tool" in r.json()["detail"]


@pytest.mark.parametrize("over,status,message", [
    ({"fingerprint_fields": ["nonsense"]}, 422, "Unknown fingerprint field"),
    ({"outbound": True}, 422, "must say which argument names the destination"),
    ({"outbound": True, "destination_args": ["nope"]}, 422, "has no argument called nope"),
    ({"local": True}, 422, None),  # not accepted at all: a classification labels risk, nothing more
    ({"egress_template": "quote_ack_v1"}, 422, None),
])
async def test_bad_classifications_are_refused(istack, over, status, message):
    async with istack.api() as api:
        r = await api.post(f"/api/v1/tools/{NEW_TOOL}/classify", json={**LABELS, **over})
    assert r.status_code == status
    if message:
        assert message in r.json()["detail"]
    assert not istack.rt.registry.is_known(NEW_TOOL)  # nothing was half-applied


async def test_a_builtin_tool_cannot_be_reclassified_and_a_phantom_tool_is_a_404(istack):
    async with istack.api() as api:
        weaken = {**LABELS, "capability": "read", "consequential": False, "outbound": False}
        assert (await api.post("/api/v1/tools/send_email/classify", json=weaken)).status_code == 409
        assert (await api.post("/api/v1/tools/does_not_exist/classify", json=LABELS)).status_code == 404
    assert istack.rt.registry.get("send_email").outbound  # still the built-in label


async def test_classification_needs_the_api_token(istack):
    async with httpx.AsyncClient(base_url=istack.api_url) as anon:
        assert (await anon.post(f"/api/v1/tools/{NEW_TOOL}/classify", json=LABELS)).status_code == 401
        assert (await anon.get("/api/v1/tools")).status_code == 401


async def test_classifying_a_tool_makes_it_usable_is_audited_and_survives_a_restart(istack):
    async with istack.api() as api:
        r = await api.post(f"/api/v1/tools/{NEW_TOOL}/classify", json=LABELS)
        assert r.status_code == 200 and r.json()["classified"]
        listed = (await api.get("/api/v1/tools")).json()
        assert {t["name"] for t in listed["tools"] if not t["classified"]} == {"delete_records"}  # the dangerous one stays out
        assert next(t for t in listed["tools"] if t["name"] == NEW_TOOL)["classified"]
        refused = await api.post("/api/v1/slips", json={"objective": "Tidy the database tables", "allowed_tools": ["delete_records"]})
        assert refused.status_code == 422 and "not a classified tool" in refused.json()["detail"]
        slip = (await api.post("/api/v1/slips", json={"objective": "Change a vendor's bank details after approval",
                                                      "allowed_tools": [NEW_TOOL], "confirm": True})).json()
    async with istack.client(slip["header_value"].removeprefix("Bearer ")) as c:
        assert [t.name for t in await c.list_tools()] == [NEW_TOOL]
    # written to the signed audit log, with the labels the officer chose
    rec = [r for r in istack.rt.audit.export_lines().splitlines() if '"registry.classified"' in r]
    assert len(rec) == 1 and NEW_TOOL in rec[0]
    assert istack.rt.audit.verify().ok
    # and saved: the overlay file holds exactly the labels the officer chose, and they validate as a registry entry again.
    # (A fresh load_registry would rightly refuse this file here: in this test only the LIVE registry pretends the tool is
    # new, while the built-in file still lists it, and an overlay may never shadow a built-in entry.)
    saved = yaml.safe_load(istack.rt.registry_overlay.read_text(encoding="utf-8"))["tools"][NEW_TOOL]
    entry = ToolEntry(name=NEW_TOOL, **saved)
    assert entry.requires_human_verification and entry.consequential and not entry.local and entry.egress_template is None
    assert isinstance(istack.rt.registry, Registry) and istack.rt.registry.get(NEW_TOOL) == entry
