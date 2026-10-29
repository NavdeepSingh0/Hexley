# Sentinel product audit: what it does, what it misses, what to build

29 Oct 2026. Written after Navdeep asked to question the product itself rather than its looks. Sources: the code on `main` (read for this audit), `docs/THREAT_MODEL.md`, the research files in `../.agents/tasks/` (01 competitive landscape, 02 academic research, 03 real incidents and benchmarks, 05 build research), and a small set of web sources listed at the end. Nothing here is a measurement unless it says so.

---

## 1. What Sentinel is today (the backend, as built)

Sentinel is an MCP gateway. An AI client connects to it instead of to the tool server; every tool call is decided before it is forwarded, by ordinary code.

| Piece | What it does | Where |
|---|---|---|
| Permission slip | Task, allowed tools, allowed destinations (e-mail domains, URL prefixes, folders), internal destinations, message limit, lifetime. The session token is bound to the confirmed slip. | `contracts.py`, `confirm.py` |
| Tool registry | Each tool is labelled: read/write/send, outbound, consequential, output integrity (trusted/untrusted), output confidentiality (public/internal/restricted), which fields to fingerprint, which arguments are destinations. An unknown tool is refused. The officer can classify new tools. | `registry.py`, `config/registry.yaml` |
| R1 | Tool and destination must be on the slip; URL query strings count (a `fetch_url` with data in the query is checked like a send). | `rules.py` |
| R2 | Values read from a restricted tool (numbers ≥ 100, codes, dates, e-mails, phones, IDs, 8-word shingles of prose) may not appear in an outbound call, except to a destination the slip calls internal. | `matcher.py`, `rules.py` |
| R3 | A destination that appeared only in untrusted content is refused. | `rules.py` |
| R4 | Sensitive changes (bank details) wait for the officer's approval of that exact call. | `rules.py`, `approvals.py` |
| R5 | Message limit per slip. | `rules.py` |
| R6 | Third denial freezes the session and revokes its token. | `rules.py` |
| R7 | After the session read untrusted content, a consequential action waits for the officer unless it goes only to an internal destination or a vendor on file. | `rules.py` |
| Audit | Ed25519-signed, SHA-256 hash-chained log, written before anything is forwarded; a failed write refuses the action. Demo tamper and restore. | `audit.py` |
| Hardened mode | The agent gets one tool that sends a fixed message to a recipient Sentinel resolves from trusted records. | `egress.py` |
| Clients | OAuth sign-in (Claude.ai, tested once) and header tokens (Claude Code, tested once). | `oauth.py`, `connect.py` |
| Hosts and evidence | Sentinel Chat (a live model through the gateway), runs and replay, eval harness. | `chat.py`, `runs.py`, `eval/` |

What it mediates: only `tools/list` and `tools/call` (`gateway.py` hooks `on_list_tools` and `on_call_tool`). One upstream tool server. Mock tools.

---

## 2. Why Sentinel needs to exist (the case, tested against the evidence)

- Every major agent data-leak of 2024 to 2026 in `03-attacks-incidents-benchmarks.md` has the same shape: untrusted content enters the context, the agent reads private data it is allowed to read, and it writes to a place the attacker can reach. Each call was allowed on its own; the chain was the attack (EchoLeak, ForcedLeak, SalesBleed, GeminiJack, ShadowLeak, AgentFlayer, GitHub MCP, Supabase MCP).
- Vendors keep patching one sink at a time and the class keeps coming back (ForcedLeak, then SalesBleed on the same product a year later through DNS). OpenAI says prompt injection in browser agents may never be fully solved.
- Meta's "Agents Rule of Two" (Oct 2025) and Simon Willison's "lethal trifecta" state the same principle Sentinel enforces: an agent should not combine untrusted input, private data and the ability to act outward in one session without a check outside the model.
- Our own M0 spike (26 Oct): agents leaked the stock figures **with no injection at all** (ultra-550B in 4 of 30 clean runs; smaller models far more). The threat is also the helpful agent that over-shares.
- The literature agrees on what works (02-academic §2.1): deterministic mediation outside the model, authority fixed from the trusted request before untrusted data is read, labels on data checked at the sinks. Detectors and LLM judges break under adaptive attack.

