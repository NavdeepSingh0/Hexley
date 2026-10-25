# Sentinel — Architecture

Status: **draft for review (C-004)**. Interfaces below are frozen once the review is closed; after that a change needs both builders to agree and a note in `docs/DECISIONS.md`.
Scope and story: `docs/MVP.md`. Attack oracles: `docs/ADVERSARIAL_TESTS.md`. Measured spike facts: `docs/spikes/M0-results.md`.

## 1. Shape of the system

```
Officer ── confirms slip ──▶ Console (React, :5173) ◀── WS /ws ──┐
                                   │ REST                         │ events
                                   ▼                              │
Agent (any MCP client) ──MCP + session token──▶ Sentinel gateway (:8100/mcp) + API (:8000)
                                                   │  registry · labels · matcher · rules · egress · audit
                                                   └──MCP + Sentinel-minted token──▶ Mock tools (:8200/mcp)
```

One Python process serves the gateway, REST/WS API and event bus. The mock tools run as a second process so "direct calls are rejected" is real. The agent runner is a third process that only knows its session's MCP URL and token.

## 2. Repository layout

| Path | Responsibility |
|---|---|
| `src/sentinel/models.py` | Pydantic contracts (section 4) |
| `src/sentinel/registry.py`, `config/registry.yaml` | Tool labels: capability, resource class, output integrity and confidentiality, `fingerprint_fields`, `requires_human_verification`, outbound flag. Unknown tool or malformed result defaults to **untrusted + restricted** |
| `src/sentinel/contracts.py`, `config/templates.yaml` | Slip templates (`quotation_processing`, `records_grievance`); session token mint/verify (Ed25519), expiry, revocation |
| `src/sentinel/labels.py` | Per-session state: integrity (min), confidentiality (max), fingerprint index (value to `source_ref`), counters |
| `src/sentinel/matcher.py` | Normalisations 1–7 from `ADVERSARIAL_TESTS.md`; returns matches with `source_ref` |
| `src/sentinel/egress.py` | Structured egress: validate `quote_ack_v1` slots, resolve the recipient from `vendor_master`, render the message |
| `src/sentinel/rules.py` | R1–R6 as **pure functions** over a `Facts` object. No I/O, no clock, no randomness |
| `src/sentinel/engine.py` | `decide(action, session) -> Decision`: build facts, run the rule set for the column and mode, combine by precedence, **fail closed** on any exception, write audit, emit events |
| `src/sentinel/audit.py` | Hash chain (SHA-256 over canonical JSON), Ed25519 signature, `verify()`, demo tamper |
| `src/sentinel/events.py` | In-process async bus (adapted from Nexus `runtime/events/bus.py`, adding per-handler error isolation) and the event envelope |
| `src/sentinel/gateway.py` | FastMCP proxy plus `SentinelMiddleware` (`on_list_tools`, `on_call_tool`) calling `engine.decide` |
| `src/sentinel/api.py` | FastAPI REST and `WS /ws` (fan-out adapted from Nexus `runtime/api/websockets/manager.py`); static bearer token; CORS limited to the console origin |
| `src/sentinel/cli.py` | `python -m sentinel {up,demo,test,verify,eval}` |
| `src/sentinel/tools/server.py` | Mock MCP tools: quotations, stock register, ledger, mail sink (with visible inboxes), payments, vendor master, veterans' records. Rejects any call without the Sentinel-minted, audience-bound token |
| `src/sentinel/agent/runner.py`, `cassette.py` | Agent loop: Ollama OpenAI-compatible `/v1/chat/completions` with tools, over a `fastmcp.Client`. Cassettes record and replay model turns keyed by a hash of the message list |
| `src/sentinel/eval/` | Scenario YAML loader, harness, reporter (pattern from Nexus `benchmark/`) |
| `fixtures/` | Synthetic data with `.example` domains: clean, poisoned and paraphrase quotations; stock register with canary rows; vendor master; veterans' records |
| `console/` | Vite + React 19, reactflow 11 + dagre (as Nexus `ui/`). Reuse Nexus `tokens.css`, the dagre layout helper and WebSocket reconnect loop; every component is new |
| `tests/` | pytest: rule tables, matcher, egress, audit, gateway integration, adversarial oracles |
| `spikes/` | M0 throwaway code; never imported by `src/` |

