# Sentinel

**The AI can only do the job you gave it.**

Sentinel is an MCP gateway that sits between an AI agent and its tools. It checks every action against the task the officer approved, where the data came from, and where it is going, and blocks what the task never asked for. No LLM makes any security decision.

Team 404 Disruptors · Zinnovatio 4.0

## Status (updated each milestone; last: M1 done, M2 in progress: matcher and R2 built)

This table says what exists today, not what the architecture describes. "Tested" means automated tests cover the listed behaviour, not that the component is comprehensively secure.

| Component | Status | Notes |
|---|---|---|
| MCP gateway (proxy, per-call checks) | **Built, tested** | R1 on every call; agent headers never forwarded; fail-closed `decide()` |
| Session tokens (EdDSA, bound to the confirmed slip) | **Built, tested** | Forged `alg: none` and key-confusion tokens rejected; revocation on freeze |
| Permission slip, officer confirmation | **Built, tested** (API) | No console screen yet |
| Rule R1 (action must be in the slip and registry) | **Built, tested** | |
| Value matcher and rule R2 (restricted values must not leave the building) | **Built, tested** | Recognises the representations in `docs/ADVERSARIAL_TESTS.md`; paraphrase is a declared gap. With a real model: unprotected and R1-only columns delivered the stock data; in the Sentinel column the first (leaking) email was blocked and a clean acknowledgement was then sent. One recorded run per column, not a rate yet |
| Rules R3-R6 (destination provenance, approval, budgets, freeze) | **Planned (M2)** | |
| Structured egress (hardened mode) | **Planned (M2)** | Slip templates validate at startup; nothing enforces them yet |
| Signed, hash-chained audit log | **Planned (M2)** | |
| Mock tool server, mail sink (measures what was delivered) | **Built, tested** | |
| Live events (WebSocket) | **Built, tested** | |
| Agent runner (OpenAI-compatible, Ollama or NVIDIA) | **Built**, smoke-tested | Not covered by unit tests |
| Console UI, phone approval, replay | **Planned (M3-M4)** | |
| API authentication | **Demo-grade** | One static bearer token; not production identity management |

Measured model results (matched trials, six models) are in [docs/spikes/M0-results.md](docs/spikes/M0-results.md). They describe one task, one quotation and four injection texts, not prompt injection in general.

## Docs
- [docs/MVP.md](docs/MVP.md): what we build and present (source of truth)
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md): layout, interfaces, build order
- [docs/ADVERSARIAL_TESTS.md](docs/ADVERSARIAL_TESTS.md): attack matrix that becomes test oracles
- [docs/spikes/M0-results.md](docs/spikes/M0-results.md): measured spike results

## Setup
```
python -m pip install --user uv
python -m uv sync
python -m uv run pytest
```

All demo data is synthetic. Domains use `.example`.
