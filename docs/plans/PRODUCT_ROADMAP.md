# From project to product: everything left

30 Oct 2026, the morning of the on-site build (starts 12:00; judging Sat 31 Oct 14:00). Navdeep's instruction: plan everything that is left to make Sentinel a viable product, not a project. Do not cut for feasibility here; open problems go to the research list. This plan follows `docs/research/PRODUCT_AUDIT.md`, `docs/plans/PRODUCT_PLAN.md` (Q2 to Q10, mostly built) and the 29 Oct conversation about coverage (other connectors and attached files bypass Sentinel).

---

## 1. Where we are

| Area | Today | Product-grade? |
|---|---|---|
| Decision engine (R1 to R9, matcher, secrets, effects, tool pinning, reply check) | Built, tested, mutation-checked, measured on our corpus | Close: the core is real |
| Coverage | One upstream tool server, our own mock tools. Other connectors in the same client and files attached to the client bypass Sentinel | **No.** The biggest gap |
| Clients | Claude.ai (sign-in) and Claude Code (token), once each; local model only in our own chat | Partial |
| Policy | Slips and tool classification by API and YAML; templates in code | No officer-facing builder |
| State | Sessions, slips, approvals, OAuth clients and chats live in memory; a restart loses them | **No** |
| Identity | One static API token, one officer code | **No** |
| Approvals | Card in the console and chat; no phone page, no notifications, no abuse limits | Partial |
| Audit | Signed, hash-chained, verifiable on the same machine | Partial: no export, no outside anchor |
| Install | `uv sync`, two `npm` builds, `sentinel up` from a clone | **No** package, no container, no offline bundle |
| Evidence | Our corpus (0/43), 30 recorded real-model runs, 15 live runs on 29 Oct | Ours only: no blind or adaptive attacker |
| Sentinel's own security | Fail closed, no secrets logged, token checks | Not reviewed as a target, and it becomes one once it holds credentials |

## 2. What "a viable product" means (the finish line)

An organisation can:
1. **Install** it on its own machine or server in under 15 minutes, with no internet if it chooses.
2. **Put every tool its agents use behind it**, real ones, with the credentials held by Sentinel and not by the agent; and see plainly what is not covered.
3. **Write policy without code**, try it in observe-only mode, then enforce it.
4. **Keep running**: state survives restarts, several officers sign in with roles.
5. **Approve** wherever the approver is, without the approval queue becoming an attack.
6. **Prove** what happened: export the log to its own systems and verify it independently.
7. **Know the error rates** on work like its own, from measurements, not claims.
8. **Trust Sentinel itself**: reviewed, hardened, honest about its limits.
9. **Adopt it**: documentation, a licence, a price, a pilot path, support.

Every item below serves one of these. "Done when" is the QA bar; nothing is called Tested until it passes.

---

## 3. Workstreams