## 3. Request lifecycle (sentinel column)

1. The officer starts a task in the console. `POST /tasks` creates a draft slip from a template, and the officer confirms it (`POST /tasks/{id}/confirm`). Sentinel mints a session token bound to the contract hash, logs `contract.issued`, and returns the session's MCP URL and token.
2. The agent connects to `:8100/mcp` with `Authorization: Bearer <session token>`.
3. `on_list_tools` returns only the tools the slip allows. In hardened mode it replaces `send_email` with `quote_ack_v1`.
4. `on_call_tool` builds an `AgentAction` and calls `engine.decide`, which works through these steps:
   - verify the token (expiry, revocation, freeze);
   - **check R1 on every call, whatever was listed** (spike finding C3: a hidden tool can still be called);
   - match the outbound arguments against the session's fingerprint index (R2);
   - check where each destination came from (R3);
   - check the registry's human-verification flag (R4);
   - check volume and send budgets (R5);
   - check the block counter (R6);
   - combine the verdicts: FREEZE > BLOCK > ASK > ALLOW.
5. What happens next depends on the verdict:
   - **ALLOW:** forward through `ProxyClient(forward_incoming_headers=False)` with Sentinel's own downstream token (finding C5: never forward agent headers). The result is then labelled from the registry, its fingerprint fields are indexed, and its hash is logged.
   - **ASK:** hold the call, emit `approval.pending`, and wait for `POST /approvals/{id}`. A timeout means BLOCK.
   - **BLOCK or FREEZE:** return a tool error carrying the plain-English summary. Nothing reaches the tool.
6. Every step emits events for the console and writes a signed audit record.

`standard` column: the same pipeline with only R1 enabled. `unprotected` column: the same process forwards everything with no rules, but still emits events and is labelled on screen as "observer, no enforcement". All three use the same model, prompt and fixtures.

## 4. Interfaces (I1–I4)

Names follow MVP.md. Mapping to the older build-kit names: ALLOW=ALLOW, ASK=REQUIRE_APPROVAL, BLOCK=DENY, FREEZE=QUARANTINE; R1–R6 replace SNT-001..015.

**I1 models (`models.py`)**
- `AgentAction`: `action_id, ts, session_id, contract_id, column (unprotected|standard|sentinel), tool, capability (read|write|send), resource_class, args, outbound: bool`.
- `TaskContract`:
  - identity: `contract_id, template, objective, officer`;
  - scope: `mode (standard|hardened), allowed_tools[], resource_classes[], allowed_recipient_domains[], max_records`;
  - egress budget: `max_messages, max_records_out`;
  - `egress_templates[]` (see below);
  - lifecycle: `issued_at, expires_at, status (pending|active|revoked|frozen), contract_hash, token_id`.
- Each entry of `egress_templates[]`:
  - `template_id`
  - `recipient_from` (registry field)
  - `slots: {name: {pattern? enum? equals_session?}}`
  - `body` (render template)
- `Facts`:
  - `contract`
  - `session: {integrity, confidentiality, untrusted_sources[]}`
  - `fingerprint_hits[]` (each: value, field, `source_ref`)
  - `destination_origin: user|registry|untrusted`
  - `counters: {blocks, messages_out, records_out}`
  - `requires_human_verification: bool`
