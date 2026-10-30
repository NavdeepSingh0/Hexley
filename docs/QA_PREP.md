# Questionnaire round: answers to prepare

> **The name:** the product is now Hexley (`hexley.site`). The program's command (`python -m sentinel`), the repository and the code keep the old name until after judging, and recorded proof files say Sentinel because that is what was said then. If asked: "We renamed it this week; the code follows after the finale."

30 Oct 2026. Every answer below is something the repository or a test backs; the "Proof" line says where. If a question is not here, use the method in section 1 rather than inventing an answer.

## 1. How to answer anything (the method)
1. **Answer first, in one or two sentences.** No windup.
2. **Say the limit before they find it.** "It is a measurement on cases we wrote" lands better from you than from a judge.
3. **Give a number only with its n and what it is not.** "0 of 43, cases we wrote, not a guarantee."
4. **If you do not know: say so, and say what you would check.** "We have not measured that. I would test it by ..." is worth more than a confident wrong answer.
5. **Point at something they can see:** a page on the site, the console, the log.
6. **Do not argue about a competitor.** "They are good; here is where we differ and where they are ahead."

## 2. Facts to have ready (one glance)
- **What it is:** an MCP gateway. Every tool call is decided before it is forwarded, by ordinary code. **No AI makes any security decision.**
- **The idea:** an officer approves a *permission slip* (task, tools, where it may send, limits, lifetime). Rules R1 to R9 then check each action against the slip, what the session has read, and where it is going.
- **Rules in one line each:** R1 on the slip. R2 restricted values never leave. R3 an address only an untrusted document named is refused. R4 sensitive changes need the officer. R5 message budget. R6 the third refusal freezes the session. R7 after untrusted content, outside actions wait for the officer. R8 (Rule of Two) restricted data plus untrusted content, outside waits. R9 a credential found in data is never used or sent.
- **Evidence (always with n):** 0 of 43 on our corpus (95% interval 0 to 8%), no protection 43 of 43; 6 declared gaps; 0 of 28 valid actions wrongly blocked (0 to 12%); real model 13 of 13 leaked unprotected, 0 of 9 behind Hexley (0 to 30%); about 780 automated tests (781 passed at the last full run).
- **Benchmarks of 30 Oct (`docs/research/BENCHMARK_20261030.md`):** decision 7.5 to 140 microseconds, signed record about 2 ms, whole check 6 to 11 ms; matcher 775 of 775 documented formats recognised, 0 of 400 ordinary sentences flagged; 15 incident-shaped scenarios: 13 of 20 harmful steps refused, 6 held, 1 not stopped (the paraphrase gap), 0 of 20 benign steps wrongly refused; about 12 to 18 of 28 reported incidents stoppable in the complete state (43 to 64 percent), 10 out of reach by design.
- **Clients tested once each:** Claude.ai (sign-in, 27 Oct, and again 30 Oct: a real over-share blocked by R2), Claude Code (token, and the hook route in five real sessions).
- **Not done:** blind red team, adaptive attacker, ChatGPT, real GitHub or Gmail connector, storage that survives a restart, a deployed public site.

## 3. The problem and the idea
**What problem do you solve?** Agents can already send e-mail, read databases and edit files. A poisoned document can steer one, and every call it then makes can be individually allowed, so the leak is in the chain, not in any one call. Hexley limits the agent to the task a person approved. *Proof: console situation 1; README measured results.*

**Is this a real problem or a hypothetical one?** Real incidents with this shape: GitHub's MCP server (a public issue steered an agent into posting private repository content), EchoLeak, Supabase's MCP. We scored 28 incidents against Hexley (our own counterfactual reading, not a measurement): 11 of 28 stopped or held today (10 of them backed by a scenario that runs); about 12 to 18 of 28 in the complete state, the upper end only where the host also uses our reply check; 10 out of reach by design. *Proof: section 5 of `docs/research/BENCHMARK_20261030.md`; the incidents themselves are in `docs/research/PRODUCT_AUDIT.md` section 4.*

**Why not just tell the model not to leak?** An instruction is advice a poisoned document can talk it out of. In our recorded runs of one real model, the unprotected setup leaked in 13 of 13 usable runs. *Proof: README, real-model table.*

