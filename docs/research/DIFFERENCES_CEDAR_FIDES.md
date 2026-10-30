# How Sentinel differs from AWS Cedar / AgentCore Policy and Microsoft FIDES

30 Oct 2026, for round 2. Every fact about AWS and Microsoft below was read on the page named in the sources table today (30 Oct 2026); anything marked NOT FOUND means "the pages I read do not say it", not "it does not exist". Facts about Sentinel are from this repository.

## The 30-second answer (say this)
> "They are good, and we use their ideas. Cedar and AWS's AgentCore Policy answer *who may call which tool, with which parameters*. FIDES, from Microsoft, tracks labels on data inside an agent that is built with Microsoft's framework. Two things are different about us. First, **Sentinel sits outside the agent**, at the tool boundary, so it works with an agent nobody can modify: Claude.ai, Claude Code, a local model. AWS's policy runs in AWS's gateway, and FIDES runs inside agents written with Microsoft Agent Framework. Second, **the policy input is the task a person approved**, plus what this session has read and where it is going: a restricted value that was read earlier cannot leave in an e-mail, and anything sent after an untrusted document waits for the officer. We are smaller and less formal than they are. We measure instead of prove, and we say what we do not cover."

## What each one is (read today)
**AWS: Cedar and AgentCore Policy.** Cedar is "a language for writing authorization policies and making authorization decisions based on those policies" (default deny, a satisfied forbid always wins). AgentCore Policy, generally available since 3 Mar 2026, stores Cedar policies in a policy engine "attached to an AgentCore Gateway, which intercepts agent-tool traffic and evaluates each request against the policies before allowing or denying tool access". A decision can use the caller's identity (OAuth claims), the tool, and the tool's input parameters ("context.input.amount < 500"). **Most policies are stateless** ("each request is evaluated on its own"), but AWS now also has **temporal policies**: conditions on "an earlier event recorded for the session by its action, principal, and the action's input or output fields" (limits: 20 per engine, 3 temporal operators per policy, a 24-hour window; the caller must send a session id). Policies can be written in natural language and are converted to Cedar for review. Provenance or taint tracking: NOT FOUND. Enforcement "through Amazon Bedrock AgentCore Gateways"; use without a Gateway: NOT FOUND.

**Microsoft: FIDES.** A research paper (Costa et al., arXiv 2505.23643, 2025) and, since 20 May 2026, an **experimental** feature of Microsoft Agent Framework, Python only ("FIDES ships in `agent-framework-core` as an experimental feature", version 1.3.0 and later). Data carries an integrity label (trusted or untrusted) and a confidentiality label (public, private, user identity). Labels propagate automatically through tool calls, "most restrictive" wins, and a tool that must not run in an untrusted or private context "is refused before it runs". Untrusted tool results are hidden from the main model behind a variable, and a separate quarantined model reads them. **Labels are opt-in per data source:** the developer labels each tool's output, and Microsoft's own pages disagree about the default for a tool nobody labelled (the May blog says trusted and public; the October page says untrusted and public). The agent must be an Agent Framework agent; protecting an app you cannot modify: NOT FOUND. The paper's attacker model "assume[s] that the agent's configuration is trusted, including the system message, tool descriptions, and LLMs", it reports that with policy checks FIDES stops all prompt-injection attacks in AgentDojo, and (from a summary of later sections, to be checked against the PDF) it does not stop text-to-text attacks or implicit flows.

**Microsoft Agent Governance Toolkit** (open source, 2 Apr 2026): "a stateless policy engine that intercepts every agent's action before execution", rules in YAML, OPA Rego or Cedar, approval workflows. Provenance and task scope: NOT FOUND. Runs as a framework hook or an AKS sidecar.

## Side by side
| | AWS Cedar / AgentCore Policy | Microsoft FIDES | Sentinel |
|---|---|---|---|
| Where it runs | AWS's AgentCore Gateway | Inside an agent built with Agent Framework (Python) | Outside the agent: an MCP gateway, or a client's own tool-call hook |
| Works on an agent you cannot change | Not found (needs the Gateway) | Not found (needs the framework) | **Yes** for any MCP client; for others through the client's hook |
| What decides | Identity, tool, tool parameters; optionally earlier events of the session | Labels on data, propagated through calls | A per-task slip the officer approved, what the session has read, and the destination |
| Session memory | Stateless by default; temporal policies by opt-in (rules you write per pattern) | Yes: the label of the whole context | Yes: restricted values read, untrusted content read, credentials seen, budget, blocks |
| Provenance | Not found | Labels (manual per source) | Value fingerprints from tool results, and where an address came from, with no per-input annotation; tool labels still come from the officer |
| Hides data from the model | Not found | **Yes** (variable hiding, quarantined model) | **No** (planned: placeholders) |
| Human approval | Not checked (the AWS pages I read were about policies, not approval flows) | Optional, bound to the exact call when possible | Yes: bound to the exact call, one use, silence is a denial |
| Evidence | AWS's analysis tools on policies | Formal guarantees under its attacker model; AgentDojo | Our own corpus, 0 of 43 supported disclosures through (n = 1 per case, cases we wrote), 6 declared gaps; no formal proof |
| Status | GA, 13 regions including Mumbai | Experimental | Hackathon build; demo-grade identity and storage |

