"""Typed destinations (e-mail, URL host, file path) and how a slip's list covers them (core plan B2).

The URL and path tests are the security-relevant ones: a destination that two parsers read differently is how data is
smuggled out, so anything ambiguous must come back as junk (refused by R1), never as a guess."""

import pytest

from sentinel import destinations as d
from sentinel.contracts import SlipError, normalise_destination_entry


def test_email_behaviour_is_unchanged():
    assert d.keys_in("Shakti Sales <Sales@Shakti.example>") == (["sales@shakti.example"], [])
    assert d.keys_in(["a@x.example", "b@y.example"], "email") == (["a@x.example", "b@y.example"], [])
    assert d.keys_in("vendor email") == ([], ["vendor email"])


@pytest.mark.parametrize("url,host", [
    ("https://collector.example/upload?x=1", "host:collector.example"),
    ("HTTPS://Collector.Example:8443/x", "host:collector.example"),
    ("http://203.0.113.5/drop", "host:203.0.113.5"),
    ("https://a.b.collector.example/x", "host:a.b.collector.example"),
])
def test_a_url_yields_its_host_only(url, host):
    assert d.keys_in(url, "url") == ([host], [])


@pytest.mark.parametrize("bad", [
    "https://allowed.example@evil.example/",       # userinfo: browsers connect to evil.example
    "https://allowed.example\\@evil.example/",     # backslash: parsers disagree where the host ends
    "https://evil.example\n.allowed.example/",     # control character inside the host
    "https://exa mple.com/",                       # whitespace
    "ftp://files.example/x", "javascript:alert(1)", "file:///etc/passwd", "data:text/plain,hi",
    "//evil.example/x", "evil.example/x", "http://localhost/x", "https://[::1]/", "https://example.com:99999999/",
    "https://collector.example./x",                # a trailing dot names the same host to some parsers and not to others
    "", "   ",
])
def test_ambiguous_or_non_http_urls_are_junk_never_guessed(bad):
    keys, junk = d.keys_in(bad, "url")
    assert keys == [] and junk == [bad]


def test_a_list_of_urls_is_checked_member_by_member():
    keys, junk = d.keys_in(["https://ok.example/a", "https://x.example@evil.example/"], "url")
    assert keys == ["host:ok.example"] and junk == ["https://x.example@evil.example/"]


@pytest.mark.parametrize("raw,key", [
    ("/reports/q3.txt", "path:/reports/q3.txt"),
    ("reports//q3.txt", "path:/reports/q3.txt"),
    ("/a/./b", "path:/a/b"),
    ("\\reports\\q3.txt", "path:/reports/q3.txt"),
])
def test_paths_are_normalised(raw, key):
    assert d.keys_in(raw, "path") == ([key], [])


@pytest.mark.parametrize("bad", ["/reports/../etc/passwd", "..\\secret", "../x", "/a/b/..", "a\x00b", "", "a\nb"])
def test_a_path_that_climbs_or_holds_odd_characters_is_junk(bad):
    keys, junk = d.keys_in(bad, "path")
    assert keys == [] and junk == [bad]


def test_a_domain_covers_its_addresses_and_its_host_but_not_its_subdomains():
    allowed = ["corp.example"]
    assert d.allowed("anyone@corp.example", allowed) and d.allowed("host:corp.example", allowed)
    assert not d.allowed("anyone@evil.corp.example", allowed)
    assert not d.allowed("host:evil.corp.example", allowed)
    assert not d.allowed("host:corp.example.evil.example", allowed)
    assert not d.allowed("anyone@notcorp.example", allowed)


def test_a_full_address_covers_only_that_address():
    assert d.allowed("boss@corp.example", ["boss@corp.example"])
    assert not d.allowed("other@corp.example", ["boss@corp.example"])
    assert d.allowed("BOSS@Corp.Example".lower(), ["Boss@Corp.Example"])  # the slip's own entries are case-insensitive


def test_a_path_prefix_covers_that_folder_and_below_with_a_real_boundary():
    allowed = ["path:/out"]
    assert d.allowed("path:/out", allowed) and d.allowed("path:/out/a.txt", allowed) and d.allowed("path:/out/x/y", allowed)
    assert not d.allowed("path:/outside/a.txt", allowed) and not d.allowed("path:/", allowed)
    assert d.allowed("path:/anything/at/all", ["path:/"])


def test_the_three_kinds_never_cover_each_other():
    assert not d.allowed("path:/corp.example/x", ["corp.example"])
    assert not d.allowed("a@corp.example", ["path:/corp.example"])
    assert not d.allowed("host:corp.example", ["path:/corp.example"])
    assert not d.allowed("host:corp.example", [])


def test_r3_leaves_url_hosts_to_the_slips_allow_list_but_still_polices_e_mail_addresses():
    """A document that mentions the very host the officer allowed must not make that host unusable; an address that
    only a document mentioned is still refused."""
    from sentinel.models import ToolEntry
    from sentinel.rules import rule_r3

    common = dict(capability="send", resource_class="r", outbound=True, consequential=True, output_integrity="trusted",
                  output_confidentiality="internal")
    web = ToolEntry(name="http_post", destination_args=["url"], destination_kind="url", **common)
    mail = ToolEntry(name="send_email", destination_args=["to"], **common)
    assert rule_r3(None, web, ["host:ok.example"], {"host:ok.example": "read_document"}, frozenset()) is None
    blocked = rule_r3(None, mail, ["audit@shakti.example"], {"audit@shakti.example": "read_quotation"}, frozenset())
    assert blocked is not None and blocked.rule_id.value == "R3"


@pytest.mark.parametrize("raw,clean", [
    ("Corp.Example", "corp.example"), (" boss@corp.example ", "boss@corp.example"), ("path:/reports/", "path:/reports"),
    ("path:/a//b", "path:/a/b"),
])
def test_officer_entries_are_normalised(raw, clean):
    assert normalise_destination_entry(raw) == clean


@pytest.mark.parametrize("bad", ["*.corp.example", "*", "https://corp.example/x", "corp", "path:reports", "path:/a/../b",
                                 "a b.example", "", "corp.example/", "path:/a\\b", "path:/*"])
def test_vague_or_odd_officer_entries_are_refused(bad):
    with pytest.raises(SlipError, match="not a valid destination"):
        normalise_destination_entry(bad)