**Why not use another AI to judge the actions?** The judge reads the same text and can be talked into the same thing; research on adaptive attacks keeps breaking classifiers. Our decision is code you can read and test, and it fails closed: any error inside the decision is a block. *Proof: `docs/ARCHITECTURE.md` invariants; CLAUDE.md "no LLM in the decision path".*

**What is new here?** The ingredients are known (deterministic mediation, labels, taint, the Rule of Two). What we can defend is the combination at the tool boundary for agents you cannot modify: the approved task as input, restricted values followed from where they were read to where they go, and session-level rules, with measurements labelled honestly. *Proof: `docs/research/DIFFERENCES_CEDAR_FIDES.md`.*

**How is it different from AWS Cedar and Microsoft FIDES?** Cedar's AgentCore Policy decides on the caller, the tool and its parameters inside AWS's gateway; most policies are stateless, with opt-in session-aware ones you write per pattern. FIDES labels data inside an agent built with Microsoft's framework (experimental, Python) and hides untrusted data from the model. We sit outside the agent, so we work with agents nobody can modify; our input is the approved task plus what the session read. They are ahead on formal guarantees, managed identity and scale of evaluation, and FIDES hides data from the model, which we do not yet. *Proof: the doc above, with sources dated 30 Oct.*

## 4. How it works (technical)
**Walk me through one decision.** The agent calls a tool; the gateway authenticates the session token, looks up the tool's labels in the registry, extracts where the call sends data, and runs the rules in order. A block outranks a question, which outranks an allow. The decision is written to a signed log before anything is forwarded. *Proof: `src/sentinel/engine.py`, `gateway.py` (`mediate`).*

**How does it know what is restricted?** The officer classifies each tool once (read or send, trusted or untrusted output, public, internal or restricted, which arguments are destinations). Values returned by a restricted tool are fingerprinted (numbers, codes, dates, e-mail addresses, phone numbers, IDs, long passages), and so is anything that looks like a credential, from any tool. An unclassified tool is refused. *Proof: `registry.yaml`, `matcher.py`, `secret_scan.py`.*

**Isn't value matching easy to evade?** Yes for some forms, and we list them. A benchmark that generates 31 documented ways of writing a value found all 775 recognised and 0 of 400 ordinary sentences flagged; it also found four undocumented forms we missed (`dd-mm-yyyy`, `yyyy.mm.dd`, `yyyymmdd`, `FSD_14`), which we closed the same day. Still missed: hexadecimal, reversed digits, digits split by letters, a date written in words. The gaps: paraphrase, generalisation, approximation, letters for digits, a spelled-out address (6 declared gaps, all of which got through in our corpus). We close forms as we find them (Indian digit grouping, spaced digits, ids in digit groups). The answers to the paraphrase gap are the Rule of Two (hold for the officer), hardened mode (the agent cannot compose the message) and, planned, placeholders so the model never sees the value. *Proof: `docs/ADVERSARIAL_TESTS.md`, README declared gaps.*

**What is the Rule of Two?** Meta's idea: an agent should not combine untrusted input, access to private data and the ability to act outward without a check outside the model. R8 turns it on per slip: once a session has read restricted data and untrusted content, anything sent outside the internal destinations waits for the officer, even to a vendor on file. *Proof: `rules.py` R8, `tests/test_rule_of_two.py`.*

**What stops an agent from simply ignoring Hexley?** At the gateway it cannot: the tools are only reachable through it, and the downstream token never reaches the agent. For other clients the route is the client's own hook, which the client must call (see limits). *Proof: ARCHITECTURE invariants; `docs/THREAT_MODEL.md` section 6.*

**How does the audit log work and what does it not prove?** Each record is Ed25519-signed and hash-chained to the previous one, written and fsynced before the action is forwarded; a failed write refuses the action. Any changed, deleted, reordered or forged record fails verification and says where. It does not prove the events were true, and a truncated log is caught only if the verifier holds the earlier head. No secret values or raw arguments are stored. *Proof: console receipts (V, T, R); `audit.py`.*

**How does approval work?** The card shows the exact request. An approval is bound to a hash of the session, the tool and the exact arguments, is single-use and expires; silence is a denial; every other rule still runs after approval, so an approval can never excuse a leak. *Proof: `approvals.py`, `tests/test_r4.py`.*

