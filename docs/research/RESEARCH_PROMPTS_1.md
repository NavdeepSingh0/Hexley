# Research prompts, set 1 (the "do first" topics)

Written 30 Oct 2026 for Navdeep to paste into Manus or any other research tool. Each prompt below is complete on its own: copy everything between the two lines of equals signs. Nothing here is a result; these are the questions.

How to use the answers: bring the reports (and especially the sources tables) back to Claude Code. Every claim will be checked against the linked source and against our code before we build on it. A research tool can invent product features, so a claim with no source link counts as unverified.

Order: Prompt 1 and 2 decide what we can build in the next day. Prompt 3 decides what we can honestly say.


PROMPT 1 of 3: real services behind the gateway
==============================================================================
BACKGROUND YOU NEED (read fully before researching)

Today is 30 October 2026. I am a student building "Sentinel" with a small team for a hackathon (Zinnovatio 4.0, demo to judges on 31 Oct 2026). We want it to become a real product afterwards, so I care about what is true and verifiable, not what sounds good. Treat everything below as the current state of our code. I say clearly what is built and what is only planned.

WHAT SENTINEL IS
Sentinel is a security gateway for AI agents that use tools through the Model Context Protocol (MCP). Its one-line promise: "The AI can only do the job you gave it." It sits between an AI client (Claude.ai, Claude Code, a local model, and so on) and the tool servers that client uses. Every tools/call is checked BEFORE it is forwarded. The check is ordinary deterministic code. No language model takes part in any security decision. That is a deliberate design rule, because models can be talked into things by injected text.

How a decision is made:
- A "permission slip" (task contract) is approved by a human officer before work starts: the task, the allowed tools, the allowed destinations (e-mail domains, URL prefixes, folders), which destinations count as internal, a message limit and a lifetime. The agent's session token is cryptographically bound to the approved slip.
- A tool registry labels every tool: read / write / send, whether it reaches outside, whether it is consequential, whether its output is trusted or untrusted, and whether its output is public, internal or restricted. Unknown tools are refused.
- Rules in plain terms. R1: the tool and destination must be on the slip. R2: values read from restricted tools (numbers, codes, e-mail addresses, phone numbers, IDs, long passages, and anything that looks like a credential) must not appear in an outbound call. R3: a destination that only appeared in untrusted content is refused. R4: sensitive changes wait for the officer's approval of that exact call. R5: message budget. R6: repeated violations freeze the session and revoke its token. R7: after the session has read untrusted content (a document, a web page), consequential outbound actions wait for the officer. R8, the "Rule of Two": if the session has read both restricted data and untrusted content, anything sent outside the internal destinations waits for the officer. R9: a credential found in data is never usable as a credential.
- Also built: a signed (Ed25519), hash-chained audit log written before an action is forwarded; pinning of each tool's definition by hash and scanning of tool descriptions for instructions to the model (against tool poisoning and rug pulls); classification of effects (protected paths such as agent config files and .env, SQL read / write / destructive, shell commands, cc / bcc / reply-to as destinations); a check on the model's reply text for data-carrying links; a web console, a website, and "Sentinel Chat", our own chat host where a live model (cloud, or local through Ollama) works through the gateway.
- Stack: Python 3.13, FastMCP for the gateway, FastAPI for the API, React front ends. Developed on Windows 11. A Cloudflare quick tunnel gives a public https address.

WHAT HAS BEEN TESTED WITH REAL CLIENTS (one session each, not a measurement)
- Claude.ai (free account): Sentinel added as a custom connector, signed in through Sentinel's own OAuth (dynamic client registration plus PKCE; the officer approves the slip with a code). A send containing restricted data was denied.
- Claude Code: added with a static bearer-token header (claude mcp add --transport http). Same result.
- A local model (qwen3 through Ollama) and a cloud model (NVIDIA-hosted Nemotron) inside Sentinel Chat.
- Not tested: ChatGPT, VS Code Copilot, Cursor, Gemini CLI (it connected and listed tools, but its own sign-in had expired), Codex CLI (its default model needed a newer CLI).

