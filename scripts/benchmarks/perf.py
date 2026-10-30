"""Speed of the decision, of the whole check, and of the gateway; and throughput with several sessions at once.

What this measures: a single machine, loopback, the mock tools, the signed audit log with its fsync on (Windows). It does not measure
a network, real tools, a model, or many machines. Numbers are for this computer on this day."""

from __future__ import annotations

import asyncio
import random
import time
from datetime import datetime, timezone

import httpx
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport
from fastmcp.server.providers.proxy import FastMCPProxy, ProxyClient

from common import API_TOKEN, DOWNSTREAM_TOKEN, save, summarise
from sentinel.engine import decide
from sentinel.models import AgentAction, Column
from sentinel.stack import free_port, running_stack, serve
from sentinel.tools.server import TOKEN_HEADER

N_ENGINE = 20000
N_HTTP = 600
N_GATEWAY = 300
SESSIONS, CALLS_EACH = 16, 60


async def new_slip(stack, **over) -> dict:
    body = {"objective": "Read the quotation and the stock and acknowledge to the vendor", "confirm": True, "max_messages": 50, "ttl_seconds": 3600,
            "allowed_tools": ["read_quotation", "query_stock", "send_email", "list_documents"],
            "allowed_destinations": ["corp.example"], "internal_destinations": ["manager@corp.example"], **over}
    async with stack.api() as api:
        r = await api.post("/api/v1/slips", json=body)
        assert r.status_code == 201, r.text
        return r.json()


def stock_text(rng: random.Random, rows: int = 50) -> str:
    return "\n".join(f"Depot FSD-{i:02d}: {rng.randint(100, 99999):,} units on hand, next dispatch 2026-11-{rng.randint(1, 28):02d}" for i in range(rows))


