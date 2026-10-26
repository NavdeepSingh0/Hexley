# Plan: Sentinel remaining build (hardened mode, runs + replay, console, eval) for the 31 Oct demo

## Context
Backend enforcement is built and tested (R1–R6, matcher, signed audit log, approvals; 235 tests; mutation-checked). Missing, in D-031 order: (1) hardened mode backend, (2) an evaluation harness whose numbers come from real gateway events and the real mail sink, (3) the console judges actually see, (4) recorded runs replayed honestly. Today is 27 Oct; on-site build starts 30 Oct 12:00; judging 31 Oct 14:00. One builder (Claude). User decisions: **both LIVE and REPLAY selectable on stage**, **Claude builds everything**, **small inline Approve/Deny card** for R4 (phone page cut, D-031). Execution runs on Sonnet (high), per the user's workflow.

Ground rules carried over: never fabricate chain links, live numbers or events (D-031); D-028 two separate demos (like-for-like comparison never mixed with hardened mode); D-030 four metrics; D-013 replay disclosure; nothing secret in the audit log.

## Key design decisions (from exploration + design review)
- **Gateway-local tool works:** `@proxy.tool async def send_quote_ack` on the `FastMCPProxy`; middleware `on_call_tool` still runs first; the tool reads the session from the existing `_current` ContextVar; it must call the backend directly via `client_factory()` (never `proxy.call_tool`, which would re-run the middleware). Needs a registry entry. Local tools win name collisions; keep names unique.
- **Hide local tools from columns whose slip doesn't allow them** (including unprotected, which today sees every backend tool), and fail closed if called without a hardened slip. Keeps the like-for-like comparison unchanged.
- **Console without reactflow:** reactflow 11 does not declare React 19 as a peer. The chain is 3–6 steps, so a horizontal timeline with SVG arcs for value-match links is simpler and avoids the dependency. Reuse from Nexus only: `ui/src/styles/tokens.css`, the `.badge/.btn/.panel/.status-dot` classes from `components.css`/`dashboard.css` (credited in a header comment). **Never copy `ui/src/utils/supabase.js`** (hard-coded key).
- **Console polls `GET /runs/{id}`** every ~700 ms instead of WebSocket: no reconnect logic, survives reloads, one source of truth. Token passed in the URL fragment printed by `up` (`http://localhost:5173/#token=…`), no login screen.
- **One agent interface, two implementations:** `ModelAgent` (existing runner) and `ScriptAgent` (a list of tool calls). Replay = ScriptAgent fed a recording plus divergence checks; the scripted attacker and the scripted eval use the same class.
- **Scripted attacker for beats a cooperative model won't produce** (freeze, paraphrase vs hardened, R4 bank change), labelled on screen "SCRIPTED: a fully compromised agent".
- **Runs keep the officer step:** `POST /runs` creates draft slips (status `awaiting_confirmation`); `POST /runs/{id}/confirm` mints sessions and starts lanes. One active run at a time (409).