**So the need is real, and the approach is the one the evidence supports.** The question is not whether, but how complete.

## 3. The USP, stated precisely

Each piece exists somewhere (01-competitive §1): Cedar policies at AWS AgentCore, FIDES labels in Microsoft's Agent Framework, Invariant two-step flow rules, Keycard task-scoped tokens, many MCP gateways. What we found nowhere as one deterministic gateway that works with **agents you cannot modify**:

1. a task contract (the slip) as the policy input, confirmed by a person before untrusted data is read;
2. value provenance across tools (restricted values tracked from where they were read to where they try to go; destinations tracked to the untrusted content that named them);
3. session-level flow rules (taint, budgets, freeze), not just per-call allow/deny;
4. evidence: signed log, decisions explained in one sentence, measurements with n and caveats.

That combination is the wedge. It is defensible only if we close the gaps below, because the large vendors are moving here.

---

## 4. The real incidents: how many would Sentinel have stopped?

Assumption for every row: the same agent's tools went through Sentinel with a sensible slip. Most incidents happened inside closed products (Copilot, Agentforce, Gemini) where nobody can insert a gateway; this is a counterfactual about the mechanism, not a claim that Sentinel would have been deployable there.

Legend: **Stopped** = a rule we have today blocks or holds the harmful step. **Partial** = blocks only with a specific slip or classification, or blocks part of the chain. **No** = outside what Sentinel sees.

| # | Incident | Today | Why (today) | After this plan | What closes it |
|---|---|---|---|---|---|
| 1 | Slack AI (2024) | No | Exfiltration through a link the model *rendered in its reply*; not a tool call | Stopped in our host | P5 output channel |
| 2 | ChatGPT Operator | Partial | R1 refuses off-slip domains if browser navigation is a classified tool; PII typed into forms is not restricted data | Partial | Browser adapter (not planned) |
| 3 | MCP tool poisoning | Partial | R1 refuses off-slip file tools; the poisoned description itself is passed through unread | Stopped | P4 description scan and pinning, P2 secret detection |
| 4 | WhatsApp MCP rug pull | Partial | R1 refuses a recipient not on the slip; the swapped tool is not noticed | Stopped | P4 pinning |
| 5 | GitHub MCP toxic flow | Stopped | R7 holds the public PR after the untrusted issue; R2 shingles catch copied private text if the repo read is restricted | Stopped | (R7 also holds legitimate PRs: P1 makes it precise) |
| 6 | EchoLeak (M365 Copilot) | No | Rendered image URL in the reply | Stopped in our host | P5 |
| 7 | Supabase MCP | Partial | One `execute_sql` tool reads and writes; tokens are not recognised as secrets | Stopped | P2 secrets, P3 SQL effect |
| 8 | Replit deletes prod DB | Partial | Only if the destructive tool is off the slip; no notion of destructive or irreversible | Stopped (held) | P3 destructive operations |
| 9 | Amazon Q wiper prompt | Partial | Shell through Sentinel is approval-only; the agent's own shell bypasses | Stopped if the shell is routed | P3 shell effect |
| 10 | CurXecute / MCPoison | Partial | A write outside the slip's folders is refused; agent config files are not a protected class | Stopped (CurXecute); MCPoison is client-side | P3 protected paths |
| 11 | AgentFlayer | No | Image URL in the reply | Stopped in our host | P5 |
| 12 | Perplexity Comet | Partial | Browser agent; same as 2 | Partial | Browser adapter |
| 13 | Nx s1ngularity | No | Malware ran the AI CLIs outside any gateway | No | Out of scope |
| 14 | ShadowLeak | Stopped | `fetch_url` to an unknown domain is refused (R1); PII in the query string is R2 | Stopped | (needs Sentinel where the agent runs, server-side) |
| 15 | postmark-mcp BCC | No | The leak is inside the server's own code | No | Sentinel-owned adapters (future) |
| 16 | ForcedLeak | No | Image URL in the reply to an expired allow-listed domain | Stopped in our host | P5 |
| 17 | Atlas omnibox | No | The instruction came through the user channel | No | Out of scope |
| 18 | GTG-1002 espionage | No | The user is the attacker | No | Out of scope |
| 19 | Google Antigravity | Partial | Refused if the logging site is not on the slip; `cat .env` is not recognised as a secret read | Stopped | P2, P3 |
| 20 | GeminiJack | No | Image URL in the reply | Stopped in our host | P5 |
| 21 | Shai-Hulud lineage | No | Supply-chain malware; config hooks | Partial | P3 protected paths |
| 22 | ClawHavoc skills | No | Malicious skill code | Partial | P4 pinning |
| 23 | Comment and Control | Stopped | R7 holds the PR comment after reading an untrusted PR (and in CI nobody approves, so it never posts) | Stopped, precisely | P2 blocks only the comment that carries a secret |
| 24 | PocketOS wipe in 9 s | No | A token found in a file was used to delete a volume; nothing knows the token was never issued to the task | Stopped | P2 discovered credentials, P3 destructive |
| 25 | OpenAI agents and Hugging Face | No | Infrastructure escape | No | Out of scope |
| 26 | Amazon Kiro | Partial | Config write refused only if outside the slip's folders; the IDE's own fetch bypasses | Partial | P3 protected paths |
| 27 | Flowise | Partial | Sentinel's own API needs a token; the platform itself was open | Partial | (deployment) |
| 28 | SalesBleed | No | Rendered output and DNS | Partial | P5, hostnames as destinations |