## Where they are ahead (say it before they do)
- **AWS is a managed product** with real identity (OAuth, IAM), scale, regions and formal analysis of policies. Cedar is a mature, analysable language. We have a static bearer token and in-memory state.
- **FIDES has formal guarantees** (noninterference for integrity, explicit secrecy for confidentiality) under a stated attacker model, and a **hide primitive**: the model never sees untrusted bytes. Ours only guards the exits; the model provider still sees what the model reads (minimisation is planned, not built).
- **Both have larger, more standard evaluations** (AgentDojo). Ours is a small corpus we wrote ourselves, and the blind red team and an adaptive attacker are not done.

## Where we are different, and what holds up
1. **Reach.** Sentinel works with an agent you cannot modify, through MCP or a client's hook (tested once with Claude.ai sign-in and with Claude Code, plus the hook route in a live session on 30 Oct). That is a deployment difference, and it is real, but note that AWS's gateway is also a gateway: the difference is that ours is open source, self-hosted and not tied to one cloud.
2. **The task is the policy input.** The officer approves a slip (task, tools, destinations, limits, lifetime) before the agent reads anything untrusted; the session token is bound to it. In the AWS and Microsoft pages I read, policies are written ahead of time for a gateway or an agent, not approved per task. That is a claim about those pages, not about their products.
3. **Rules over what the session read.** R2 follows a restricted value from where it was read to where it tries to go; R3 refuses an address that only appeared in untrusted content; R7 and R8 hold an outside action once the session has read untrusted content (and, for R8, restricted data too). An AWS temporal policy can express a sequence you anticipate; FIDES does it with labels. We do it without the developer writing each pattern, but we pay for it with approvals, which is the cost FIDES's own authors name.

**Do not claim:** that nothing like this exists (the pieces do, and AWS now has session-aware policies); that we are stronger than FIDES (we have no formal guarantee and no hiding); that we are "better than Cedar" (we are not a policy language); any number without its n.

## Follow-ups you may get
- **"Why not just use Cedar?"** Cedar is a good engine for the per-call question, and nothing stops Sentinel from using it for that part. The part Cedar does not give you out of the box is the memory of what a session read and the task the officer approved; AWS's temporal policies move toward it, and they need a rule per pattern.
- **"Can't AgentCore temporal policies do your R7?"** You can write a rule like it for a sequence you foresee. The pages I read show no labels that follow a value across tools, and no per-task approval.
- **"Is FIDES not just better?"** It is stronger inside an agent built for it, and it hides data from the model. It does not protect an app you did not write. We take its idea (labels, hiding) as the next step.
- **"Is it novel?"** The ingredients are known: deterministic mediation, labels, taint, Rule of Two. What we can defend is the combination at the tool boundary for agents you cannot modify, with the evidence labelled honestly.
- **"What breaks it?"** A client that does not ask or does not report results, paraphrase of restricted data (R8 holds it for the officer at the cost of approvals), and anything outside the tools Sentinel sees. See the limits page.

## Corrections to our own earlier notes
- `.agents/tasks/01-competitive-landscape.md` row 19 calls AgentCore Policy "deterministic but stateless". That is **out of date**: temporal policies exist (policy-temporal page).
- The same file lists FIDES as tied to the framework with "provenance only, no task scope": still right, and now confirmed as experimental, Python only, labels opt-in.
- Do not use the line "Others decide per call". Use "per request by default, per session if you write the rule".

## Sources (all read 30 Oct 2026)
| Page | Date shown |
|---|---|
| aws.amazon.com/about-aws/whats-new/2026/03/policy-amazon-bedrock-agentcore-generally-available/ | Posted 3 Mar 2026 |
| docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy.html, policy-core-concepts.html, policy-natural-language.html, policy-temporal.html, policy-permissions.html | none shown |
| docs.cedarpolicy.com and /auth/authorization.html | Cedar docs, version 4.6 |
| devblogs.microsoft.com/agent-framework/fides | 20 May 2026 |
| learn.microsoft.com/en-gb/agent-framework/agents/security | ms.date 2026-10-07 |
| github.com/microsoft/fides (README: a notebook that accompanies the paper) | none shown |
| arxiv.org/abs/2505.23643 (introduction and section 2.1 read verbatim; later sections came from a summary) | v1 29 May 2025, v2 3 Sep 2025 |
| opensource.microsoft.com/blog/2026/04/02/introducing-the-agent-governance-toolkit-open-source-runtime-security-for-ai-agents | 2 Apr 2026 |
