"""`up` must never say "Sentinel up" while its tool server is dead (a port already taken by another program, or by a leftover
Sentinel, made every tool call fail quietly in the background). Real sockets and real child processes, no mocks."""

import asyncio
import socket
import subprocess
import sys

import pytest

from sentinel.cli import api_port_default, check_ports, exposure_problem, port_in_use, wait_until_listening, watch_child


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture()
def listener():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    s.listen(5)
    yield s.getsockname()[1]
    s.close()


def test_a_port_with_a_listener_is_in_use_and_a_free_one_is_not(listener):
    assert port_in_use(listener) is True
    assert port_in_use(free_port()) is False


def test_a_bound_port_that_is_not_listening_yet_still_counts_as_in_use():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))  # held, not listening: connecting fails, but a second bind would too
    try:
        assert port_in_use(s.getsockname()[1]) is True
    finally:
        s.close()


def test_check_ports_passes_for_three_free_distinct_ports():
    check_ports({"API and console": (free_port(), "--api-port"), "gateway": (free_port(), "--gateway-port"),
                 "tool server": (free_port(), "--tools-port")})


def test_check_ports_names_the_busy_port_and_the_flag_that_changes_it(listener):
    with pytest.raises(SystemExit) as e:
        check_ports({"API and console": (free_port(), "--api-port"), "gateway": (free_port(), "--gateway-port"),
                     "tool server": (listener, "--tools-port")})
    msg = str(e.value)
    assert msg.startswith("Nothing was started.") and f"port {listener}" in msg and "tool server" in msg and "--tools-port" in msg
    assert "--api-port" not in msg  # only the real problem is reported


def test_check_ports_refuses_two_services_on_one_port():
    p = free_port()
    with pytest.raises(SystemExit) as e:
        check_ports({"API and console": (p, "--api-port"), "gateway": (p, "--gateway-port"), "tool server": (free_port(), "--tools-port")})
    assert "both set to port" in str(e.value)


async def test_a_child_that_exits_at_start_is_reported_not_waited_for():
    proc = subprocess.Popen([sys.executable, "-c", "import sys; sys.exit(3)"])
    with pytest.raises(SystemExit) as e:
        await wait_until_listening(free_port(), proc, "tool server", timeout=10)
    assert "stopped at start" in str(e.value) and "3" in str(e.value)


async def test_a_child_that_never_listens_times_out_with_a_clear_message():
    proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    try:
        with pytest.raises(SystemExit) as e:
            await wait_until_listening(free_port(), proc, "tool server", timeout=0.8)
        assert "did not start listening" in str(e.value)
    finally:
        proc.kill()


async def test_a_child_that_starts_listening_is_accepted():
    port = free_port()
    code = (f"import socket, time; s = socket.socket(); s.bind(('127.0.0.1', {port})); s.listen(5); time.sleep(30)")
    proc = subprocess.Popen([sys.executable, "-c", code])
    try:
        await wait_until_listening(port, proc, "tool server", timeout=15)
    finally:
        proc.kill()


async def test_the_watchdog_stops_sentinel_when_the_tool_server_dies_later():
    proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(0.5)"])
    with pytest.raises(SystemExit) as e:
        await asyncio.wait_for(watch_child(proc, "tool server"), timeout=10)
    assert "tools are gone" in str(e.value)


# ---- plan D1: running on a hosting platform ------------------------------------------------------------------------------------
def test_the_api_port_comes_from_the_platforms_port_variable_when_it_is_sane(monkeypatch):
    monkeypatch.delenv("PORT", raising=False)
    assert api_port_default() == 8000
    monkeypatch.setenv("PORT", "10000")
    assert api_port_default() == 10000
    for bad in ("", "abc", "0", "70000", "-5", "80 80"):
        monkeypatch.setenv("PORT", bad)
        assert api_port_default() == 8000, bad


@pytest.mark.parametrize("host", ["127.0.0.1", "localhost", "::1"])
def test_this_computer_needs_no_chosen_token(host):
    assert exposure_problem(host, None) is None and exposure_problem(host, "x") is None


@pytest.mark.parametrize("token", [None, "", "short", "a" * 23, "has space in it but is long enough!!", "token-with-a-fragment#and-more-chars", "x" * 23 + "+"])
def test_the_api_is_never_exposed_beyond_this_computer_without_a_strong_token_the_operator_chose(token):
    for host in ("0.0.0.0", "192.168.1.5", "example.com"):
        assert exposure_problem(host, token), (host, token)


def test_a_strong_url_safe_token_allows_exposure_and_the_message_does_not_repeat_a_token():
    good = "Abc_def-0123456789ABCDEFGH"
    assert exposure_problem("0.0.0.0", good) is None
    assert "SENTINEL_API_TOKEN" in exposure_problem("0.0.0.0", "short") and "short" not in exposure_problem("0.0.0.0", "short")


async def test_the_live_model_cap_stops_requests_before_they_are_sent(monkeypatch):
    import httpx

    from sentinel.agent import runner

    sent = []

    def handler(request: httpx.Request) -> httpx.Response:
        sent.append(1)
        return httpx.Response(200, json={"choices": [{"message": {"role": "assistant", "content": "ok"}}]})

    monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-test-key-not-real-000000000000")
    monkeypatch.setenv("SENTINEL_LIVE_MODEL_CAP", "2")
    monkeypatch.setattr(runner, "_LIVE_REQUESTS", 0)
    monkeypatch.setattr(runner, "load_env", lambda *a, **k: None)
    endpoint = runner.ModelEndpoint(provider="nvidia", model="m")
    monkeypatch.setattr(runner.ModelEndpoint, "_min_gap", property(lambda self: 0.0))
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        await endpoint.chat(client, [{"role": "user", "content": "a"}], [])
        await endpoint.chat(client, [{"role": "user", "content": "b"}], [])
        with pytest.raises(RuntimeError, match="live-model limit"):
            await endpoint.chat(client, [{"role": "user", "content": "c"}], [])
    assert len(sent) == 2  # the third request was never sent
    monkeypatch.delenv("SENTINEL_LIVE_MODEL_CAP")  # unset means no cap (a laptop)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        await endpoint.chat(client, [{"role": "user", "content": "d"}], [])
    assert len(sent) == 3