### W1. Coverage: Sentinel is the only door
| # | Item | Done when |
|---|---|---|
| 1.1 | **Several upstreams behind one gateway** (`config/upstreams.yaml`; stdio and HTTP servers; tools named `<server>.<tool>`; a tool name offered by two servers is refused as shadowing; pinning and description scan per upstream) | Two real MCP servers behind one gateway; shadowing test; existing suite green |
| 1.2 | **Credential broker**: Sentinel holds each upstream's credentials (OAuth to Google or GitHub, tokens), encrypted at rest; the agent never receives them; a slip can narrow an upstream's scope | The agent's session has no route to a credential; R9 still refuses a discovered one; key never in logs |
| 1.3 | **Real connectors, configured not rebuilt**: GitHub (official MCP server), Gmail or real SMTP to a test mailbox, filesystem, Postgres, Slack; each with a registry classification preset | Each runs end to end with a real side effect on a test account; sink-equivalent check reads the real result |
| 1.4 | **Enforced client hooks**: Claude Code `PreToolUse` `http` hook (matcher `mcp__.*` and built-in tools) posts every call to `POST /api/v1/check`, `onFailure: block` (Claude Code v2.1.295 or newer); then research equivalents in Cursor, VS Code, Gemini CLI, Codex | A Claude Code session with Gmail-like tools from another server: the harmful call is denied by Sentinel, the honest one runs; a stalled Sentinel blocks |
| 1.5 | **Cooperative route for chat apps** (Claude.ai, ChatGPT): `sentinel_setup` returns the exact personal-preferences text to paste; `sentinel_check(connector, tool, args)` decides; labelled advisory | Compliance measured: n runs each for no preference, preference, preference plus an injection saying "skip the check"; reported with n |
| 1.6 | **Unseen-context mode**: slip flag for clients where Sentinel cannot see what the model read (attachments); the session is untrusted from its first call, so R3, R7 and R8 apply | Rule tests; the two-account demo with an attached PDF |
| 1.7 | **Coverage report**: per session, what goes through Sentinel and what does not (from the hook route, every tool name is visible, so unguarded tools can be listed) | Shown in the console and in the session record |
| 1.8 | **SDK middleware for teams that build their own agents** (Python and TypeScript: OpenAI Agents SDK, LangGraph, Claude Agent SDK hooks), same engine through `/api/v1/check` | One sample agent per SDK, blocked on the same scenario |
| 1.9 | **MCP beyond tools**: resources, prompts, sampling (a server asking the client's model to run a prompt), elicitation | Each mediated or refused by default, with tests |
| 1.10 | Browser agents (navigation and form fills as actions) | Research first (§5) |

### W2. Policy an officer can write
| # | Item | Done when |
|---|---|---|
| 2.1 | **Slip builder screen** (objective, tools, destinations, internal destinations, data classes, budgets, lifetime, Rule of Two, unseen context), validated live against the registry | An officer builds a slip with no YAML; invalid slips explain why |
| 2.2 | **Tool classification screen**: new tools listed with MCP annotations pre-filled (never trusted alone), pinned-definition diff on change | A new upstream's tools classified by clicking |
| 2.3 | **Template library by domain**: procurement, electoral office, health records, finance, HR, citizen grievances, developer operations | Each template has a scenario that runs in all three lanes |
| 2.4 | **Observe-only (shadow) mode**: decide and log "would have blocked", forward everything | Toggle per slip; log and dashboard show would-block counts |
| 2.5 | **Slip widening mid-session**: the agent's or user's request for more becomes an approval, never a silent change | Test: a widened slip is a new signed version in the log |
| 2.6 | **Policy as files**: export and import slips, templates and classifications as YAML for review in git; versions and diffs | Round trip test |
| 2.7 | **Policy test runner**: run a scenario or a recorded session against a draft slip before enforcing it | CLI and screen |

### W3. Platform foundations
| # | Item | Done when |
|---|---|---|
| 3.1 | **Persistence**: SQLite by default, Postgres option; slips, sessions, approvals, OAuth clients and tokens, registry overlays, pins, chats; migrations | Restart mid-session: the session, its taint and its pending approval survive |
| 3.2 | **Officer identity**: OIDC single sign-on; local accounts for offline sites | Sign-in tests; no shared token |
| 3.3 | **Roles**: admin, policy author, approver, auditor, viewer; separation of duties (the author of a slip cannot be its only approver) | Permission tests per endpoint |
| 3.4 | **Organisations** (several tenants on one install) | Isolation tests |
| 3.5 | **Scoped API keys** for hosts and hooks, rotation, expiry | Replaces the static token |
| 3.6 | **Key management**: signing keys in the OS key store, a KMS or an HSM; rotation that keeps old logs verifiable | Rotation test |

### W4. Approvals as a workflow
| # | Item | Done when |
|---|---|---|
| 4.1 | **Phone approval page** (one card, the exact action, approve or deny, signed) | Works on a phone through the tunnel |
| 4.2 | **Notifications**: e-mail, Slack or Teams, webhook; SMS or WhatsApp later | A pending approval reaches a person outside the console |
| 4.3 | **Abuse limits (audit P7)**: rate limit per session, batching of similar requests, a spike freezes the session | Flood test: the harmful request is not lost in noise |
| 4.4 | **The card shows provenance**: which untrusted content was read before this request; for a change, old beside new | Screens and tests |
| 4.5 | **Escalation and timeouts**; two-person rule for chosen actions; delegated approvers | Tests |

### W5. Data protection depth
| # | Item | Done when |
|---|---|---|
| 5.1 | **Data minimisation (audit P6)**: restricted values reach the model as placeholders; the gateway fills them in only at exits allowed to receive them; the model provider never sees the raw value | Test: no restricted value in any model request; a paraphrase of a value the model never saw is impossible |
| 5.2 | **Record fingerprints**: combinations of fields from one restricted row (name with ward or street) are caught, closing the voter-roll gap | The declared-gap test flips; false-positive check on clean summaries |
| 5.3 | **Indian identifiers**: Aadhaar (with its checksum), PAN, voter ID, IFSC, GSTIN, UPI IDs, Indian phone forms | Table tests with true and false positives |
| 5.4 | **Indic text**: Devanagari and other Indian digits, number words in Hindi, lakh and crore everywhere | Matcher tests |
| 5.5 | **OCR for images in PDFs**, and readers for DOCX, XLSX and images | Hidden text drawn as an image is extracted and labelled untrusted |
| 5.6 | **Reply check SDK** for hosts other than ours | One host integration sample |

### W6. Audit, visibility, compliance
| # | Item | Done when |
|---|---|---|
| 6.1 | **Audit export (audit P8)**: JSON lines plus a signed head; `sentinel audit verify --head` for a third party | Verified on another machine |
| 6.2 | **Outside anchor** of the chain head (a second store or a timestamp service), so a truncated log is caught | Truncation test |
| 6.3 | **SIEM export** (syslog, OpenTelemetry) | Events visible in a sample collector |
| 6.4 | **Dashboard**: decisions by rule, approval load, frozen sessions, top destinations, would-block counts | Screens from real data |
| 6.5 | **Incident report per session**: what was read, what was tried, what was stopped, what left; ready for an incident notice (CERT-In's 6-hour reporting, a DPDP breach notice) | Generated from the log only |
| 6.6 | **Compliance mapping**: DPDP Act 2023, CERT-In directions, ISO 27001, NIST AI RMF, OWASP Top 10 for LLM and agentic applications, EU AI Act logging | A document, each line traceable to a feature |
| 6.7 | Retention and deletion policy for logs and uploads | Configurable, tested |

### W7. Evidence and quality
| # | Item | Done when |
|---|---|---|
| 7.1 | **Blind red team** (people who have not read the rules) and an **adaptive attacker** that retries after each refusal | Results on their own line |
| 7.2 | **Standard benchmark** (AgentDojo) through Sentinel | Results file with n |
| 7.3 | **More models**: cloud and local (qwen3, llama, gemma, an Indian-language model) | Per-model table |
| 7.4 | **False positives on realistic work**, from shadow-mode logs | Rate with n |
| 7.5 | **Evaluation in CI** on every commit; results compared with the last file | Regressions fail the build |
| 7.6 | **Latency**: time added per call (p50, p99) under load | Number with n |
| 7.7 | Published method and limits page | On the site |

### W8. Package, deploy, operate
| # | Item | Done when |
|---|---|---|
| 8.1 | **One-command install**: `pipx install sentinel` (site and console built into the wheel) | Fresh machine, one command |
| 8.2 | **Container**: image plus compose (Sentinel, optional Ollama, optional Postgres) | `docker compose up` works on a clean machine |
| 8.3 | **Offline bundle** for air-gapped sites (wheels, site build, a model) | Install with the network off |
| 8.4 | Runs as a service (Windows service, systemd); health and readiness endpoints; backups; upgrade with migrations | Upgrade test from the previous version |
| 8.5 | **Scale**: stateless gateway workers over the shared store; load test | Throughput and latency numbers |
| 8.6 | TLS, API rate limits, versioned releases, changelog, SBOM, signed artefacts | Release checklist passes |

### W9. Securing Sentinel itself
Once Sentinel holds every credential (1.2), it is the most valuable thing on the network.
| # | Item | Done when |
|---|---|---|
| 9.1 | Threat model of Sentinel as a target (credential vault, policy tampering, approval spoofing, log deletion) | Document, each threat mapped to a control or a stated gap |
| 9.2 | Security review of `gateway`, `engine`, `rules`, `oauth`, `egress`, the broker | Findings fixed or recorded |
| 9.3 | Fuzzing of the matcher, effects and secret-scan parsers | No crash, no fail-open |
| 9.4 | Dependency scanning, least privilege for the process, an external penetration test | Reports |

### W10. The sovereign stack (governments and regulated offices)
The SIH problem statements ask for local AI that a department runs itself. This is where Sentinel can be the whole product, not an add-on, because there is no outside connector to go around.
| # | Item | Done when |
|---|---|---|
| 10.1 | **Sentinel Workspace**: Sentinel Chat as an on-premises agent workspace with a local model (Ollama or vLLM), uploads, department templates, all tools behind the gateway | Runs on one server with the network off |
| 10.2 | **Hindi and regional-language interface**, and Indic detectors (W5.3, 5.4) | Screens and tests |
| 10.3 | **Local-model evaluation**: which local models follow injections, measured, so the risk case is evidence | Per-model table |
| 10.4 | Hardware sizing guide (CPU-only, one GPU) | Measured response times |

### W11. Product surface and adoption
| # | Item | Done when |
|---|---|---|
| 11.1 | **Onboarding wizard**: connect the first agent and the first real tool in five minutes | Timed with someone who has not seen it |
| 11.2 | **One app** under one sign-in: console, chat, policies, approvals, dashboard, settings | |
| 11.3 | **Docs**: install, administration, policy guide, API reference (OpenAPI), security whitepaper, limits | |
| 11.4 | **Licence and price**: e.g. open core (self-host free; single sign-on, high availability, support paid) | Decided, then on the site without "illustrative" |
| 11.5 | **Pilot path**: two weeks observe-only in one department, then enforce; success measures agreed in advance | A pilot plan document |
| 11.6 | Support channel, trust page, terms and privacy notice | |

---

## 4. Order

### Tier 0: before code freeze (Sat 31 Oct 10:00)
Roughly 20 working hours remain. The list below is about 25, so the cut line is marked. Order is by what changes the answer to "would anyone use this?"

| Order | Phase | Items | Hours | Cut line |
|---|---|---|---|---|
| F1 | Enforced hook route: `/api/v1/check` for any connector's tool, Claude Code `http` hook, unseen-context mode, coverage list | 1.4, 1.6, 1.7 | 3 | Must |
| F2 | Several upstreams and one real connector with Sentinel holding the credential (GitHub recommended: a fine-grained token on a test repo) | 1.1, 1.2 (minimal), 1.3 (one) | 5 | Must |
| F3 | Cooperative route for Claude.ai: `sentinel_setup`, `sentinel_check`, preferences text, compliance runs (Navdeep runs the Claude.ai part) | 1.5 | 2 | Must |
| F4 | Two-account demo, rehearsal ×3, fallback video, pitch aligned with the coverage story | — | 3 | Must |
| F5 | Persistence (SQLite) for slips, sessions, approvals, OAuth | 3.1 | 3 | Should |
| F6 | Observe-only mode | 2.4 | 1 | Should |
| F7 | Phone approval page, rate limit, provenance on the card | 4.1, 4.3, 4.4 | 2 | Should |
| F8 | Audit export and third-party verify | 6.1 | 1 | Should |
| F9 | Slip builder and tool classification screens | 2.1, 2.2 | 3 | Could |
| F10 | Container and compose, fresh-machine test | 8.2 | 2 | Could |

### Tier 1: two weeks after the finale (an alpha a pilot can install)
3.1 to 3.5 identity, roles, Postgres; 4.2 notifications; 5.1 minimisation, 5.2 record fingerprints, 5.3 and 5.4 Indian identifiers and Indic text, 5.5 OCR; 6.2 to 6.5 anchor, SIEM, dashboard, incident report; 7.1, 7.3, 7.5, 7.6 blind and adaptive red team, more models, CI evaluation, latency; 8.1, 8.3 package and offline bundle; 9.1 to 9.3 Sentinel's own threat model, review, fuzzing; the rest of 1.3 connectors.

### Tier 2: one to three months (first pilot)
1.4 hooks in other clients, 1.8 SDK middleware, 1.9 MCP beyond tools; 2.3, 2.5 to 2.7 templates, slip widening, policy files, policy test runner; 3.4 organisations, 3.6 key management; 4.5 escalation; 6.6, 6.7 compliance mapping, retention; 7.2, 7.4 AgentDojo and false positives from shadow logs; 8.4 to 8.6 service, scale, release process; 9.4 external penetration test; W10 sovereign stack; W11 onboarding, one app, docs, licence, pilot.

### Tier 3: later
1.10 browser agents; covert-channel defences; certifications; a shared library of templates and tool classifications.

---

## 5. Research: problems nobody has solved yet (where we innovate)
1. **Enforcement inside closed chat apps** without relying on the model's cooperation: enterprise admin controls over connectors, an organisation-level network egress point for connector traffic, a browser extension that observes. Which of these can actually guarantee mediation?
2. **Meaning, not strings, without a model in the decision**: paraphrase and summary leaks. Minimisation (5.1) is the strongest lead: if the model never sees the value, it cannot paraphrase it. What fraction of real tasks survive minimisation?
3. **Task-scoped credentials**: minting a downscoped token per slip at each upstream (GitHub fine-grained tokens per repo, Google scopes per task) so even a bypass holds no broad power.
4. **Approval design that resists fatigue**: measured with real approvers; when does batching hide an attack?
5. **Drafting slips from plain language** with a model, while the decision stays deterministic: the model proposes, the officer confirms, the validator checks.
6. **Detecting other connectors in a session** from what a client exposes (hook payloads, tool lists).
7. **Covert channels** through allowed actions: timing, counts, choice of allowed recipient, encoding in innocent fields.
8. **Names and addresses** as restricted data without flagging every honest summary.

## 6. Method (unchanged)
Phase-gated: each phase has its done-when list; QA pass, log in `docs/PHASE_LOG.md`, commit locally, next. Three QA attempts, then stop and discuss. Every phase re-runs the full suite, the scripted evaluation, replay and the scenario sweep. Honesty rules hold: Tested, Should work or Planned on every claim; every number with n and its caveat; no "100% secure". Push only on Navdeep's word.

## 7. Decisions for Navdeep
1. The real connector for F2: GitHub (a token, recommended) or Gmail (Google Cloud sign-in setup and a test account).
2. Which customer leads the pitch: governments running their own agents (W10, strongest coverage story) or organisations using Claude.ai and ChatGPT (larger market, weaker guarantee today).
3. Licence model (11.4), when there is time.