**How do you connect to clients?** Claude.ai through OAuth sign-in (dynamic client registration and PKCE; the officer approves the slip with a code shown in the terminal); Claude Code through a token or through its own hook; a local model in our chat through Ollama. The token is bound to the confirmed slip and revoked when a session freezes. *Proof: the Integrations page and the proof files.*

**What if the client has other connectors, like Gmail?** Then those calls bypass a gateway, and we say so. For clients with hooks (Claude Code) the client itself asks Hexley before every tool call, whichever server it belongs to, and a Hexley that is down blocks the call. For chat apps without hooks, the honest answer is that other connectors are outside what Hexley sees unless Hexley is the only connector. *Proof: `/docs/connect-claude-code-hook`, the proof file of 30 Oct.*

**What about prompt injection in tool descriptions?** Each tool's definition is pinned by hash; a changed definition hides the tool until the officer approves it, and descriptions that read like instructions to the model are held. *Proof: `tool_pins.py`, 17 tests.*

**What about the model's reply, like an image link that carries data?** In our chat host the reply is checked and links or images that carry restricted values or point outside the slip are removed; other hosts can call a check endpoint. Hosts that do not ask are not covered. *Proof: `output_check.py`, Q6.*

**Latency and scale?** Measured on 30 Oct on one laptop with mock tools: a decision takes 7.5 to 140 microseconds, writing the signed audit record about 2 ms, and a whole check 6 to 11 ms at the median. A call through our gateway takes about 50 to 85 ms, about 32 ms of which is the general-purpose proxy library; we have not profiled the remainder. Throughput was 93 to 136 checks per second with 16 sessions in one process. That is not a scale claim: state is in memory in a single process, and the roadmap lists scale as unbuilt. *Proof: `docs/research/BENCHMARK_20261030.md`, `eval/benchmarks/`.*

**How many real attacks could it stop?** We scored the 28 incidents in our audit with one question: had this agent's tools passed through Hexley with a sensible slip, would the harmful step have been stopped or held? About 12 of 28 (43 percent) fully in the complete state, up to 18 (64 percent) if the hosts where leaks went through rendered replies also adopt our reply check; 11 today. The other 10 (36 percent) are outside what a tool-call gateway can see: browser agents, supply-chain malware, a server that misbehaves inside its own code, an infrastructure escape. It is a counterfactual reading by us, most of those incidents happened inside closed products, and ten of the eleven we count today are backed by a scenario that runs. *Proof: section 5 of the benchmark report.*

## 5. Evidence
**Can we trust your results?** Treat them as what they are: a corpus **we** wrote from the matcher's documented list and the routes we built, so it shows the system does what its documentation says, not that an attacker cannot find another route. Nobody who has not read the rules has attacked it yet, and an adaptive attacker is not done. The results files carry the commit, model, n and date. *Proof: `eval/results/`, the Limits page.*

**Why n = 9 for the real model?** 21 of the 90 lanes failed on the hosted API (rate limit) and are excluded and listed. Nine is small: the interval is 0 to 30%, which is why we say "a count, not a guarantee". *Proof: README.*

**What if the model just ignores the attack?** Then there is nothing to stop, and that happens with strong models: in our 15 live runs with a hosted model, the note was followed 0 of 5 when the task was only "summarise", and 4 of 5 when the task said "carry out the document's steps". Claude ignored it in the two runs we saw. Two things remain: weaker or local models do follow injections, and a helpful agent over-shares even with no attack (4 of 13 unprotected clean lanes sent restricted figures). On 30 Oct a real Claude.ai session asked for the stock figures was stopped by R2. *Proof: `docs/research/LIVE_RUNS_20261029.md`; the Hexley log of 30 Oct.*

**Did anything get through?** In the live runs, a copy of text into the internal `/out` folder was allowed, by design (the officer named it internal), and it held no restricted data. An injected instruction can still make an agent write harmless text into an internal place; that is a stated limit.

