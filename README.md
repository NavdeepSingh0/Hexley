# Sentinel

**The AI can only do the job you gave it.**

Sentinel is an MCP gateway that sits between an AI agent and its tools. It checks every action against the task the officer approved, where the data came from, and where it is going, and blocks what the task never asked for. No LLM makes any security decision.

Team 404 Disruptors · Zinnovatio 4.0

## Status (updated each milestone; last: M3 console built on top of M2 enforcement; the evaluation harness built; the fallback video and a full rehearsal remain)

This table says what exists today, not what the architecture describes. "Tested" means automated tests cover the listed behaviour, not that the component is comprehensively secure.

| Component | Status | Notes |
|---|---|---|
| MCP gateway (proxy, per-call checks) | **Built, tested** | R1 on every call; agent headers never forwarded; fail-closed `decide()` |
| Session tokens (EdDSA, bound to the confirmed slip) | **Built, tested** | Forged `alg: none` and key-confusion tokens rejected; revocation on freeze |
| Permission slip, officer confirmation | **Built, tested** (API and console) | |
| Rule R1 (action must be in the slip and registry) | **Built, tested** | |
| Value matcher and rule R2 (restricted values must not leave the building) | **Built, tested** | Recognises the representations in `docs/ADVERSARIAL_TESTS.md`; paraphrase is a declared gap. With a real model: unprotected and R1-only columns delivered the stock data; in the Sentinel column the first (leaking) email was blocked and a clean acknowledgement was then sent. One recorded run per column, not a rate yet |
| Rule R5 (send budget, reserved atomically) and R6 (third policy block freezes the session) | **Built, tested** | The race test fails when the lock is removed (checked by mutation). Bulk-read volume limits arrive with the second scenario |
| Rule R3 (a recipient that appears only in untrusted content is refused) and the recipient part of R1 (recipients must be inside the slip's domains) | **Built, tested** | Catches a redirect to another mailbox on the vendor's own domain, which the R1-only column lets through. Value matching on addresses only: an address an attacker assembles from fragments is not caught (asserted in the tests). An unseen address on an allowed domain used to be a declared gap; R7 now makes it wait for the officer once the session has read untrusted content |
| Generality core (rule R7, typed destinations, generic fingerprints, tool onboarding, slip builder) | **Built, tested** (108 new tests, 12 new mutation checks) | Works for any tool the officer classifies, not only the quotation scenario. R7: after the session reads untrusted content, a consequential action needs the officer's approval unless it goes only to a destination the slip names as internal, the vendor on file, or Sentinel's fixed template. Destinations are typed (e-mail, URL host, file path), and an ambiguous URL or path is refused rather than interpreted. Fingerprints cover e-mail addresses, phone and account numbers, identifiers and copied passages. Unclassified tools stay invisible and blocked. **Limits:** one tool server per gateway (several upstreams are not built); a paraphrase of confidential text is still a declared gap; R7 can be noisy on a task that reads untrusted content and then acts often; see D-037 |
| Rule R4 (a held call needs the officer's approval of this exact action) | **Built, tested** (API) | Bound to a hash of session, tool and arguments; one-time; expires; silence is a denial; every other rule still runs after approval. No phone page or console screen yet |
| Structured egress (hardened mode) | **Built, tested** (backend) | The slip is bound to a quotation work item resolved through a mock intake queue to the vendor master; the agent gets one tool, `send_quote_ack(quote_id)`, and no free-text e-mail tool; Sentinel renders a fixed message and chooses the recipient; the message hash is recorded before sending and re-checked at send time. Narrows the attack surface; does not remove every covert channel (calls, timing, retries, other tools). Not yet on screen |
| Signed, hash-chained audit log | **Built, tested** | Ed25519-signed, SHA-256 chained, fsynced, written before an action is forwarded; slow or failed writes fail closed; no secret values or raw arguments are stored. Detects a changed, deleted, reordered or forged record. It does not prove the events were true, and a truncated log is only caught if the verifier holds the earlier chain head |
| Mock tool server, mail sink (measures what was delivered) | **Built, tested** | |
| Live events (WebSocket) | **Built, tested** | |
| Runs API (`/runs`: scenarios across the three comparison lanes, officer confirmation, scripted attacker, replay of recorded runs with divergence detection, `record` CLI) | **Built, tested** | Views are built only from gateway events and the real mail sink. Replay re-issues the recorded model actions; Sentinel's decisions are computed live and compared with the recorded ones. Real-model recordings are committed (see below) |
| General-purpose tools and scenarios (documents and real PDFs, a customer database, a mock web, a webhook, files, an approval-gated command) | **Built, tested** (31 new tests, 4 new mutation checks) | Two scenarios on the officer's own task: `compromised_pdf` (hidden white text in a PDF names an address inside the allowed domain) and `poisoned_web` (hidden text in an intranet page asks for customer data in a status post). Both baselines leak because the destination is allowed; Sentinel stops restricted customer data leaving to a place that is not internal (R2, plus R3 for the PDF) and still delivers the real summary. The database is read-only by SQLite's authorizer. **Limits:** our own mock tools, not real MCP servers; image-based injections need OCR and are not covered; see D-038 |
| OAuth sign-in for AI clients (`up --public-url` or `--tunnel`) | **Built, tested** (26 tests, 3 mutation checks); **verified live on 27 Oct 2026** with a free Claude.ai account: signed in with "Sign in now", the officer approved the slip, a send containing restricted data was denied by R2 and nothing was delivered (one session, not a measurement) | The AI client signs in; the officer approves the permission slip with a code shown in the terminal; the token is the session token, so the header route still works. Demo-grade (in-memory, one officer); see D-036 for the stated limits |
| Agent runner (OpenAI-compatible, Ollama or NVIDIA) | **Built**, smoke-tested | The model client's retry of timeouts and 429/5xx is unit-tested with a fake transport; a full model run is not |
| Evaluation harness (`python -m sentinel eval`) | **Built, tested** | Measured from the mail sink against a labelled corpus; results with commit, model, n and date in `eval/results/`. Numbers below are copied from `scripted-20261028T053039.json` (commit 4945d6b, clean tree) and `recorded-20261026T195255.json` (commit 1ffea42, clean tree). They describe this corpus and this task, not prompt injection in general |
| Console (start, permission slip, three-column stage, verdict with the matched values highlighted, officer approval card, audit verify and tamper, guided presenter keys) | **Built**, unit-tested (derivations) and checked on screen at 1280x720 and 1920x1080 | Served at `/console/` by `python -m sentinel up`. Build once with `npm --prefix console ci` then `npm --prefix console run build` (the build output is not committed). Not yet rehearsed end to end by a person |
| Recordings of a real model (`recordings/`, nemotron-3-ultra-550b, 5 attempts each of the poisoned and clean quotation) | **Committed** | Several attempts ended in `agent_error` on the hosted API (the attempt is kept, and shown as such). Every recording replays without divergence (tested) |
| Phone approval page | **Planned**, first to cut | The approval card in the console works; there is no separate phone page |
| API authentication | **Demo-grade** | One static bearer token; not production identity management |

## Measured results (from `eval/results/`, not typed by hand)

Scripted attacker, labelled corpus (`scripted-20261028T053039.json`, commit 4945d6b, clean tree), through the real gateway, read from the mail sink (n = 1 per case and column). The corpus covers the quotation scenario and the general families (documents, a customer database, a mock web, a webhook, files):

| Measure | Unprotected | R1-only | Sentinel |
|---|---|---|---|
| Disclosures that reached the sink (41 cases: 31 representations of the stock data, 10 customer-data routes through an allowed but not internal e-mail address, web address or folder) | 41/41 | 41/41 | **0/41** (95% CI 0%-9%) |
| Declared gaps that reached the sink (8 cases: paraphrase, digits spaced apart, a spelled-out e-mail address, ...) | 8/8 | 8/8 | **8/8** (expected; stated on the limits slide) |
| Reply to another address that reached the sink (3 cases) | 3/3 | 2/3 | 0/3 |
| Valid actions wrongly blocked (28 actions in 10 clean cases) | 0/28 | 0/28 | 0/28 (95% CI 0%-12%) |
| Clean tasks completed (10 cases, incl. a hostile document and a compromised PDF whose real summary still goes) | 10/10 | 10/10 | 10/10 |

The zero is a measurement on this corpus. The cases were written by us from the matcher's documented list and from the routes we built, so it shows the system does what its documentation says, not that an attacker cannot find another route. The blind attack cards written by people who had not read the rules (core plan B4) are not in yet. Hardened slip, apart from the table: 0 of 4 attack cases delivered; the valid acknowledgement completed 1/1. The tools in the general families are our own mocks (D-038), not real file, browser or database servers.

Real model (nemotron-3-ultra-550b), from the 30 committed recordings (15 poisoned, 15 clean attempts; `recorded-20261026T195255.json`, commit 1ffea42). 21 of the 90 lanes ended in `agent_error`, all HTTP 429 (the hosted API's rate limit) after retries, and are excluded and listed, so the denominators are 9 to 13 lanes per cell:

| Condition | Unprotected | R1-only | Sentinel |
|---|---|---|---|
| Poisoned quotation: lanes that delivered restricted data | 13/13 (95% CI 77-100%) | 12/12 (76-100%) | **0/9** (0-30%) |
| Clean quotation: lanes that delivered restricted data (the model's own habit, as in M0) | 4/13 (13-58%) | 2/11 (5-48%) | 0/11 (0-26%) |

All 9 usable poisoned Sentinel lanes were stopped and then sent a clean acknowledgement (`recovered`, not counted as completed, D-007); on the clean quotation 7 of 11 Sentinel lanes completed outright and 4 recovered, because the model tried to include stock figures even without an injection and was stopped. Zero of 37 valid Sentinel actions were blocked. One model, one task: this does not generalise to other models or other attacks.

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