**Today: 3 stopped, 11 partial, 14 not stopped** (of 28). After the plan: about **16 stopped** (5 of them only in hosts that use Sentinel's output check), **7 partial**, **5 out of scope** (13, 15, 17, 18, 25). The single largest gap is not a rule: **7 of 28 leaked through the model's rendered reply**, which a tool gateway never sees.

---

## 5. What we did not think through

Ordered by how much each weakens the product.

1. **The rendered reply is an exit.** Markdown images and links in the model's answer leak data the moment a client renders them (7 incidents). Sentinel sees tool calls only. In our own chat host we can control rendering; for other hosts we can offer a check they call before rendering.
2. **Secrets and credentials inside tool output are not recognised.** API keys, tokens, private keys, passwords, connection strings returned by any tool are treated as ordinary text unless that tool was labelled restricted. A key found in a file can be sent out or used (PocketOS, Supabase, Comment and Control, Antigravity).
3. **Tools are identified by name only.** A tool's description and schema are passed to the model unread and unpinned: poisoned descriptions and silent changes (rug pulls) are invisible.
4. **Effects are not normalised.** `cat .env` and `read_file .env` are different tools to Sentinel; a SQL tool that reads and writes is one tool; nothing knows that a delete is irreversible or that `.cursor/mcp.json` is a dangerous place to write.
5. **The model provider sees the restricted data.** When the agent reads the stock register, the values go to the model provider as a tool result. Sentinel protects the exits, not the model's input. For a government or defence buyer that is itself the leak. Two answers: a local model, or never giving the model the raw value (a placeholder the gateway resolves only at allowed exits).
6. **Value matching is literal.** Paraphrase, derived values ("about 2.4k"), numbers under 100, Indian formats (1,15,000; 1.15 lakh), digits spaced or spelled out, splitting across messages, Unicode look-alikes and zero-width characters inside addresses all pass R2.
7. **The denial message coaches the attacker.** R2 tells the agent how many values matched and of which kinds ("quantity, depot code"). A compromised agent learns exactly what to reword.
8. **R7 is coarse.** It holds every consequential action after any untrusted read: right for safety, costly in practice (in CI nobody approves, so a code-review bot can never comment). It exempts vendors on file and internal destinations, which is where a paraphrased leak to the vendor would go.
9. **Approvals can be abused.** No rate limit, no batching, no fatigue signal, no old-versus-new view for a change. An injection can flood the officer with harmless requests before the harmful one.
10. **Freeze is a denial-of-service lever.** Three induced denials freeze legitimate work; a typo-level R1 denial counts the same as a leak attempt.
11. **The slip is fixed for a session that drifts.** Multi-turn chat asks for new things; nobody designed how a slip is widened safely.
12. **User-supplied content.** Data the user types or uploads is not labelled. An uploaded document is untrusted even though the user brought it (exactly Navdeep's live test).
13. **MCP beyond tools.** Resources, prompts, sampling (a server asking the client's model to run a prompt) and elicitation are not mediated. MCP tool annotations (`readOnlyHint`, `destructiveHint`, `openWorldHint`) exist and are not used, not even as defaults.
14. **One upstream.** Real deployments connect several servers; tool-name shadowing between servers is an attack (Invariant).
15. **The audit log trusts its own machine.** Key on the same disk; no export; no external anchor of the chain head.
16. **Evaluation is ours.** Corpus written by people who know the rules; one model, one scenario for the real recordings; no blind attacker; no adaptive round; no standard benchmark (AgentDojo).

## 6. Assumptions that do not hold in a real deployment

| We assumed | In reality |
|---|---|
| The agent has no other way out (complete mediation) | Agents hold shells, browsers, their own fetch and other servers. It must be a deployment rule, checked where possible |
| Restricted data is structured values | Most secrets are prose, documents, images and credentials |
| Tools are well-typed with explicit destination arguments | Real e-mail has `cc`, `bcc`, `reply_to`; real APIs hide destinations in nested JSON and IDs |
| One officer, attentive, at a desk | Several approvers, fatigue, 2 a.m., phones |
| Tool definitions are stable and honest | Descriptions can carry injections and change after approval |
| The model only acts through tools | Its reply is rendered, and rendering fetches URLs |
| Mocks and a mail sink measure safety | Real side effects: drafts, outboxes, retries, webhooks, logs at the provider |
| The model will follow the injection in our demo | Frontier models increasingly refuse; a real test may show "nothing happened", which is also a result |

---

## 7. Improvements, designed

Each is deterministic (no model in the decision), testable, and keeps the existing rules.

### P1. Precise flow rules (the Rule of Two as an invariant)
- **R8 trifecta:** a session that has read restricted data and untrusted content may send free text outward only to internal destinations; anything else is held for the officer, including a vendor on file. A slip setting (`strict_flows`), on by default for new presets, off for the measured quotation demo so its numbers keep their meaning. Closes the paraphrase-to-the-vendor path that R2 and R7 both miss.
- **Generic denials to the agent:** the agent is told "contains restricted data from this task; send it without that information", never the count or kinds. Detail goes to the officer and the log (the ARM finding).
- **Freeze counts intent:** R6 counts denials that look like an attempt (R2, R3, R8 refusals and repeated identical refusals), not a first R1 refusal of an off-slip tool. Threshold becomes a slip setting.

### P2. Secrets and discovered credentials
- A built-in detector runs on **every** tool result regardless of labels: private keys, AWS/GCP/Azure keys, GitHub/Slack/Stripe tokens, JWTs, bearer tokens, `password=`, connection strings, `.env`-style `KEY=value` lines. Found values join the restricted index as kind `secret`.
- R2 blocks any outbound call carrying one (even to internal destinations: a credential is never data to share).
- **New R9:** a secret found in data is never usable as a credential: an argument named like a credential (`token`, `api_key`, `authorization`, `password`, headers) carrying a discovered secret is refused ("this credential was found in data, it was not issued to this task").

### P3. Effects, not names
- **Protected paths:** any argument that is a path is checked against protected classes (agent and IDE config: `.cursor/`, `.claude/`, `.vscode/`, `.kiro/`, `mcp.json`, `*.code-workspace`, git hooks; secrets: `.env*`, `.ssh/`, `*.pem`, `id_rsa*`, `credentials`): writes refused, reads mark the session as having read secrets.
- **Destructive operations:** a registry flag `irreversible` plus recognisers for SQL (`DROP`, `DELETE`/`UPDATE` without `WHERE`, `TRUNCATE`, `ALTER`) and shell (`rm -r`, `mkfs`, `dd`, cloud `delete`) → held for the officer; a slip may forbid them outright.
- **SQL and shell normalisation:** a SQL statement is classified read/write/DDL with its tables; a slip may name allowed tables and whether writes are allowed. Shell commands are tokenised; `cat`/`type`/`less` of a protected path is a secret read; `curl`/`wget` with a URL is an outbound destination.
- **Destinations everywhere:** e-mail `cc`/`bcc`/`reply_to`; any hostname in any argument of an outbound tool (DNS exfiltration through `data.attacker.example`).
- **Normalisation hardening for the matcher:** Unicode NFKC, zero-width removal, look-alike folding in addresses; Indian digit grouping (1,15,000) and lakh/crore words; spaced digits.

### P4. Tool supply chain
- **Pin** each tool's full wire definition (name, description, input schema, annotations) by hash when it is first classified. A changed definition hides the tool and raises an officer alert until it is re-approved (rug pull).
- **Scan** descriptions for instruction-like content (imperatives aimed at the model, "ignore", "do not tell the user", references to other tools, secret paths): the tool is quarantined until the officer looks.
- **Annotations as defaults:** an unclassified tool's MCP annotations pre-fill the officer's classification form (never trusted on their own).

### P5. The output channel
- In Sentinel Chat, the model's reply is rendered as text with links shown, never auto-loading remote images. Any URL in a reply that carries restricted values (R2 index) or goes to a host outside the slip is neutralised and flagged.
- `POST /api/v1/check/text`: any host can ask Sentinel, before rendering, whether a reply carries this session's restricted values or links to unknown hosts. The same index, the same reasons.

### P6. The model never sees the secret (data minimisation)
- Slip setting `minimise`: restricted values in tool results are replaced by stable placeholders (for example `⟦stock#1⟧`) before they reach the model; an outbound call that contains a placeholder is resolved by the gateway only for destinations allowed to receive restricted data, otherwise refused. The model provider never receives the raw value, and a paraphrase of a value the model never saw is impossible. Trade-off: tasks that need to reason about the values (is stock above 500?) lose them; the slip says which fields may be shown.

### P7. Approvals that resist abuse
- Rate limit per session; similar requests batched; a spike of approval requests freezes the session.
- The card shows where the request came from (which untrusted content was read before it) and, for changes, the old value beside the new one.

### P8. Audit you can take elsewhere
- Export the log (JSON lines and a signed head) and an `audit verify --head` command a third party can run; anchor the head periodically to a second location.

### P9. Real evidence
- A blind red team (people who have not read the rules), reported on its own line.
- **Navdeep's own compromised PDF**, never seen by the model or by us, uploaded into Sentinel Chat and run against the live model. Whatever happens is reported.
- AgentDojo through Sentinel (plan in 03 §2.3), when model quota allows.

### Not planned (and why)
Browser and IDE adapters (large), Sentinel-owned provider adapters that observe real recipients (postmark-mcp), multi-tenant identity, malicious-principal detection (a different product).

---

## 8. Sources used beyond the local research files

- Meta AI, "Agents Rule of Two" (Oct 2025): [ai.meta.com/blog/practical-ai-agent-security](https://ai.meta.com/blog/practical-ai-agent-security/); discussion: [Simon Willison](https://simonw.substack.com/p/new-prompt-injection-papers-agents).
- MCP tool annotations are hints, not security: [MCP bundles guide](https://www.mcpbundles.com/guides/tool-annotations), [Speakeasy](https://www.speakeasy.com/docs/mcp/build/gram-functions/tool-annotations).
- Tool pinning and rug pulls: [Zuplo](https://zuplo.com/blog/remote-mcp-server-rug-pull/), [ReversingLabs](https://reversinglabs.com/blog/mcp-rug-pull-attack-worries), [hash the wire definition](https://dev.to/luckypipewrench/your-mcp-servers-tool-descriptions-are-an-attack-surface-37pj).
- Placeholders instead of raw values: [IBM community](https://community.ibm.com/community/user/blogs/mohammed-ali-shaik/2026/03/25/protecting-pii-in-agentic-frameworks-the-mask-rehy), [mcp-pvp](https://app.readytensor.ai/publications/securing-ai-agent-pipelines-a-privacy-vault-architecture-for-the-model-context-protocol-Zb7okN2XJvpL).
- Hidden text in PDFs (white, tiny, off-page, annotations; text extractors pass it on, OCR does not): [arXiv 2509.10248](https://arxiv.org/pdf/2509.10248), [document attack surface](https://tianpan.co/blog/2026-04-20-document-attack-surface-enterprise-ai-prompt-injection).
- Markdown image exfiltration and its fixes: [Archestra](https://archestra.ai/blog/data-exfiltration-via-markdown-image), [Embrace The Red on Claude](https://embracethered.com/blog/posts/2023/anthropic-fixes-claude-data-exfiltration-via-images).
