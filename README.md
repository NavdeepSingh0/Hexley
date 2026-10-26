# Sentinel

**The AI can only do the job you gave it.**

Sentinel is an MCP gateway that sits between an AI agent and its tools. It checks every action against the task the officer approved, where the data came from, and where it is going, and blocks what the task never asked for. No LLM makes any security decision.

Team 404 Disruptors · Zinnovatio 4.0

## Status (updated each milestone; last: M1 done, M2 enforcement complete: matcher, R1-R6, audit log, approvals and hardened mode built; the runs API, evaluation harness and console remain)

This table says what exists today, not what the architecture describes. "Tested" means automated tests cover the listed behaviour, not that the component is comprehensively secure.

| Component | Status | Notes |
|---|---|---|
| MCP gateway (proxy, per-call checks) | **Built, tested** | R1 on every call; agent headers never forwarded; fail-closed `decide()` |
| Session tokens (EdDSA, bound to the confirmed slip) | **Built, tested** | Forged `alg: none` and key-confusion tokens rejected; revocation on freeze |
| Permission slip, officer confirmation | **Built, tested** (API) | No console screen yet |
| Rule R1 (action must be in the slip and registry) | **Built, tested** | |
| Value matcher and rule R2 (restricted values must not leave the building) | **Built, tested** | Recognises the representations in `docs/ADVERSARIAL_TESTS.md`; paraphrase is a declared gap. With a real model: unprotected and R1-only columns delivered the stock data; in the Sentinel column the first (leaking) email was blocked and a clean acknowledgement was then sent. One recorded run per column, not a rate yet |
| Rule R5 (send budget, reserved atomically) and R6 (third policy block freezes the session) | **Built, tested** | The race test fails when the lock is removed (checked by mutation). Bulk-read volume limits arrive with the second scenario |
| Rule R3 (a recipient that appears only in untrusted content is refused) and the recipient part of R1 (recipients must be inside the slip's domains) | **Built, tested** | Catches a redirect to another mailbox on the vendor's own domain, which the R1-only column lets through. Value matching on addresses only: an address an attacker assembles from fragments, or an unseen address on an allowed domain, is not caught (asserted in the tests) |
| Rule R4 (a held call needs the officer's approval of this exact action) | **Built, tested** (API) | Bound to a hash of session, tool and arguments; one-time; expires; silence is a denial; every other rule still runs after approval. No phone page or console screen yet |
| Structured egress (hardened mode) | **Built, tested** (backend) | The slip is bound to a quotation work item resolved through a mock intake queue to the vendor master; the agent gets one tool, `send_quote_ack(quote_id)`, and no free-text e-mail tool; Sentinel renders a fixed message and chooses the recipient; the message hash is recorded before sending and re-checked at send time. Narrows the attack surface; does not remove every covert channel (calls, timing, retries, other tools). Not yet on screen |
| Signed, hash-chained audit log | **Built, tested** | Ed25519-signed, SHA-256 chained, fsynced, written before an action is forwarded; slow or failed writes fail closed; no secret values or raw arguments are stored. Detects a changed, deleted, reordered or forged record. It does not prove the events were true, and a truncated log is only caught if the verifier holds the earlier chain head |
| Mock tool server, mail sink (measures what was delivered) | **Built, tested** | |
| Live events (WebSocket) | **Built, tested** | |
| Runs API (`/runs`: scenarios across the three comparison lanes, officer confirmation, scripted attacker, replay of recorded runs with divergence detection, `record` CLI) | **Built, tested** | Views are built only from gateway events and the real mail sink. Replay re-issues the recorded model actions; Sentinel's decisions are computed live and compared with the recorded ones. No recordings from a real model are committed yet |
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