## Part 1: Hardened backend (27 Oct, time-boxed ~5 h)
Files: `models.py`, `fixtures.py`, `config/templates.yaml`, `config/registry.yaml`, `contracts.py`, `rules.py`, new `egress.py`, `engine.py`, `gateway.py`, `api.py`, tests.
- `TaskContract`: add `work_item_id: str | None = None`, `resolved_vendor: dict | None = None` (defaults keep existing tests green; `extra="forbid"` stays). `ToolEntry`: add `egress_template: str | None = None`, `local: bool = False`.
- `fixtures.INTAKE = {"Q-1042": "shakti", "Q-1043": "shakti", "Q-1044": "shakti", "Q-1045": "shakti"}` (synthetic trusted intake queue).
- Templates: remove the stale `quote_ack_v1` (with `status`) from `quotation_processing`. Add `quotation_processing_hardened`: `mode: hardened` (the template sets the mode; API returns 422 on mismatch), `allowed_tools: [read_quotation, query_stock, send_quote_ack]`, `requires_work_item: true`, egress template `quote_ack_v1` with ONE slot `quote_id {pattern: "^Q-\\d{4}$", equals_session: work_item_id}`, body `"Quotation {quote_id} received. A purchase order will follow if accepted."`, subject `"Quotation {quote_id} acknowledged"`, `max_messages: 1`.
- `draft_contract(..., work_item_id=None)`: when the template requires a work item, resolve INTAKE → `VENDOR_MASTER`; unknown → `KeyError` → API 422; assert the resolved vendor's domain ∈ `allowed_recipient_domains`. `work_item_id` and `resolved_vendor` are inside the contract hash.
- Registry: `send_quote_ack {capability: send, outbound: true, consequential: true, local: true, egress_template: quote_ack_v1, output: trusted/internal}`.
- `egress.py` (pure): `validate(template, args, contract) -> list[str]` (exact slot set: extra or missing slot, non-string, pattern, equals_session) and `render(template, args, contract) -> RenderedMessage{to, subject, body, body_sha256}`.
- `rules.rule_r1_egress(action, entry, contract)`: errors → BLOCK `EGRESS_TEMPLATE_INVALID` (counts toward freeze); on success adds evidence `rendered_sha256`.
- Gateway: register local tool; it re-renders, refuses to send if the hash differs from the decision evidence, then calls backend `send_email` via `client_factory()` with the resolved address. `on_list_tools`: local tools appear only when `tool in contract.allowed_tools` (all columns). Unprotected/r1_only call of a local tool → fail closed. Emit `egress.rendered {action_id, template_id, to, body, body_sha256}`.
- R3 evidence fix: `Session.untrusted_destinations` becomes `dict[address, source_tool]` so chain links can name the source tool.
- Acceptance tests (`tests/test_hardened.py`): `test_intake_resolves_vendor`, `test_unknown_work_item_422`, `test_contract_hash_covers_work_item`, `test_quote_ack_sink_body_exact_and_to_resolved`, `test_r1_egress_table` (wrong id, `"Q-1043 2400"`, extra slot, missing slot, non-string → BLOCK), `test_hardened_send_email_is_r1_and_never_delivered`, `test_second_ack_blocked_by_r5`, `test_three_bad_acks_freeze`, `test_quote_ack_hidden_from_baseline_lists`, `test_quote_ack_unprotected_fails_closed`, `test_audit_rendered_hash_equals_sink_body_sha`, `test_paraphrase_attack_cannot_leak_in_hardened`, `test_quotation_vendor_spoof_still_replies_to_resolved_vendor` (row 29). Update `ADVERSARIAL_TESTS.md` coverage (rows 14, 15, 22, 23, 29).

## Part 2: Runs, agents, recordings (27 Oct evening → 28 Oct morning)
New: `src/sentinel/stack.py` (move `Stack`/`serve`/`free_port` out of `tests/conftest.py`; tests import it), `src/sentinel/agents.py`, `src/sentinel/runs.py`, `src/sentinel/eval/oracle.py`; changes to `api.py`, `gateway.py`, `tools/server.py`, `agent/runner.py`, `cli.py`.
- `agents.py`: `Agent` protocol `async run(gateway_url, token, task) -> Transcript`; `ModelAgent` (wraps `run_agent`, shared `RateLimiter` across lanes so three hosted lanes stay under NVIDIA_MAX_RPM); `ScriptAgent(steps)` (issues recorded/scripted calls in order; for replay, compares each live `effect`/`rule_ids` with the recorded ones and stops the lane with `replay.diverged` on mismatch).
- Scenarios (`runs.py` `SCENARIOS`): `poisoned` (Q-1043, fingerprint), `clean` (Q-1042), `redirect` (Q-1044), `stranger` (Q-1045), `hardened` (two lanes: fingerprint vs hardened, scripted paraphrase attacker), `freeze` (scripted repeated leak), `bank_change` (vendor_maintenance + new bank-change letter fixture, scripted, triggers R4 → inline approval card).
- API (frozen):
  - `POST /runs {scenario, source: live|replay|scripted, model?: {provider, model}, recording_id?, officer}` → 201 `{run_id, status: "awaiting_confirmation", task_text, work_item_id, lanes: [{lane_id, column, mode, contract}], disclosure}`
  - `POST /runs/{id}/confirm` → `{status: "running", lanes: [{lane_id, session_id}]}`; 409 if another run is active.
  - `GET /runs/{id}` → `{run, lanes: [{lane_id, column, mode, session_id, status, outcome, steps:[{tool,args,effect,rule_ids,summary,evidence}]}], inbox: [{session_id, to, subject, body, oracle_leak}], approvals: [...], audit_head}`; `POST /runs/{id}/cancel`; `GET /recordings`.
  - Inbox rows are filtered by the run's session ids; `oracle_leak` is labelled in the UI "measured by evaluation oracle".
