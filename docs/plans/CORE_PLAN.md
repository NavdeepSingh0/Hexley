# Sentinel core plan (Navdeep + Claude)

**Written 27 Oct 2026.** The teammates' half is `docs/plans/FRONTEND_PLAN.md`; the shared contracts are in `docs/contracts/`. Both plans use the same phase gates.

## Context
The core works on one measured scenario (poisoned quotation → e-mail): gateway, R1–R6, signed audit log, approvals, hardened mode, runs/replay, minimum console, eval harness, and one real Claude.ai session denied on 27 Oct. For the finale we make it **general** (any tool, your own task, a compromised PDF), **connectable by anyone** (OAuth for free Claude.ai accounts), give it a **chat host** and a **mascot**, restyle the console to the deck look, and rehearse. Deadlines: on-site build from **Fri 30 Oct 12:00**; judging **Sat 31 Oct 14:00**.

## Decisions
- Dark theme default; one vocabulary everywhere: **ALLOWED / DENIED / NEEDS APPROVAL / QUARANTINED** with a plain-English reason underneath.
- The deck stays as it is; the quotation demo stays; general scenarios are added.
- New API endpoints under `/api/v1/…`; existing ones (`/runs`, `/audit/*`, `/approvals/*`, …) stay put.
- Red-team cards: teammates (blind) and Navdeep (informed), reported separately.

