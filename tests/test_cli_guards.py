"""`up` must never say "Sentinel up" while its tool server is dead (a port already taken by another program, or by a leftover
Sentinel, made every tool call fail quietly in the background). Real sockets and real child processes, no mocks."""

import asyncio
import socket
import subprocess
import sys

import pytest

from sentinel.cli import check_ports, port_in_use, wait_until_listening, watch_child


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