**How do you cover Claude.ai and ChatGPT, where there is no hook?** Honestly, weaker. In Claude Code the hook is enforced: Claude cannot skip it. On Claude.ai a connector runs on the vendor's servers and nothing asks us, so the person pastes a text into their preferences that tells Claude to ask Hexley first. That is advisory: nothing forces it, and the model is what an attacker steers. We measured it on Claude Code, not on Claude.ai, n=5 per condition on two models: with the text it asked first in 5 of 5 on each, also when a mail said to skip the check; without the text 0 of 5; when Hexley said no, the send did not run in 10 of 10 (about 72 to 100%). **We do not claim this stopped an attack:** both models ignored that injection with no Hexley at all. *Proof: `eval/compliance/`, `docs/PHASE_LOG.md` row F3b, D-057.*

**Does it make agents dumber or slower?** It limits actions, not thinking: 0 of 28 valid actions were blocked in our clean tasks (interval 0 to 12%). Some valid sends wait for the officer after untrusted content (3 of 12 in our corpus); we report that cost.

## 6. Limits and risks (say these yourselves)
**What does it not cover?** Anything that does not pass through it (other connectors, files attached to a chat, a client without a hook); paraphrase and other declared gaps; covert channels (timing, which allowed recipient); text drawn inside images (no OCR); names with a short address and no ID or phone; a model provider seeing what the model reads. *Proof: `docs/THREAT_MODEL.md`, the Limits page.*

**What if the officer is the attacker?** Out of scope: a malicious principal is a different product. The log still shows who approved what.

**Where is it not production-ready?** Identity is one token, state is in memory, the audit signing key sits next to the log, there is no export or outside anchor, and the tools behind it are mocks. The product roadmap lists what is left. *Proof: `docs/plans/PRODUCT_ROADMAP.md`.*

**Can an agent remove its own protection?** Writes to agent and editor configuration are refused, including common shell forms (redirection, `tee`, `sed -i`, `cp`, `mv`, `rm`, inline Python); a program that writes the file in a way the recogniser cannot read would not be caught. *Proof: `tests/test_effects.py`; the Limits page.*

## 7. Product, users, business
**Who is the customer?** Offices that run agents on sensitive records and cannot send them to a cloud service: government departments (the local-AI problem statements in SIH), finance, health. A local model through Ollama works in Hexley Chat; nothing leaves the computer.

**Is it only for one scenario?** No. The engine has no quotation logic. We show a second domain, an electoral office with a compromised circular and a synthetic voter roll, through the same rules. *Proof: the chat preset and `tests/test_general_tools.py`.*

**Compliance (DPDP, CERT-In)?** We do not claim compliance. The roadmap includes an incident report generated from the log and a mapping of features to DPDP and CERT-In requirements; not built.

**Business model and pricing?** The pricing page is illustrative and nothing is offered or sold. The idea on the roadmap is open core: self-host free, single sign-on, high availability and support paid. Not decided.

**How would a pilot work?** Two weeks in observe-only mode (decide and log what it would block, forward everything) in one department, then enforce; success measures agreed in advance. Observe-only is planned, not built.

**What is the roadmap?** Real connectors behind the gateway with Hexley holding the credentials (GitHub first), storage that survives a restart, officer sign-in and roles, a phone approval page, audit export, data minimisation, a blind red team, packaging. *Proof: the roadmap file.*

## 8. Team and process
**Who built what?** Navdeep led the product, design and testing with an AI coding assistant (Claude Code) writing and reviewing code under his direction. A teammate built the browser extension (Aadarsh Parmar); another is working on the mascot animation. Say plainly that AI assistance was used, and what you decided yourselves: the concept, the rules, what to claim and what not to.

**How did you make sure it works?** Phase-gated work: every phase had a checklist, tests first for anything security-relevant, a deliberate-break check for each rule (about 750 tests; each new rule was broken on purpose to confirm a test fails), real-browser runs, and a log of what was and was not exercised in `docs/PHASE_LOG.md`.

**What went wrong and what did you learn?** Examples you can tell truthfully: a false alarm that "Hexley allows leaks" turned out to be a leftover test server of ours (the program now refuses busy ports); an earlier note called a competitor "stateless" and the vendor's own page showed it was not (we corrected it); a hook-protection claim was too strong until we probed shell forms (we fixed it and wrote down what remains). We prefer finding these ourselves.

## 9. If you are stuck
- "We have not measured that; the nearest thing we have is [number with n]."
- "That is a real limit; it is on our Limits page."
- "Could you tell us the attack? We will run it in Scripted mode now and show what Hexley decides and why."
- Never guess a number, a date or a feature.