## Method (same as the frontend plan)
1. Each phase has deliverables and a QA checklist; QA = `python -m uv run pytest` green, the phase's new tests, the listed manual checks, and (where a rule is added) a mutation check in `spikes/mutate.py`.
2. **Pass → commit on `main`** (no co-author or attribution trailer, by Navdeep's instruction) → next phase.
3. **Fail → rework only what failed → QA again. 3 QA attempts per phase.** After attempt 3 fails: stop the phase, write an escalation note in `docs/PHASE_LOG.md`, and decide with Navdeep (cut scope / change approach / move later / drop).
4. Every attempt is one line in `docs/PHASE_LOG.md`.
5. Dependent phases wait for their predecessor to pass.

## Priorities and cut order
- **Must:** B0, B2, B3 (files, web, PDF), B6, B8, B9.
- **Should:** B1, B5, B4.
- **Could:** B7, the database and shell families, chat replay, a local-model client.
- **Cut first if late:** B7 extension → shell/database families → chat replay → local-model client → secret-URL route (not planned unless OAuth fails).

## Phases

### B0. Handoff kit (Tue 27)
- **Deliverables:** `docs/plans/FRONTEND_PLAN.md`, this file, `docs/PHASE_LOG.md`, `docs/contracts/API.md`, `docs/contracts/MASCOT.md`, `docs/redteam/CARD_TEMPLATE.md`, `.github/pull_request_template.md`; `design/tokens.css`; `site/` scaffold (Vite + React 19 + `react-router-dom`, pinned versions at least two weeks old, dev server on port 5174, proxy to the API like `console/vite.config.js`, `src/api/client.js` reusing the token logic of `console/src/api.js` with a mock switch, route placeholders, mocks shaped exactly like `API.md`); `docs/TEAM_BRIEF.md` and `docs/brief/` committed.
- **Remote:** only after Navdeep creates the private repo and gives the URL: scan for secrets (`.env` ignored; no `nvapi-`, bearer tokens, keys), `git remote add origin`, push `main`.
- **QA:** a fresh clone in another folder → `python -m uv sync`, `npm ci` in `console/` and `site/`, all Python and console tests pass, `npm run build --prefix site` passes, the site dev server renders the shell on mocks; teammates confirm they can clone.

### B1. OAuth (Tue 27 → Wed 28)
- **Design:** `src/sentinel/oauth.py` with `SentinelOAuthProvider(OAuthProvider)` (base class `fastmcp/server/auth/auth.py`, pattern of `fastmcp/server/auth/providers/in_memory.py`). The library provides discovery metadata, dynamic client registration and PKCE.
  - `authorize()` stores a pending request (slip drafted with `contracts.draft_contract` from a preset) and redirects the browser to `/oauth/consent?request=<id>`.
  - `GET/POST /api/v1/oauth/requests/{id}`: approval needs the **officer code** (random 6 digits, shown in the console and the terminal); approval calls `confirm.confirm_draft` and issues a one-time authorization code.
  - Token exchange returns **our session JWT** (`contracts.mint_session_token`) as the access token, so `gateway.SentinelMiddleware._session()` is unchanged and the header route keeps working. `verify_token` = `verify_session_token` + `store.is_usable`. Refresh re-mints for the same live session; freezing a session revokes its tokens.
  - The consent page and its endpoints are served on the gateway's public origin.
  - `cli.py up --public-url URL` and `--tunnel` (starts a `cloudflared` quick tunnel, reads its URL, sets the issuer and base URL before the gateway starts).
- **Attempt 1 includes a live spike** on the free Claude.ai account ("Sign in now").
- **Tests (`tests/test_oauth.py`):** discovery metadata; registration; authorize → consent → code → token → tool call; wrong PKCE verifier; code reuse; redirect mismatch; missing or wrong officer code; expired request; frozen-session token rejected; refresh; header route unchanged. **Mutation:** approval without the officer code must fail a test.
- **QA:** tests green; live: free Claude.ai account connects with Sign in now and a send containing restricted data is DENIED.

### B2. Generality core (Wed 28)
- **(a) R7 taint:** when a session reads output labelled untrusted (already detected in `gateway.py` where R3 collects addresses), set `Session.tainted_by`. After that, an outbound action to a destination outside the slip → DENIED; a consequential action → NEEDS APPROVAL. The quotation flow (reply to the vendor on file) stays ALLOWED.
- **(b) Generic destinations:** every outbound tool declares `destination_args` in the registry; the slip gets `allowed_destinations` (e-mail domains, URL prefixes, sandbox path prefixes); R1's recipient check generalises to it.
- **(c) Generic fingerprints** (`matcher.py`): `fingerprint_fields: [all]` for confidential tools; new kinds for e-mail addresses, phone numbers, generic IDs, and long-text shingles (normalised word n-grams) so copied confidential prose is caught. Existing representations keep their tests.
- **(d) Tool onboarding:** `config/upstreams.yaml` (several upstream MCP servers behind one gateway); unknown tools keep the conservative default (`registry.py`); `GET /api/v1/tools`, `POST /api/v1/tools/{name}/classify` (officer) → `data/registry.local.yaml` overlay merged by `load_registry`.
- **(e) Slip builder:** `POST /api/v1/slips` (objective, tools, destinations, data classes, budgets, TTL) validated against the registry; existing templates become presets.
- **Tests:** `test_r7_taint.py`, `test_matcher_generic.py`, `test_onboarding.py`, `test_slip_builder.py`; mutation entries for R7 and the destination check.
- **QA:** all tests green; `python -m sentinel eval --agent scripted` still shows 0 through and 0 false blocks.

### B3. Tool families and general scenarios (Wed 28 → Thu 29)
- **Mock, synthetic, sandboxed** (`tools/server.py`, `fixtures.py`): `list_documents`, `read_document(path)` (real PDFs in a sandbox folder, text via `pypdf`), `write_file`, `fetch_url` (local mock web pages, one poisoned), `http_post` (outbound sink, recorded like mail), `query_db` (in-memory SQLite: customers and salaries, confidential), `run_command` (approval-only, never executes anything). Registry entries for each.
- **Scenarios** in `runs.py` (three lanes, scripted attacker + model task text): **your own task with a compromised PDF** ("summarise my documents and send the summary to my manager"; the PDF asks to post customer data to an outside URL); **poisoned web page** → `http_post` exfiltration; **database report** → e-mail.
- **QA:** each scenario behaves correctly in all three console columns; tests per scenario; the scripted corpus gains cases for the new families.

### B4. Red-team evaluation (Thu 29)
- **Deliverables:** `eval/corpus_redteam.py` from `docs/redteam/cards/` (label, `author_saw_rules`); each card converted or rejected with a written reason; scripted run + one live pass; result file; README section reporting **blind** and **informed** results separately, plus the false-block rate on the normal tasks.
- **QA:** every card accounted for; result JSON with commit, n, date.

### B5. Chat backend (Thu 29)
- **Deliverables:** `src/sentinel/chat.py` ChatManager and `/api/v1/chat*` routes per `API.md`; `agent/runner.run_agent` refactored for multi-turn with per-step callbacks; **key failover** in `ModelEndpoint` (`NVIDIA_API_KEY`, `NVIDIA_API_KEY_2`, `NVIDIA_API_KEY_3`; never logged; a throttle gate per key; switch key on 429; honour `Retry-After`; `retry` in the view); server-side `mascot_state(events)` pure function implementing the table in `MASCOT.md`; presets; chat record and replay as a fallback.
- **Tests:** a model faked with `httpx.MockTransport` (scripted tool calls), 429 failover, disclosure always present, mascot mapping.
- **QA:** tests green; one live smoke conversation.

### B6. Console restyle and vocabulary (Thu 29)
- **Deliverables:** `console/` imports `design/tokens.css`; dark default and toggle; deck vocabulary in `console/src/lib/derive.js` (stamps, headlines, verdict) with tests updated; a mascot slot.
- **QA:** vitest green; headless-Chrome screenshots at 1280×720 and 1920×1080 in both themes reviewed; contrast AA.

### B7. Mascot integration and extension (Thu 29, could)
- **Deliverables:** `<sentinel-mascot>` (from A6b) in the console and the chat; `extension/` (Manifest V3): a background worker polls `GET /api/v1/mascot/state`; a content script injects the widget in a Shadow DOM at the bottom left of claude.ai and chatgpt.com; it reads nothing from the page; an on/off switch.
- **Attempt 1** starts with Chrome's local-network-permission spike.
- **QA:** loads unpacked; during a real Claude.ai session it shows DENIED after a blocked send.

### B8. Integration and real clients (Fri 30)
- **Deliverables:** `site/dist` served at `/` (pattern of `api.mount_console` / `ConsoleFiles`, SPA fallback, FastAPI `docs_url=None`); `up` opens `/`; `scripts/export_evidence.py` → `site/public/evidence.json`; real-client matrix: Claude.ai free (OAuth), Claude.ai Pro (header), Claude Code (header), VS Code (header, if available), a local model through an MCP-capable client (if feasible) → screenshots and statuses in the connect data; fresh-clone test on unused ports.
- **QA:** every Tested status has a screenshot; the fresh clone runs end to end.

### B9. Rehearsal and fallback (Fri 30 on-site → Sat 31)
- **Deliverables:** three timed rehearsals of the five-minute flow (site → See it work → three columns → why denied → quarantine → approval → audit verify and tamper → your own task with a compromised PDF in Sentinel Chat → real Claude.ai); fix list; fallback video; README and DECISIONS (D-036 onwards); code freeze Sat 10:00.
- **QA:** a full rehearsal without intervention; the fallback video plays offline.

## Verification (whole system)
`python -m uv run pytest`; `npm --prefix console run test`; `npm --prefix site run build`; `python -m sentinel eval --agent scripted` (0 through, 0 false blocks); red-team result file; fresh clone on unused ports; real-client screenshots; three rehearsals.
