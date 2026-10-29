# Product plan: closing the gaps found in the audit

29 Oct 2026. Follows `docs/research/PRODUCT_AUDIT.md`. Navdeep's instruction: build the real product (not reframe), cover the gaps found, then test the live model with a compromised PDF he writes himself and that neither the model nor we have seen.

## Method (unchanged)
Phase-gated as before: each phase has deliverables and a QA list; QA pass → log in `docs/PHASE_LOG.md` → commit locally (no trailer) → next phase. Three QA attempts, then stop and discuss. Push only on Navdeep's word.

Every phase also re-runs, so a fix never quietly costs safety or utility:
- the full Python suite;
- the scripted evaluation (disclosures reaching the sink, valid actions wrongly blocked, approval workload), compared with the last results file;
- replay of every recorded real-model run (must stay 0 diverged, or the divergence is explained and the recording re-labelled honestly);
- every scenario end to end through the real stack (`scenario_sweep`), with the log verifying at the end.

## Order and why
Highest value per hour first; the live test is last, as asked, but it is guaranteed: if time runs short, Q7 to Q9 move after it.

| Phase | Audit item | What | Closes incidents |
|---|---|---|---|
| A0 | §1-7 | The audit and this plan (logged as A0; Q1 is the core check that came before it) | — |
| Q2 | P2 | Secret and credential detector on every tool result; R2 for secrets everywhere; **R9** discovered credential never usable | 7, 19, 23, 24 (with Q4) |
| Q3 | P1 | **R8** Rule of Two (`strict_flows`), generic denials to the agent, R6 counts intent | the paraphrase-to-vendor path; freeze DoS |
| Q4 | P3 | Protected paths, destructive operations, SQL and shell effects, `cc`/`bcc`/`reply_to`, hostnames as destinations, matcher normalisation (Unicode, Indian digit grouping, spaced digits) | 8, 9, 10, 19, 21, 26, 28 (part) |
| Q5 | P4 | Tool definition pinning, description scanning, annotations as defaults | 3, 4, 22 (part) |
| Q6 | P5 | Output channel: Sentinel Chat never auto-loads remote content and neutralises leaking links; `POST /api/v1/check/text` for other hosts | 1, 6, 11, 16, 20 (in hosts that use it) |
| Q10 | P9 | **Your own document:** upload a PDF into Sentinel Chat, a live-model preset with a realistic toolset, a "what the model saw" view (including hidden text), then Navdeep's blind test | the real thing |
| Q7 | P6 | Data minimisation (`minimise`): placeholders instead of restricted values; the model provider never sees them | model-provider exposure |
| Q8 | P7 | Approval rate limit, batching, spike freeze, provenance and old-versus-new on the card | approval fatigue |
| Q9 | P8 | Audit export, signed head, third-party verify, anchoring | trust in the log |

## Phase details and QA

### Q2 Secrets and discovered credentials
Deliverables: `secrets.py` (pattern set, each with a test); the session index gains kind `secret` from any tool result; R2 blocks a secret to any destination including internal ones; R9 (new rule id, plain-English line in the site's rules data and docs) refuses a discovered secret used in a credential-like argument. A fixture document and a mock tool output that contain a fake key, for the scenario sweep.
QA: unit tests per pattern (true and false positives, including look-alike non-secrets such as order numbers); R2/R9 tests; mutation (remove the detector call: tests fail); no change in the scripted evaluation's false-block count.

### Q3 Precise flow rules
Deliverables: R8 with the slip flag and its plain-English reason; R2 and R8 agent-facing text without counts or kinds; R6 counting rule; registry/slip schema and API docs updated; a scenario where the agent paraphrases restricted data to the vendor on file (blocked or held only with R8 on).
QA: tests for each; mutation for R8; scripted evaluation: disclosures unchanged or lower, false blocks unchanged, approval workload reported; replay 0 diverged (R8 off for the quotation recordings, so they keep their meaning).

### Q4 Effects, not names
Deliverables: `effects.py` (path classes, SQL classifier, shell tokeniser), registry flag `irreversible`, slip fields for allowed tables and destructive operations, destination extraction for `cc`/`bcc`/`reply_to` and hostnames, matcher normalisation.
QA: table-driven tests (each pattern, each SQL form, each shell form, Unicode tricks, Indian formats, spaced digits); scenario for a destructive request held; the evaluation corpus gains the new representations as cases (reported on their own line, not mixed into the old figure).

### Q5 Tool supply chain
Deliverables: definition hash stored at classification and on first sight of a built-in tool; changed definition → tool hidden, alert on the console and in the log, re-approval by the officer; description scanner; annotations pre-fill the classification form.
QA: a test upstream whose tool description changes mid-session (hidden and alerted), a poisoned description (quarantined), annotations shown but never trusted.

### Q6 Output channel
Deliverables: chat reply renderer that never loads remote content and marks links; reply check against the session's restricted index and slip destinations; `POST /api/v1/check/text` with docs.
QA: a scripted chat whose model reply contains an image URL with stock figures in its query (neutralised, flagged); a reply with a harmless link to an allowed host (shown); API tests.

### Q10 Your own document (the live test)
Deliverables:
- `POST /api/v1/chat/{id}/documents` (officer token): accepts a PDF up to a size limit, validates it is a PDF, stores it in the run's data folder; the tool server reads uploaded documents alongside its fixtures (`uploads/<name>.pdf`).
- A preset "Work with your own document": slip with list/read documents, the customer database (restricted), e-mail (corp domain allowed, manager internal), web fetch and post, file write; live model only; the task is the user's own words.
- An upload control in the composer; the uploaded file is labelled **untrusted** (a user's document can be compromised: that is the test).
- Details shows "what the model was given": the exact text the PDF reader extracted, including text a person cannot see.
QA: with a PDF I make (not Navdeep's): upload, extraction, preset, a scripted run, a live run; size and type limits; the file never leaves the machine.
Then: **Navdeep uploads his own compromised PDF** and asks the live model (nemotron through the NVIDIA API) to work with it. We record the chat (recording file committed), report exactly what happened, whatever it is: the model ignored it, the model tried and Sentinel refused, or something got through (then that is the most important finding of all and goes in the log first).

### Q7 to Q9
As in the audit (§7 P6 to P8); QA lists written when the phase starts.

## Out of scope for now
Browser and IDE adapters, provider-side egress observation, multi-tenant identity, malicious-principal detection.