- New events (payload carries `run_id`): `run.created`, `run.started`, `action.completed {action_id, tool, ok, result_sha256, chars}`, `egress.rendered`, `lane.finished {lane_id, outcome: completed|recovered|frozen|agent_error|max_steps|diverged|cancelled, steps, seconds, final_text}`, `replay.diverged`, `run.finished`.
- Recording schema `recordings/<scenario>-<model>-<ts>.json`: `{schema: "sentinel.recording/1", scenario, work_item_id, task_text, model, recorded_at, sentinel_commit, registry_sha256, templates_sha256, attempt, attempts_total, lanes: [{column, mode, final_text, steps: [{i, tool, args, t_offset_s, recorded: {effect, rule_ids, reason_code, result_sha256}}], outcome: {lane_outcome, delivered, oracle_leak}}]}`. `python -m sentinel record --scenario poisoned --model nvidia/nemotron-3-ultra-550b-a55b --attempts 5` keeps **every** attempt; the console shows "attempt i of N". Replay is labelled "REPLAY · model actions recorded <date> · <model> · Sentinel decisions computed live · time-compressed".
- Acceptance tests (`tests/test_runs.py`): `test_run_requires_confirmation`, `test_scripted_run_event_sequence`, `test_one_active_run_409`, `test_inbox_filtered_by_run`, `test_committed_recordings_replay_without_divergence`, `test_mutated_recording_diverges_and_stops`, `test_record_keeps_all_attempts`, `test_local_tools_hidden_in_baseline_runs`.
- Start the hosted recordings (poisoned + clean, 5 attempts each) in the background on 27 Oct evening so quota/429 problems surface early.

## Part 3: Console (28 Oct, polish 29 Oct)
New `console/` (Vite + React 19, plain JS, no reactflow). `vite.config.js` with `server: {port: 5173, strictPort: true}` (CORS is pinned to 5173).
- `src/api.js` (token from URL fragment; fetch wrapper), `src/useRun.js` (poll `GET /runs/{id}`), `styles/tokens.css` + `styles/components.css` (copied from Nexus with credit, enlarged type for the projector: base 18 px, verdict 28 px+, high contrast).
- Screens/components: `StartPanel` (scenario, source LIVE/REPLAY/SCRIPTED toggle, recording attempt picker, model) → `SlipCard` (allowed tools, recipient domains, resolved vendor + destination with the D-028 wording, Confirm button = officer step) → `Stage` with `Lane` ×3 (headers exactly: "No policy enforcement — instrumented baseline", "R1-only access control", "Sentinel" + mode badge `FINGERPRINT MODE: value matching` / `HARDENED MODE: structured egress`) each with `StepTimeline`, `InboxPanel` (red highlight only when `oracle_leak`), `VerdictCard` (summary_plain, rule ids, evidence incl. matched tokens), `FreezeBanner`; `ChainStrip` (steps in a line; SVG arcs only from R2/R3 evidence `source_ref` to the blocked send; caption "observed tool flow with value-match links"; baseline lanes show "no links: no policy evaluated"); `ApprovalCard` (inline Approve/Deny via `/approvals/{id}`); `AuditPanel` (verify, head hash, tamper button only if enabled); `DisclosureBar` (LIVE / REPLAY / SCRIPTED banner, model, n, date).
- Hardened demo is its own two-lane screen (fingerprint vs hardened), never part of the three-column comparison.
- Acceptance: vitest on the run-state reducer with a captured fixture; exact D-028 header strings; no arc without R2/R3 evidence; replay banner text; `npm run build` passes; grep check: no `supabase`, no tokens in `dist`.