THE PROBLEM THIS RESEARCH IS ABOUT: COMPLETE MEDIATION
Sentinel only decides what goes through Sentinel. Today it connects to ONE upstream tool server (our own mock tools). In a real client the same agent usually has other routes that never touch Sentinel: other MCP connectors (for example the Gmail or GitHub connector the user switched on in the same Claude.ai conversation); files attached directly to the conversation (they go straight into the model's context, so Sentinel cannot mark the session as having read untrusted content); the client's built-in tools (shell, file edit, web fetch); and rendered output. If an injected instruction makes the agent use another connector, Sentinel never sees it. We consider this the biggest gap between our project and a real product.

Three approaches we are weighing:
 (A) PROXY. Sentinel connects to the real upstream MCP servers (GitHub, Gmail, ...) itself and holds their credentials. The user's client has ONLY Sentinel as a connector, so Sentinel is the only door. Sentinel would not re-implement Gmail or GitHub; it would proxy the real servers like an API gateway. Not built yet. FastMCP can mount and proxy remote servers, but we have not tried it.
 (B) CLIENT HOOK. The client itself calls Sentinel before every tool call, whichever server the tool belongs to. We know Claude Code has PreToolUse hooks: a matcher regex over names such as mcp__server__tool; handler types include command and http; the hook can return permissionDecision allow / deny / ask; exit code 2 blocks; a timeout does not block unless onFailure is set to block, which is said to need Claude Code 2.1.295 or newer. We plan a POST /api/v1/check endpoint that takes the tool name and arguments of any tool and returns Sentinel's decision. Not built yet.
 (C) COOPERATIVE. A Sentinel tool that the model is told (through the user's personal preferences / custom instructions) to call before using any other connector. This depends on the model choosing to comply, so it is advisory only.

Hard constraints: about 24 hours of working time before the demo; a team of one builder plus an AI coding assistant; no budget; a Windows machine; free or low-cost accounts only. After the demo, 2 to 3 months to a first pilot with an Indian government department or a company. Prefer findings I can act on today.

HOW I WANT YOU TO WORK (applies to everything below)
1. Use primary sources first: official documentation, the MCP specification and its changelog, vendor changelogs and release notes, GitHub repositories and their issues, security advisories. Blog posts and forums are allowed as secondary evidence and must be labelled as such. Marketing pages do not count as evidence of what a product can technically do.
2. For EVERY claim give: the source URL, the page's date or the product version it describes, and a short direct quote (under 25 words) that supports it. If you cannot find a source, write NOT FOUND or UNVERIFIED. Do not guess, and do not fill gaps with what is plausible.
3. Mark every statement as DOCUMENTED (the docs say so), REPORTED (someone says they observed it, with a link) or INFERRED (your own reasoning; say so).
4. Today is 30 Oct 2026. Flag anything older than 6 months, and anything about a product version that may have changed, with its date. If sources disagree, show both.
5. Actively look for counter-evidence: bugs, issues, bypasses, complaints. Examples: hooks that do not fire for some tool types, configuration the agent can overwrite, features that exist only on paid or enterprise plans, features that are beta or waitlist only.
6. Always state the plan or tier (Free, Pro, Team, Enterprise) and any region limits (I am in India).
7. Finish with the deliverables listed below. Use tables for comparisons. Do not pad. I would rather read "unknown" than a confident wrong answer.

TASK 1: CAN SENTINEL BE THE GATEWAY IN FRONT OF REAL SERVICES? (approach A)

Goal: decide whether approach (A) is feasible in about one working day for ONE real connector, and which connector to pick.

PART 1. Inventory of real MCP servers.
Cover: GitHub; Google (Gmail, Calendar, Drive, Docs and Sheets); Slack; Microsoft 365 (Outlook mail, Teams, SharePoint / OneDrive); Atlassian (Jira, Confluence); Notion; Linear; a Postgres database (including Supabase's server); a filesystem server. Add Stripe only if it is quick.
For each one find:
 a. Is there an OFFICIAL MCP server from the service owner? If only community servers exist, name the most used and its state (last commit, stars, open security issues).
 b. Transport: remote (Streamable HTTP or SSE; give the URL) or local-only (stdio)? Which MCP spec revision does it implement?
 c. Authentication, exactly. OAuth 2.1 with dynamic client registration; OAuth with a pre-registered client; personal access token; API key; service account; other. What can a SERVER-SIDE gateway (no person at a browser) use? Can it hold a long-lived credential or a refresh token and call the server without a person present? Do any of these servers accept only specific, approved MCP clients (allow-lists of client IDs or redirect URIs) that would block a self-hosted gateway?
 d. Scope granularity: can the credential be narrowed (a GitHub fine-grained token limited to one repository and specific permissions; Gmail read-only vs send vs full; Slack scopes)? Which scopes are "restricted" or "sensitive" and trigger vendor verification (for example Google's OAuth app verification, refresh-token expiry while an app is in testing mode, the cap on test users)?
 e. The tool list: exact tool names, whether each carries MCP annotations (readOnlyHint, destructiveHint, openWorldHint), and which tools send, post or delete (outbound or consequential).
 f. Cost, rate limits, free-tier availability, and what a student needs to create a test account.
 g. Realistic setup time for one person starting from nothing, with the exact steps.
Then RANK the top 3 for a one-day integration, with reasons.

PART 2. Gateway mechanics.
 a. How do existing gateways and proxies expose several upstream MCP servers behind one endpoint? Cover namespacing / prefixing, tool-name collisions, capability negotiation, session handling, notifications and progress, and how they pass through or block sampling, elicitation, resources and prompts. Cite the FastMCP documentation for mounting and proxying remote servers (current version, the proxy API, how to attach an upstream's auth headers, how to intercept tools/call). Cite at least three open-source MCP gateway projects with their approach and maintenance status.
 b. Known security issues of this pattern: confused deputy (one gateway credential serving several users), token passthrough (what does the MCP authorization specification say about it?), tool-name shadowing, SSRF through upstream URLs, secrets at rest, stdio servers running as subprocesses with the gateway's privileges. What do the MCP spec's security best practices say?
 c. MCP specification: what is the latest revision as of today? What changed in authorization (resource indicators, protected resource metadata, client ID metadata documents)? Is there anything on enterprise-managed authorization, token exchange or "cross-app access" that lets an organisation's identity provider authorise an agent-to-service connection without each user clicking through? Explain in plain words what that would give a gateway like ours.

PART 3. How do other products broker credentials for agents? Cover Composio, Arcade, Keycard, Aembit, Cloudflare's MCP server portal / gateway, Docker's MCP Gateway, Microsoft's MCP gateway, and anything newer you find. One short paragraph each: what they hold, how they scope, whether they enforce policy on each call, and what they cost. The point is to tell me what is commodity and what is not.

DELIVERABLES
1. One paragraph: which single real connector to wire up first and why, with the exact auth setup steps.
2. The Part 1 table, one row per service.
3. A list of risks that could waste our day.
4. A sources table: URL, date, type (official doc / spec / repo / issue / blog / forum), and what it was used for.
==============================================================================


PROMPT 2 of 3: client hooks
==============================================================================
BACKGROUND YOU NEED (read fully before researching)

Today is 30 October 2026. I am a student building "Sentinel" with a small team for a hackathon (Zinnovatio 4.0, demo to judges on 31 Oct 2026). We want it to become a real product afterwards, so I care about what is true and verifiable, not what sounds good. Treat everything below as the current state of our code. I say clearly what is built and what is only planned.

WHAT SENTINEL IS
Sentinel is a security gateway for AI agents that use tools through the Model Context Protocol (MCP). Its one-line promise: "The AI can only do the job you gave it." It sits between an AI client (Claude.ai, Claude Code, a local model, and so on) and the tool servers that client uses. Every tools/call is checked BEFORE it is forwarded. The check is ordinary deterministic code. No language model takes part in any security decision. That is a deliberate design rule, because models can be talked into things by injected text.

How a decision is made:
- A "permission slip" (task contract) is approved by a human officer before work starts: the task, the allowed tools, the allowed destinations (e-mail domains, URL prefixes, folders), which destinations count as internal, a message limit and a lifetime. The agent's session token is cryptographically bound to the approved slip.
- A tool registry labels every tool: read / write / send, whether it reaches outside, whether it is consequential, whether its output is trusted or untrusted, and whether its output is public, internal or restricted. Unknown tools are refused.
- Rules in plain terms. R1: the tool and destination must be on the slip. R2: values read from restricted tools (numbers, codes, e-mail addresses, phone numbers, IDs, long passages, and anything that looks like a credential) must not appear in an outbound call. R3: a destination that only appeared in untrusted content is refused. R4: sensitive changes wait for the officer's approval of that exact call. R5: message budget. R6: repeated violations freeze the session and revoke its token. R7: after the session has read untrusted content (a document, a web page), consequential outbound actions wait for the officer. R8, the "Rule of Two": if the session has read both restricted data and untrusted content, anything sent outside the internal destinations waits for the officer. R9: a credential found in data is never usable as a credential.
- Also built: a signed (Ed25519), hash-chained audit log written before an action is forwarded; pinning of each tool's definition by hash and scanning of tool descriptions for instructions to the model (against tool poisoning and rug pulls); classification of effects (protected paths such as agent config files and .env, SQL read / write / destructive, shell commands, cc / bcc / reply-to as destinations); a check on the model's reply text for data-carrying links; a web console, a website, and "Sentinel Chat", our own chat host where a live model (cloud, or local through Ollama) works through the gateway.
- Stack: Python 3.13, FastMCP for the gateway, FastAPI for the API, React front ends. Developed on Windows 11. A Cloudflare quick tunnel gives a public https address.

WHAT HAS BEEN TESTED WITH REAL CLIENTS (one session each, not a measurement)
- Claude.ai (free account): Sentinel added as a custom connector, signed in through Sentinel's own OAuth (dynamic client registration plus PKCE; the officer approves the slip with a code). A send containing restricted data was denied.
- Claude Code: added with a static bearer-token header (claude mcp add --transport http). Same result.
- A local model (qwen3 through Ollama) and a cloud model (NVIDIA-hosted Nemotron) inside Sentinel Chat.
- Not tested: ChatGPT, VS Code Copilot, Cursor, Gemini CLI (it connected and listed tools, but its own sign-in had expired), Codex CLI (its default model needed a newer CLI).

THE PROBLEM THIS RESEARCH IS ABOUT: COMPLETE MEDIATION
Sentinel only decides what goes through Sentinel. Today it connects to ONE upstream tool server (our own mock tools). In a real client the same agent usually has other routes that never touch Sentinel: other MCP connectors (for example the Gmail or GitHub connector the user switched on in the same Claude.ai conversation); files attached directly to the conversation (they go straight into the model's context, so Sentinel cannot mark the session as having read untrusted content); the client's built-in tools (shell, file edit, web fetch); and rendered output. If an injected instruction makes the agent use another connector, Sentinel never sees it. We consider this the biggest gap between our project and a real product.

Three approaches we are weighing:
 (A) PROXY. Sentinel connects to the real upstream MCP servers (GitHub, Gmail, ...) itself and holds their credentials. The user's client has ONLY Sentinel as a connector, so Sentinel is the only door. Sentinel would not re-implement Gmail or GitHub; it would proxy the real servers like an API gateway. Not built yet. FastMCP can mount and proxy remote servers, but we have not tried it.
 (B) CLIENT HOOK. The client itself calls Sentinel before every tool call, whichever server the tool belongs to. We know Claude Code has PreToolUse hooks: a matcher regex over names such as mcp__server__tool; handler types include command and http; the hook can return permissionDecision allow / deny / ask; exit code 2 blocks; a timeout does not block unless onFailure is set to block, which is said to need Claude Code 2.1.295 or newer. We plan a POST /api/v1/check endpoint that takes the tool name and arguments of any tool and returns Sentinel's decision. Not built yet.
 (C) COOPERATIVE. A Sentinel tool that the model is told (through the user's personal preferences / custom instructions) to call before using any other connector. This depends on the model choosing to comply, so it is advisory only.

Hard constraints: about 24 hours of working time before the demo; a team of one builder plus an AI coding assistant; no budget; a Windows machine; free or low-cost accounts only. After the demo, 2 to 3 months to a first pilot with an Indian government department or a company. Prefer findings I can act on today.

HOW I WANT YOU TO WORK (applies to everything below)
1. Use primary sources first: official documentation, the MCP specification and its changelog, vendor changelogs and release notes, GitHub repositories and their issues, security advisories. Blog posts and forums are allowed as secondary evidence and must be labelled as such. Marketing pages do not count as evidence of what a product can technically do.
2. For EVERY claim give: the source URL, the page's date or the product version it describes, and a short direct quote (under 25 words) that supports it. If you cannot find a source, write NOT FOUND or UNVERIFIED. Do not guess, and do not fill gaps with what is plausible.
3. Mark every statement as DOCUMENTED (the docs say so), REPORTED (someone says they observed it, with a link) or INFERRED (your own reasoning; say so).
4. Today is 30 Oct 2026. Flag anything older than 6 months, and anything about a product version that may have changed, with its date. If sources disagree, show both.
5. Actively look for counter-evidence: bugs, issues, bypasses, complaints. Examples: hooks that do not fire for some tool types, configuration the agent can overwrite, features that exist only on paid or enterprise plans, features that are beta or waitlist only.
6. Always state the plan or tier (Free, Pro, Team, Enterprise) and any region limits (I am in India).
7. Finish with the deliverables listed below. Use tables for comparisons. Do not pad. I would rather read "unknown" than a confident wrong answer.

TASK 2: WHICH AI CLIENTS LET A SECURITY TOOL CHECK EVERY TOOL CALL BEFORE IT RUNS? (approach B)

Goal: decide how far approach (B) extends beyond Claude Code, and how hard it is for the agent or an attacker to bypass.

PART 1. Claude Code (most important; we plan to build on it).
Verify against the CURRENT official documentation:
 a. PreToolUse hooks: event names; matcher syntax for MCP tools (mcp__server__tool) and for built-in tools (Bash, Edit, Write, WebFetch and others); whether the hook fires for subagents' tools, for MCP connectors that come from a claude.ai account and are synced into Claude Code, and in non-interactive modes (-p flag, the Agent SDK).
 b. The http handler: the full request JSON schema (every field), the full response JSON schema (permissionDecision allow / deny / ask / defer, reason fields, and updatedInput if it exists), header and auth support, timeouts, retries, the onFailure setting and its minimum version, and what happens when the endpoint is unreachable. Also: can a deny be overridden by other permission rules or modes (allow rules, bypass-permissions mode, the dangerously-skip-permissions flag)?
 c. Hardening: can an organisation push MANAGED settings that neither users nor the agent can override (managed policy file, MDM, an option that allows only managed hooks)? Can the agent edit .claude/settings.json and remove the hook? Search the GitHub issues for known bugs or bypasses where hooks did not run or could be evaded.
 d. Is there official guidance on using hooks as a security boundary rather than a convenience?
Quote a minimal working http hook configuration from the docs.

PART 2. Other clients. Cover: Claude Desktop; Cursor; VS Code with GitHub Copilot agent mode; Windsurf; Gemini CLI; OpenAI Codex CLI; Google Antigravity; Amazon Kiro; GitHub Copilot CLI and coding agent; Cline and Roo Code; Zed; JetBrains (AI Assistant, Junie); Goose; Amp.
Table columns: does a pre-tool-call interception mechanism exist (hook, plugin or extension API, policy file)? | covers MCP tools / built-in tools / both | mechanism and config file location | payload fields | can it call an HTTP endpoint | can it block | on error or timeout: fail-open or fail-closed | can the agent or injected text modify the config | enterprise / managed lock | available since version | doc URL and date.
Separately from hooks: admin policies that restrict WHICH MCP servers can be used (VS Code MCP policies, Cursor team or admin controls, and similar).

PART 3. Agent frameworks, for teams who build their own agents: OpenAI Agents SDK (guardrails, tool hooks), LangGraph / LangChain (interrupts, middleware), Claude Agent SDK (hooks, canUseTool), Google ADK (callbacks), Microsoft Agent Framework, Vercel AI SDK, CrewAI, Pydantic AI. Which have a pre-tool-call callback that can deny with a reason, and how would an external policy service plug into each?

PART 4. Standards. Is there an emerging standard for pre-tool-call authorization (an MCP proposal, OPA or Cedar integrations, OpenID AuthZEN) that clients are adopting? Who is adopting it?

DELIVERABLES
1. A ranked list of clients by how enforceable a hook is today: ENFORCED, BYPASSABLE, or ABSENT, with one line of evidence each.
2. The exact request / response contract for Claude Code http hooks as documented, plus the minimal working config quoted from the docs.
3. A list of every bypass or bug you found, with links.
4. A sources table: URL, date, type, and what it was used for.
==============================================================================


PROMPT 3 of 3: closed chat apps
==============================================================================
BACKGROUND YOU NEED (read fully before researching)

Today is 30 October 2026. I am a student building "Sentinel" with a small team for a hackathon (Zinnovatio 4.0, demo to judges on 31 Oct 2026). We want it to become a real product afterwards, so I care about what is true and verifiable, not what sounds good. Treat everything below as the current state of our code. I say clearly what is built and what is only planned.

WHAT SENTINEL IS
Sentinel is a security gateway for AI agents that use tools through the Model Context Protocol (MCP). Its one-line promise: "The AI can only do the job you gave it." It sits between an AI client (Claude.ai, Claude Code, a local model, and so on) and the tool servers that client uses. Every tools/call is checked BEFORE it is forwarded. The check is ordinary deterministic code. No language model takes part in any security decision. That is a deliberate design rule, because models can be talked into things by injected text.

How a decision is made:
- A "permission slip" (task contract) is approved by a human officer before work starts: the task, the allowed tools, the allowed destinations (e-mail domains, URL prefixes, folders), which destinations count as internal, a message limit and a lifetime. The agent's session token is cryptographically bound to the approved slip.
- A tool registry labels every tool: read / write / send, whether it reaches outside, whether it is consequential, whether its output is trusted or untrusted, and whether its output is public, internal or restricted. Unknown tools are refused.
- Rules in plain terms. R1: the tool and destination must be on the slip. R2: values read from restricted tools (numbers, codes, e-mail addresses, phone numbers, IDs, long passages, and anything that looks like a credential) must not appear in an outbound call. R3: a destination that only appeared in untrusted content is refused. R4: sensitive changes wait for the officer's approval of that exact call. R5: message budget. R6: repeated violations freeze the session and revoke its token. R7: after the session has read untrusted content (a document, a web page), consequential outbound actions wait for the officer. R8, the "Rule of Two": if the session has read both restricted data and untrusted content, anything sent outside the internal destinations waits for the officer. R9: a credential found in data is never usable as a credential.
- Also built: a signed (Ed25519), hash-chained audit log written before an action is forwarded; pinning of each tool's definition by hash and scanning of tool descriptions for instructions to the model (against tool poisoning and rug pulls); classification of effects (protected paths such as agent config files and .env, SQL read / write / destructive, shell commands, cc / bcc / reply-to as destinations); a check on the model's reply text for data-carrying links; a web console, a website, and "Sentinel Chat", our own chat host where a live model (cloud, or local through Ollama) works through the gateway.
- Stack: Python 3.13, FastMCP for the gateway, FastAPI for the API, React front ends. Developed on Windows 11. A Cloudflare quick tunnel gives a public https address.

WHAT HAS BEEN TESTED WITH REAL CLIENTS (one session each, not a measurement)
- Claude.ai (free account): Sentinel added as a custom connector, signed in through Sentinel's own OAuth (dynamic client registration plus PKCE; the officer approves the slip with a code). A send containing restricted data was denied.
- Claude Code: added with a static bearer-token header (claude mcp add --transport http). Same result.
- A local model (qwen3 through Ollama) and a cloud model (NVIDIA-hosted Nemotron) inside Sentinel Chat.
- Not tested: ChatGPT, VS Code Copilot, Cursor, Gemini CLI (it connected and listed tools, but its own sign-in had expired), Codex CLI (its default model needed a newer CLI).

THE PROBLEM THIS RESEARCH IS ABOUT: COMPLETE MEDIATION
Sentinel only decides what goes through Sentinel. Today it connects to ONE upstream tool server (our own mock tools). In a real client the same agent usually has other routes that never touch Sentinel: other MCP connectors (for example the Gmail or GitHub connector the user switched on in the same Claude.ai conversation); files attached directly to the conversation (they go straight into the model's context, so Sentinel cannot mark the session as having read untrusted content); the client's built-in tools (shell, file edit, web fetch); and rendered output. If an injected instruction makes the agent use another connector, Sentinel never sees it. We consider this the biggest gap between our project and a real product.

Three approaches we are weighing:
 (A) PROXY. Sentinel connects to the real upstream MCP servers (GitHub, Gmail, ...) itself and holds their credentials. The user's client has ONLY Sentinel as a connector, so Sentinel is the only door. Sentinel would not re-implement Gmail or GitHub; it would proxy the real servers like an API gateway. Not built yet. FastMCP can mount and proxy remote servers, but we have not tried it.
 (B) CLIENT HOOK. The client itself calls Sentinel before every tool call, whichever server the tool belongs to. We know Claude Code has PreToolUse hooks: a matcher regex over names such as mcp__server__tool; handler types include command and http; the hook can return permissionDecision allow / deny / ask; exit code 2 blocks; a timeout does not block unless onFailure is set to block, which is said to need Claude Code 2.1.295 or newer. We plan a POST /api/v1/check endpoint that takes the tool name and arguments of any tool and returns Sentinel's decision. Not built yet.
 (C) COOPERATIVE. A Sentinel tool that the model is told (through the user's personal preferences / custom instructions) to call before using any other connector. This depends on the model choosing to comply, so it is advisory only.

Hard constraints: about 24 hours of working time before the demo; a team of one builder plus an AI coding assistant; no budget; a Windows machine; free or low-cost accounts only. After the demo, 2 to 3 months to a first pilot with an Indian government department or a company. Prefer findings I can act on today.

HOW I WANT YOU TO WORK (applies to everything below)
1. Use primary sources first: official documentation, the MCP specification and its changelog, vendor changelogs and release notes, GitHub repositories and their issues, security advisories. Blog posts and forums are allowed as secondary evidence and must be labelled as such. Marketing pages do not count as evidence of what a product can technically do.
2. For EVERY claim give: the source URL, the page's date or the product version it describes, and a short direct quote (under 25 words) that supports it. If you cannot find a source, write NOT FOUND or UNVERIFIED. Do not guess, and do not fill gaps with what is plausible.
3. Mark every statement as DOCUMENTED (the docs say so), REPORTED (someone says they observed it, with a link) or INFERRED (your own reasoning; say so).
4. Today is 30 Oct 2026. Flag anything older than 6 months, and anything about a product version that may have changed, with its date. If sources disagree, show both.
5. Actively look for counter-evidence: bugs, issues, bypasses, complaints. Examples: hooks that do not fire for some tool types, configuration the agent can overwrite, features that exist only on paid or enterprise plans, features that are beta or waitlist only.
6. Always state the plan or tier (Free, Pro, Team, Enterprise) and any region limits (I am in India).
7. Finish with the deliverables listed below. Use tables for comparisons. Do not pad. I would rather read "unknown" than a confident wrong answer.

TASK 3: CAN ANYTHING ENFORCE A TOOL-CALL POLICY INSIDE CLAUDE.AI OR CHATGPT?

Goal: decide how honest our pitch can be for people who use chat apps, and whether an enforced path exists at all. This is the hardest of our three questions, so be especially strict about evidence.

PART A. Claude.ai, Claude Desktop and Claude mobile. State the plan for every finding (Free, Pro, Max, Team, Enterprise).
 1. Connector governance: can admins on Team or Enterprise allow or deny specific connectors (including custom connectors) for the whole organisation? Can they disable every connector except one? Can members add custom connectors by themselves? Are per-tool permissions (always allow / needs approval / never) documented, and are they enforced by Anthropic's servers or only by the client UI?
 2. Other admin switches: can file uploads, web search, the code-execution / analysis tool and memory be disabled at organisation level? That would close the "attached file" bypass.
 3. Organisation-level instructions: can admins set instructions that members cannot remove? Do personal preferences apply in Projects, on mobile and on desktop? Is there published data on how reliably Claude follows standing instructions when injected content conflicts with them? Cite Anthropic's own prompt-injection robustness figures (system cards, blog posts) for tool use and browser use: exact numbers, what was measured, which model.
 4. Logging: audit logs, the Compliance API and exports. Do they contain tool calls, arguments and connector names?
 5. Is there any "bring your own policy engine" hook in Claude.ai (a webhook before a tool runs)? What about the Claude API's MCP connector or Managed Agents: can tool approval be routed to a customer's own service?
 6. Where do remote MCP connector requests come from? If they come from Anthropic's servers with documented IP ranges, could an organisation in principle allow-list only Sentinel's address for connectors?

PART B. ChatGPT (Plus, Pro, Business, Enterprise, Edu). Same questions: apps and connectors, developer mode, admin role-based controls over which apps and actions are allowed, per-action confirmation behaviour, file-upload and browsing switches, the Compliance API's contents, organisation-level custom instructions, MCP connectors, and the Agents SDK / Agent Builder guardrails.

PART C. Other assistants where an external policy service can approve or deny each tool call BEFORE it runs. Check Microsoft Copilot Studio (is there a real-time external threat-detection or runtime-protection webhook that can block a tool call? details, plan, availability), Microsoft 365 Copilot, Google Gemini Enterprise / Agentspace, Salesforce Agentforce, Perplexity, and anything else you find. For each: the request / response format, latency limit, whether it fails open or closed, and cost or plan needed.

PART D. Observation without control. Could a browser extension, a managed-browser policy, an enterprise proxy / CASB, or MDM at least DETECT which connectors or tools were used in a chat session, to power a "coverage warning"? What is technically possible, and what are the legal, privacy, store-policy and terms-of-service problems of an extension that touches claude.ai or chatgpt.com? Is there precedent (enterprise-browser vendors doing AI-app data-loss prevention)?

PART E. Independent evidence. What do papers, red-team reports, CVEs and incident write-ups say about whether chat-app connector permission prompts ("needs approval") protect against prompt injection? List real incidents involving connectors such as Gmail or Drive that exposed data. Include any "the attacker moves second" evidence against defences that looked good on fixed attacks.

DELIVERABLES
1. An honest matrix, app x plan x lever (admin connector control; file-upload disable; organisation instructions; external policy hook; logging), where each cell is one of: ENFORCED BY VENDOR / ADVISORY ONLY / NOT AVAILABLE / UNKNOWN, with a source.
2. A recommendation: for a person or organisation on Claude.ai or ChatGPT, what is the strongest realistic configuration with Sentinel (for example "admin allows only the Sentinel connector and disables uploads")? What does it still not cover? Which exact sentence about coverage can we truthfully put on our website?
3. Open questions you could not resolve, and the simple test that would resolve each.
4. A sources table: URL, date, type, and what it was used for.
==============================================================================