def micro(fn, n: int) -> list[float]:
    for _ in range(min(1000, n // 10)):
        fn()
    out = []
    for _ in range(n):
        t0 = time.perf_counter_ns()
        fn()
        out.append((time.perf_counter_ns() - t0) / 1000.0)  # microseconds
    return out


async def main() -> None:
    rng = random.Random(7)
    results: dict = {"what": "speed of Sentinel on one machine, loopback, mock tools, audit fsync on"}
    async with running_stack(API_TOKEN, DOWNSTREAM_TOKEN) as stack:
        rt = stack.rt
        slip = await new_slip(stack)
        session = rt.store.get(slip["session_id"])
        text = stock_text(rng)
        session.index.add(text, ["quantity", "depot_code", "dispatch_date"], source_ref="query_stock")
        restricted_value = f"{int(text.split(':')[1].split(' units')[0].replace(',', '')):,}"
        results["index"] = "50 rows of a stock register, 3 fingerprinted fields each (quantity, depot code, dispatch date)"

        def act(tool: str, args: dict) -> AgentAction:
            e = rt.registry.get(tool)
            return AgentAction(action_id="act_bench", ts=datetime.now(timezone.utc), session_id=session.session_id,
                               contract_id=session.contract.contract_id, column=Column.SENTINEL, tool=tool, capability=e.capability,
                               resource_class=e.resource_class, args=args, outbound=e.outbound)

        clean_body = "Dear vendor, we acknowledge receipt of your quotation and will respond after review. Regards, Procurement. " * 3
        cases = {
            "allowed read (no outbound)": act("read_quotation", {}),
            "allowed send to the officer's own address (scans the index)": act("send_email", {"to": "manager@corp.example", "subject": "s", "body": clean_body}),
            "allowed send to the vendor, clean body (scans the index)": act("send_email", {"to": "vendor@corp.example", "subject": "s", "body": clean_body}),
            "blocked: restricted value in the body (R2)": act("send_email", {"to": "vendor@corp.example", "subject": "s", "body": f"We have {restricted_value} units"}),
            "blocked: tool not on the slip (R1)": act("fetch_url", {"url": "https://attacker.example/x"}),
        }
        results["decision_only"] = {}
        for name, a in cases.items():
            d = decide(a, session, rt.registry)
            us = micro(lambda a=a: decide(a, session, rt.registry), N_ENGINE)
            results["decision_only"][name] = {"effect": str(d.effect), "rules": [str(r) for r in d.rule_ids], **summarise(us, "microseconds"),
                                              "decisions_per_second_single_thread": round(1e6 / (sum(us) / len(us)))}
            print(f"decision only | {name:<62} {str(d.effect):<6} p50 {results['decision_only'][name]['p50']:>8.1f} us  p99 {results['decision_only'][name]['p99']:>8.1f} us")

        # The cost of writing one signed, fsynced audit record (what every real decision pays before anything is forwarded).
        audit = []
        for _ in range(300):
            t0 = time.perf_counter_ns()
            await rt.audit.append("decision", session_id=session.session_id, payload={"bench": True})
            audit.append((time.perf_counter_ns() - t0) / 1e6)
        results["one_audit_record"] = summarise(audit, "milliseconds")
        print(f"one signed audit record, fsynced              p50 {results['one_audit_record']['p50']:.2f} ms  p99 {results['one_audit_record']['p99']:.2f} ms")

        # The whole check over HTTP (token check, decision, audit record, events), the way a client's hook calls it.
        lat = []
        async with httpx.AsyncClient(base_url=stack.api_url, headers={"Authorization": slip["header_value"]}, timeout=30) as c:
            for i in range(50):  # warm-up
                await c.post("/api/v1/check/call", json={"tool_name": "read_quotation", "tool_input": {}, "tool_use_id": f"w{i}"})
            for i in range(N_HTTP):
                t0 = time.perf_counter_ns()
                r = await c.post("/api/v1/check/call", json={"tool_name": "read_quotation", "tool_input": {}, "tool_use_id": f"u{i}"})
                lat.append((time.perf_counter_ns() - t0) / 1e6)
                assert r.json()["effect"] == "ALLOW"
        results["whole_check_over_http"] = summarise(lat, "milliseconds")
        print(f"whole check over HTTP (hook route)            p50 {results['whole_check_over_http']['p50']:.2f} ms  p99 {results['whole_check_over_http']['p99']:.2f} ms")

        # What the gateway adds to a tool call: the same call through Sentinel's gateway and straight to the tool server.
        gslip = await new_slip(stack)
        token = gslip["header_value"].removeprefix("Bearer ")
        direct_t = StreamableHttpTransport(stack.tools_url, headers={TOKEN_HEADER: rt.downstream_token})
        via, direct = [], []
        async with stack.client(token) as g, Client(direct_t) as d:
            for _ in range(30):
                await g.call_tool("list_documents", {"folder": "reports"})
                await d.call_tool("list_documents", {"folder": "reports"})
            for _ in range(N_GATEWAY):
                t0 = time.perf_counter_ns()
                await g.call_tool("list_documents", {"folder": "reports"})
                via.append((time.perf_counter_ns() - t0) / 1e6)
                t0 = time.perf_counter_ns()
                await d.call_tool("list_documents", {"folder": "reports"})
                direct.append((time.perf_counter_ns() - t0) / 1e6)
        # The same proxy library with NO Sentinel in it: shows what is the library's own cost and what is Sentinel's.
        bare_port = free_port()
        bare_app = FastMCPProxy(client_factory=lambda: ProxyClient(StreamableHttpTransport(
            stack.tools_url, headers={TOKEN_HEADER: rt.downstream_token}), forward_incoming_headers=False), name="bare").http_app()
        bare_server, bare_task = await serve(bare_app, bare_port)
        bare = []
        try:
            async with Client(StreamableHttpTransport(f"http://127.0.0.1:{bare_port}/mcp")) as b:
                for _ in range(30):
                    await b.call_tool("list_documents", {"folder": "reports"})
                for _ in range(N_GATEWAY):
                    t0 = time.perf_counter_ns()
                    await b.call_tool("list_documents", {"folder": "reports"})
                    bare.append((time.perf_counter_ns() - t0) / 1e6)
        finally:
            bare_server.should_exit = True
            await asyncio.gather(bare_task, return_exceptions=True)
        results["same_proxy_library_without_sentinel"] = summarise(bare, "milliseconds")
        results["tool_call_through_the_gateway"] = summarise(via, "milliseconds")
        results["same_call_straight_to_the_tool_server"] = summarise(direct, "milliseconds")
        results["added_by_the_proxy_library_alone_at_p50_ms"] = round(results["same_proxy_library_without_sentinel"]["p50"] - results["same_call_straight_to_the_tool_server"]["p50"], 3)
        results["added_by_sentinel_on_top_of_the_proxy_at_p50_ms"] = round(results["tool_call_through_the_gateway"]["p50"] - results["same_proxy_library_without_sentinel"]["p50"], 3)
        results["added_in_total_at_p50_ms"] = round(results["tool_call_through_the_gateway"]["p50"] - results["same_call_straight_to_the_tool_server"]["p50"], 3)
        print(f"straight to the tool server p50 {results['same_call_straight_to_the_tool_server']['p50']:.1f} ms | through the bare proxy library "
              f"{results['same_proxy_library_without_sentinel']['p50']:.1f} ms | through Sentinel's gateway {results['tool_call_through_the_gateway']['p50']:.1f} ms")
        print(f"  the proxy library alone adds {results['added_by_the_proxy_library_alone_at_p50_ms']:.1f} ms; Sentinel adds {results['added_by_sentinel_on_top_of_the_proxy_at_p50_ms']:.1f} ms on top of it")

        # Several sessions at once.
        slips = [await new_slip(stack) for _ in range(SESSIONS)]
        lat2: list[float] = []
        first_calls: list[float] = []  # the first call of each session, reported on its own: all sessions start at the same instant

        async def worker(s: dict) -> None:
            async with httpx.AsyncClient(base_url=stack.api_url, headers={"Authorization": s["header_value"]}, timeout=60) as c:
                for i in range(CALLS_EACH):
                    t0 = time.perf_counter_ns()
                    r = await c.post("/api/v1/check/call", json={"tool_name": "read_quotation", "tool_input": {}, "tool_use_id": f"c{i}"})
                    (first_calls if i == 0 else lat2).append((time.perf_counter_ns() - t0) / 1e6)
                    assert r.status_code == 200

        t0 = time.perf_counter()
        await asyncio.gather(*(worker(s) for s in slips))
        wall = time.perf_counter() - t0
        results["concurrent"] = {"sessions": SESSIONS, "calls_each": CALLS_EACH, "wall_seconds": round(wall, 2),
                                 "checks_per_second": round(SESSIONS * CALLS_EACH / wall, 1), "steady_state_after_first_call": summarise(lat2, "milliseconds"),
                                 "first_call_of_each_session_when_all_start_at_once": summarise(first_calls, "milliseconds")}
        c = results["concurrent"]
        print(f"{SESSIONS} sessions at once: {c['checks_per_second']} checks/s; after each session's first call p50 {c['steady_state_after_first_call']['p50']:.0f} ms, "
              f"p99 {c['steady_state_after_first_call']['p99']:.0f} ms; the first calls took p50 {c['first_call_of_each_session_when_all_start_at_once']['p50']:.0f} ms, "
              f"max {c['first_call_of_each_session_when_all_start_at_once']['max']:.0f} ms")
    print("saved", save("perf", results))


if __name__ == "__main__":
    asyncio.run(main())