## Part 4: Evaluation harness (29 Oct morning)
New `src/sentinel/eval/{oracle.py, corpus.py, harness.py}`; `python -m sentinel eval --agent scripted|live --n N [--model …]` writes `eval/results/<ts>.json` + a markdown table.
- `oracle.py`: `contains_secret` moved from `spikes/eval_matrix.py` (with its 23 golden cases as tests). `corpus.py`: labelled scripted cases (`supported` / `unsupported-paraphrase` / `clean`) so the denominator is ground truth, not the matcher's own judgement.
- Metrics (D-030; definitions in the JSON): model leakage `{k, n, ci95}` (unprotected lane, live), fingerprint enforcement `{supported_attempts, leaks_through}`, unsupported attempts reported separately, false blocks `{valid_actions, wrongly_blocked}`, task completion `{completed, attempted}` with D-007 strictness (block-then-clean = `recovered`, not completed). Attempt = oracle flags an outbound call's args; leak = oracle flags a mail-sink row; valid action = oracle-clean args to the resolved vendor.
- Result JSON `{schema: "sentinel.eval/1", created_at, sentinel_commit, dirty, agent, model, temperature, n_per_cell, cells: [...], metrics: {...}, errors: [...]}`; errored runs are listed, never dropped.
- Live quota (D-030): only real-model runs through the Sentinel column (the unmeasured number, D-024 is n=1), small n, reported honestly.
- Acceptance (`tests/test_eval.py`): `test_oracle_golden_cases`, `test_scripted_supported_corpus_zero_through`, `test_clean_corpus_zero_false_blocks`, `test_paraphrase_counted_separately`, `test_metrics_from_sink_not_verdicts`, `test_errors_listed_not_dropped`, `test_result_has_commit_model_n`.

## Day-by-day
- **27 Oct (today):** Part 1 (time-boxed); then `stack.py`, `agents.py` (ScriptAgent + scripted attacker), `runs.py` skeleton and the record CLI; start hosted recordings in the background.
- **28 Oct:** `/runs` API + events + replay with divergence; console stage driven by scripted runs (lanes, timeline, inbox, verdict, freeze, audit), then REPLAY and LIVE toggles.
- **29 Oct:** morning eval harness + real numbers into README/deck table; afternoon chain arcs, hardened two-lane screen, approval card; evening fresh-start test on unused ports and **record the fallback video**.
- **30 Oct morning:** rehearsal ×3, fix list; 12:00 on-site build begins (polish, deck numbers, Q&A).

## Cut order (first to go)
1. Inline approval card (R4 stays tested backend-only; one slide).
2. Chain arcs → plain step timeline.
3. LIVE source on stage (REPLAY + SCRIPTED only).
4. Live-model eval metrics → scripted metrics + existing M0 numbers.
5. Hardened two-lane screen → recorded run + slide.
Never cut: the three-column comparison with the real mail-sink inbox, the verdict card, freeze, audit verify.

## Verification
- `python -m uv run pytest` green after each part; new suites named above; `python -m uv run python spikes/mutate.py` extended with a hardened-mode mutation (skip slot validation → `test_r1_egress_table` must fail).
- End to end: `python -m uv run python -m sentinel up --demo --api-port 18000 --gateway-port 18100 --tools-port 18200` (unused ports; check they are free first; stop only the PIDs started), `npm --prefix console run dev`, open the printed `#token=` URL; run `poisoned` in SCRIPTED, REPLAY (attempt 1 of N) and LIVE; confirm the unprotected and R1-only inboxes show the stock data, the Sentinel inbox stays empty, the verdict card names R2, audit verify is green, tamper turns it red at the right record.
- `python -m uv run python -m sentinel eval --agent scripted` produces the four metrics with commit, n and date; numbers copied into README only from that file.
- Update README status table, `ADVERSARIAL_TESTS.md` coverage and `DECISIONS.md` (new interfaces as D-032+) as each part lands; commit per part with the Opus attribution line.