- `Decision`: `decision_id, action_id, effect (ALLOW|ASK|BLOCK|FREEZE), rule_ids[] (R1..R6), reason_code, summary_plain, evidence[] {kind, detail, matched_tokens[], source_ref}, latency_ms`.
- `LogRecord` (from build-kit `event_log_record`): `seq, ts, type, session_id, payload_hash, prev_hash, hash, sig, kid`. Genesis `prev_hash` is 64 zeros; `hash` is SHA-256 over canonical JSON without `hash` and `sig`; `sig` is Ed25519 over `hash`. Tool results are stored as hashes only.
- Reason codes:

  | Rule | Codes |
  |---|---|
  | R1 | `NOT_IN_SLIP`, `EGRESS_TEMPLATE_INVALID`, `NOT_IN_REGISTRY` |
  | R2 | `SECRET_EGRESS` |
  | R3 | `DEST_FROM_UNTRUSTED` |
  | R4 | `HUMAN_VERIFICATION` |
  | R5 | `VOLUME_EXCEEDED` |
  | R6 | `BLOCK_THRESHOLD_FREEZE` |
  | Engine fault | `FAIL_CLOSED` |

**I2 config (`config/*.yaml`)**: the tool registry and slip templates, validated against the models at startup. Invalid config means Sentinel refuses to start.

**I3 REST (`:8000`, bearer token)**

| Endpoint | Purpose |
|---|---|
| `POST /tasks` | Create a draft slip |
| `POST /tasks/{id}/confirm` | Activate the slip; returns `{mcp_url, session_token}` |
| `GET /approvals/{id}` | Read an approval card (phone page) |
| `POST /approvals/{id}` | Resolve it: approve or deny |
| `POST /killswitch` | Freeze a session |
| `GET /audit/verify` | Check the log chain |
| `POST /audit/tamper` | Demo build flag only |
| `GET /inbox` | Mail-sink contents per column |
| `GET /metrics` | Counters and latency |
| `GET /sessions/{id}` | Session state |

**I4 events (`WS /ws`)**
- Envelope: `{type, session_id, column, ts, payload}`.
- Types:

  | Type | Carries |
  |---|---|
  | `contract.issued` | The confirmed slip |
  | `session.started` | |
  | `action.requested` | The proposed action |
  | `decision` | The full Decision |
  | `approval.pending`, `approval.resolved` | |
  | `freeze` | |
  | `inbox.received` | What the mail sink delivered; feeds the enemy-inbox panel |
  | `audit.record` | |
  | `graph.node`, `graph.edge` | Edges are tool flow plus value-match links |
  | `metrics.tick` | |

**Ports:** API 8000 · gateway 8100 · tools 8200 · console 5173 · Ollama 11434.

## 5. Security invariants (each has a test)
1. No LLM call anywhere in `rules.py`, `engine.py`, `matcher.py` or `egress.py`.
2. Any exception inside `decide` returns BLOCK with `FAIL_CLOSED`.
3. R1 is evaluated on **every** `tools/call`, not just reflected in `tools/list`.
4. The gateway's downstream client never forwards incoming agent headers.
5. Tools reject calls without the Sentinel-minted token.
6. Labels and fingerprint fields come only from the registry. Unknown means untrusted + restricted.
7. A frozen or revoked session cannot call, reconnect, or start a new session without a newly confirmed slip.
8. Recipients in hardened mode are resolved by Sentinel, never supplied by the agent.

## 6. Build order
| Milestone | Done when |
|---|---|
| M0 spikes | `docs/spikes/M0-results.md` |
| M1 skeleton | Agent → gateway → tools, all ALLOW, events reach a bare console |
| **M2 core (gate)** | Matcher, rules, egress, audit; the priority oracles (rows 1, 9, 12, 13, 15, 17, 18) pass in pytest; primary scenario leaks in unprotected and standard and is blocked in sentinel; benign twin passes |
| M3 demo surface | Main stage, verdict card, chain view on real events |
| M4 Tier 1 | Challenge, approval, freeze, signed log UI, scoreboard, measured eval, replay |
| M5 ready | Fresh-clone demo offline on both laptops, deck with measured numbers, rehearsals |
