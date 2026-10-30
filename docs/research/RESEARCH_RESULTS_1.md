# Research results, set 1

The answers to the three prompts in `RESEARCH_PROMPTS_1.md`. Paste each report into its own section below.

## How to fill this in
1. Paste the report **exactly as the research tool gave it**, under "Raw report". Do not shorten or tidy it; the wording matters when we check it.
2. Paste its sources table under "Sources". If the tool gave no sources, write `NO SOURCES GIVEN` there. A claim with no source is treated as unverified.
3. Fill in the three header lines (tool, date, status). Status is `complete`, `partial` (for example the tool stopped early), or `not run yet`.
4. Put your own reactions and follow-up questions under "Your notes".
5. Leave "Checked by Claude" empty. Claude fills it in later, claim by claim, against the linked sources and against our code.

A research tool can invent product features. Nothing here is a fact about the world until it has a "Checked by Claude" entry that says `CONFIRMED` with a source.

---

## Prompt 1: real services behind the gateway

- Tool used: Manus (per Navdeep)
- Date run: 30 Oct 2026
- Status: partial
- What is missing, if partial: Part 1 only, as per-service summaries (GitHub, Google, Slack, Microsoft 365, Atlassian, Notion, Linear, Postgres/Supabase, filesystem). No URLs, quotes or sources table came with it. Part 2 (gateway mechanics, MCP security best practices, enterprise-managed authorization) is missing, and so are the Part 3 vendors Cloudflare, Docker and Microsoft's gateway (Composio, Arcade and Keycard came back). All four deliverables are missing: the recommendation, the table, the risks and the sources.

### Raw report
<!-- paste below this line -->

Research exactly this subject for Sentinel using web search and opening primary-source pages. Date context 2026-10-30; user is in India. Subject: GitHub MCP. Scope: Official status/repo; transport URL/spec; auth and unattended server gateway/client restrictions; fine-grained token scopes; exact tools/annotations and write/delete actions; cost/rate limits; exact student setup and one-day feasibility.. Prioritize official vendor docs, MCP specs/changelogs, GitHub repos/releases/issues/security advisories; label secondary sources. Every material claim needs URL, date/version, type, direct quote under 25 words and status DOCUMENTED/REPORTED/INFERRED. Explicitly say NOT FOUND or UNVERIFIED rather than guess. Flag sources older than six months or version-sensitive claims. Include plan/tier and India region limits or unknown, counter-evidence, exact annotation names only when documented, and practical single-connector setup where relevant. Do not rely on snippets alone. Return concise substantive findings and source records in required JSON.
Subtask completed
Result
GitHub MCP (GitHub Copilot MCP Server) – concise summary of validated findings (as of 2026-10-30)
Key status and availability
The GitHub MCP Server exists as an official, hosted remote service. The latest observed release is v1.12.2, published 2026-09-16.
The remote endpoint is hosted at https://api.githubcopilot.com/mcp/. The MCP transport uses Streamable HTTP via HTTP POST messages to a single endpoint.
Documentation indicates remote hosting and client configuration for MCP, with version-sensitive main/docs. The README is mutable.
Authentication and gateways
Supported authentication methods include interactive OAuth and PAT bearer-header options for the remote endpoint.
OAuth: requires host/client app setup and adherence to organization policies; some enterprise accounts may have PATs disabled by policy.
The MCP authorization spec requires an OAuth client registration path; refresh tokens are not guaranteed.
The device-code flow documented for local stdio is not applicable to the hosted remote endpoint; for unattended local stdio, guidance points to GitHub App authentication.
Practical gateway inference: a gateway would need remote MCP HTTP/Streamable HTTP support, bearer auth handling, MCP headers, and compliance with OAuth/enterprise policies. No official gateway compatibility matrix or hosted service-to-service identity method is published.
Tool catalog and writes
Default remote tools available on the server include context, issues, pull_requests, repos, and users. Examples: get_me, issue_read, issue_write, list_issues, create_pull_request, merge_pull_request, create_branch, create_or_update_file, delete_file, delete_repository, push_files, search_users, etc.
Additional toolsets cover actions, discussions, gists, governance, projects, labels, notifications, security, and more.
A read-only mode exists; enabling read-only disables write tools.
Explicit write tools include a wide set (e.g., actions_run_trigger, discussion_comment_write, create_repository, delete_file, delete_repository, push_files, pull_request_review_write, update_pull_request, etc.). These capabilities refer to API capabilities and do not guarantee per-account or per-client permissions.
Fine-grained tokens and permissions
GitHub’s fine-grained PAT model differs from classic OAuth scopes. Permissions are resource-owner and repo-scoped with minimum necessary access.
The server’s config indicates classic PAT scope filtering is special; some token types (including fine-grained PATs) may still surface tools, but actual access is enforced by the gateway/API.
There is no published one-to-one mapping from every MCP tool to specific fine-grained PAT permissions. Use the X-Accepted-GitHub-Permissions header and the underlying endpoint docs for exact mappings.
Costs, rate limits, and regional considerations
MCP is described as available to GitHub users regardless of plan; licensing depends on the specific Copilot/MCP tool.
Practical limits come from GitHub REST API rate limits (5,000 requests/hour for authenticated users; higher for certain Enterprise apps). This REST-rate limit is not the MCP-specific quota.
No published MCP-specific hosted quota or India-region data residency, currency, or region-based exceptions were found.
Student setup and one-day feasibility
For a verified student with GitHub, VS Code, and Copilot Student entitlement, a one-day trial is reasonable in theory: install an MCP-capable client, configure the remote endpoint, complete OAuth, verify the server appears in MCP: List Servers, and start with a read tool before enabling write tools.
This is an inferred feasibility estimate, not a guaranteed SLA. Education status verification, organizational policy, and gateway procurement can affect timing.
Noted gaps and caveats
No official per-region hosting/data residency statement for api.githubcopilot.com/mcp/ found; India-specific residency/limits remain UNVERIFIED.
No published standalone MCP service fee, hosted-MCP rate quota, or explicit MCP SLA found.
The accuracy and applicability of the v1.12.2 changes to current hosted service require verification beyond the cited sources.
Education eligibility and same-day approval are not guaranteed; eligibility steps exist but timing is not guaranteed.
Security advisories exist for the MCP server, including potential DoS vectors in local components; applicability to the hosted remote endpoint remains to be independently verified.
Bottom-line
The GitHub MCP remains an officially hosted remote service with a defined tool catalog and authentication model, but many specifics (region data residency, MCP-specific quotas/SLA, one-to-one permission mappings, and gateway compatibility) are not fully published and require careful per-endpoint verification. A one-day student trial is plausible, given appropriate account status and policy allowances, but not guaranteed.

Research Google MCP: Gmail, Calendar, Drive, Docs, Sheets
Research exactly this subject for Sentinel using web search and opening primary-source pages. Date context 2026-10-30; user is in India. Subject: Google MCP: Gmail, Calendar, Drive, Docs, Sheets. Scope: Per service owner official server or community; transport/URL/spec; OAuth setup, unattended gateway viability/client restrictions; Google scopes, verification/testing-mode/refresh-token limitations; exact tools and annotations and outbound effects; cost/quotas; India/account setup. Mark each service separately.. Prioritize official vendor docs, MCP specs/changelogs, GitHub repos/releases/issues/security advisories; label secondary sources. Every material claim needs URL, date/version, type, direct quote under 25 words and status DOCUMENTED/REPORTED/INFERRED. Explicitly say NOT FOUND or UNVERIFIED rather than guess. Flag sources older than six months or version-sensitive claims. Include plan/tier and India region limits or unknown, counter-evidence, exact annotation names only when documented, and practical single-connector setup where relevant. Do not rely on snippets alone. Return concise substantive findings and source records in required JSON.
Subtask completed
Result
Summary of the untrusted structured result on Google MCP for Gmail, Calendar, Drive, Docs, Sheets
Status overview
Google’s first-party MCP services exist for all five products, with dedicated global endpoints. Platform-wide GA status is separate from per-service GA; many services are still documented as Preview-gated in Workspace docs as of the cutoff. India-specific endpoints or eligibility rules are not confirmed.
Endpoints and transport
Global MCP endpoints (per service): Gmail: gmailmcp.googleapis.com/mcp/v1; Calendar: calendarmcp.googleapis.com/mcp/v1; Drive: drivemcp.googleapis.com/mcp/v1; Docs: docsmcp.googleapis.com/mcp/v1; Sheets: sheetsmcp.googleapis.com/mcp/v1.
Transport: Streamable HTTP; OAuth 2.0. Clients must use the per-service URL and scope; client callback URIs must match the selected client’s registered URI.
OAuth and testing
Durable user-delegated sessions require refresh tokens; offline access must be requested via access_type=offline. Testing environments show a 7-day refresh-token expiry for unverified scopes, with a 100-new-user cap for unapproved sensitive/restricted scopes. Service accounts/domain-wide delegation for these MCP endpoints is not found in the docs.
Tool surface and behavior by product
Gmail
Tools documented: create_draft, get_thread, label_message, label_thread, list_drafts, list_labels, search_threads, unlabel_message, unlabel_thread.
No explicit send_email tool; create_draft creates a draft. Scopes: gmail.readonly, gmail.compose (restricted, with verification and security considerations).
Calendar
Tools documented: create_event, delete_event, get_event, list_calendars, list_events, respond_to_event, suggest_time, update_event.
Scopes include read-only ones; write capability exists but verify authorization requirements before enabling writes.
Drive
Tools documented: copy_file, create_file, download_file_content, get_file_metadata, get_file_permissions, list_recent_files, read_file_content, search_files.
create_file can upload Docs/Sheets; drive.readonly is restricted, drive.file is per-file access.
Docs
Tools documented: read_doc, update_doc.
update_doc applies batch changes and can edit content; hints indicate write capabilities. Scopes include drive.readonly, drive.file, documents.readonly, documents.
Sheets
Tools documented: get_values, get_spreadsheet, update_spreadsheet, update_values, update_formulas, insert_dimension.
update_spreadsheet can perform structural edits; get_values is read-oriented. Scopes include spreadsheets.readonly, spreadsheets, drive.readonly, drive.file.
Quotas and pricing
Baseline: standard API use is described as no additional cost, with planned overage billing later in 2026 (not confirmed as implemented). Per-service quota hints:
Gmail: 1.2M quota units/project/minute; 6,000/user/project/minute; 80M units/project/day.
Calendar: 10,000 requests/project/minute; 600/user/project/minute; 1,000,000 requests/project/day.
Drive: 1,000,000 quota units/project/minute; 325,000/user/project/minute; 400,000,000 units/project/day; 1 TB/day egress.
Docs/Sheets: quota figures exist in sources but exact per-user write quotas are not fully extracted here; per-tool read/write metrics exist.
Advice: consult current Cloud Console quota pages for precise, up-to-date values; avoid extrapolating from aggregate counts.
India-specific notes
No India-only MCP endpoint or eligibility rule found; official guidance indicates global endpoints, with India-specific residency or eligibility unverified.
Community and non-official implementations
Community projects (e.g., taylorwilsdon/google_workspace_mcp) claim coverage for all five products and offer local/remote modes, but are not Google-supported. These should be treated as not officially endorsed and may carry additional security and reliability considerations.
Google Workspace CLI repository states it is not an officially supported Google product, which corroborates that not all tooling is official MCP server support.
Annotations and tool surface
Annotations (destructiveHint, idempotentHint, readOnlyHint, openWorldHint) exist per-tool in MCP references, but exact per-tool values can vary; rely on the live tools/list responses for current values.
The official tool inventories in setup guides may lag behind live surface; cross-check via tools/list at runtime.
Key caveats and gaps
Documentation gaps: tool inventories and per-tool annotation values may not be fully captured across all five products; some quota values are not extracted in full for Docs/Sheets.
Data residency and India-specific eligibility remain unverified; no explicit service-account or domain-wide delegation support found for these MCP endpoints.
Production vs. testing mode details: 7-day refresh-token expiry for unverified scopes and 100-new-user cap impose limitations on unattended testing; production/internal app enrollment is the recommended path.
Bottom line
The structured result confirms official, first-party MCP surfaces exist for Gmail, Calendar, Drive, Docs, and Sheets, with global endpoints and OAuth-based access. Preview gating and regional eligibility nuances exist, and documentation shows per-service tool lists and scopes. Quotas exist with planned overage considerations; exact, current per-tool quotas should be verified in the respective Cloud Console pages. Community MCP implementations exist but are not Google-supported.

Research Slack MCP
Research exactly this subject for Sentinel using web search and opening primary-source pages. Date context 2026-10-30; user is in India. Subject: Slack MCP. Scope: Official/community, transport/spec, OAuth and unattended gateway/client restrictions, scopes/verification, exact tools/annotations and outbound actions, free plan/rate limits, setup and feasibility.. Prioritize official vendor docs, MCP specs/changelogs, GitHub repos/releases/issues/security advisories; label secondary sources. Every material claim needs URL, date/version, type, direct quote under 25 words and status DOCUMENTED/REPORTED/INFERRED. Explicitly say NOT FOUND or UNVERIFIED rather than guess. Flag sources older than six months or version-sensitive claims. Include plan/tier and India region limits or unknown, counter-evidence, exact annotation names only when documented, and practical single-connector setup where relevant. Do not rely on snippets alone. Return concise substantive findings and source records in required JSON.
Subtask completed
Result
Summary of Slack MCP findings (as of 2026-10-30)
What Slack MCP is (transport, identity, and direction)
Slack exposes a hosted MCP endpoint at https://mcp.slack.com/mcp for external AI clients to read and act on Slack data.
The external-client-to-Slack direction uses JSON-RPC 2.0 over Streamable HTTP; SSE-based connections and Dynamic Client Registration are not supported for this direction.
Slackbot’s MCP client uses remote HTTP/SSE to connect to external MCP servers, which describes a separate, first-party client path. The two statements describe different connection directions and are not mutually contradictory in their own contexts.
What tools, actions, scopes, and annotations are documented
Documented capabilities (high-level labels, not complete wire names): search for messages/files/users/channels; file reads; channel/thread reads; user profiles and channel members; send and schedule messages; create conversations/channels; add/get reactions; create/update/read canvases; upload files; create/read/update lists, columns, and records.
May 13, 2026 changelog additions: reactions, conversation/channel creation, channel-member listing, emoji listing, and file reading.
Write-capable actions include sending/scheduling messages, creating conversations, adding reactions, creating/updating canvases, uploading files, and creating/updating list data. Deletion tools are not documented; list deletion not found in first-party MCP descriptions.
Tool identifiers (exact names) are not fully published; guesses like slack_* names are not confirmed.
User scopes: per-action scopes are published (examples include search:read.*; files:read/files:write; emoji:read; chat:write; histories; channel/group/im/mpim writes; reactions:write/read; canvases:read/write; users:read; lists:read/write). Plan to apply least privilege; exact per-tool scope mappings beyond labels are not independently confirmed.
OAuth, verification, and unattended use
OAuth requires fixed app identity; confidential OAuth uses client_id and client_secret; PKCE is available for certain flows; user authorization is required; only Marketplace-published or internal apps are eligible; admin/workspace approval required.
Token rotation: user tokens can rotate; access tokens expire after 12 hours; refresh tokens are one-use and replaced on refresh. Fully headless, unattended authorization is not established as documented; noninteractive credential options are not found or verified.
No Dynamic Client Registration (DCR); IP allowlisting may apply to MCP calls.
Plan, rate limits, and setup
MCP rate limits align with Web API tiers (e.g., some tools at Tier 2/3/4). MCP inherits corresponding Web API rate limits. No public documentation of a minimum Slack plan for external MCP clients.
Slackbot is listed on Business+ and Enterprise+, but that does not confirm plan prerequisites for external MCP server access in all cases.
India data residency notes exist (Mumbai region, Hyderabad backup) but do not document an India-specific MCP endpoint or MCP feature locality; residency notes cover data at rest and plan requirements for residency.
Practical single-connector setup (documented)
Use the remote connector at https://mcp.slack.com/mcp.
CLI example: codex mcp add --transport http slack https://mcp.slack.com/mcp, then codex mcp login slack.
For a custom client: use a Slack internal or Marketplace-published app with MCP enabled, configure redirect URI, obtain admin approval, supply fixed client_id (and secret for confidential OAuth), request only needed user scopes, and ensure IP allowlisting if configured. If an IP allowlist is enabled, include gateway egress IP.
Gaps and cautions
The complete authenticated tools/list for the Slack MCP server was not publicly retrievable; exact tool identifiers beyond the documented upload tools, full schemas, and live authorization-dependent visibility remain UNVERIFIED.
No documented MCP deletion operations; “manage” wording does not confirm delete capabilities.
A minimum plan requirement for external MCP access and India-specific MCP endpoints/processing locations are NOT FOUND or UNVERIFIED.
No explicit unattended/service-account guarantee for MCP; persistent gateways rely on attended authorization and secure credential handling.
Marketplace/internal app eligibility and admin approval are described, but no separate MCP security certification or full OAuth verification policy is documented.
Key sources (trust but unverified)
Slack MCP server docs (transport, SSE/DCR restrictions)
MCP setup and codex example guides
Changelog: new MCP tools
Slack help: org-level per-tool access controls
MCP protocol and authorization specs (external standard)
Slack OAuth user-access reference and token rotation guidance
Slack data residency and pricing/plans pages
Slack MCP endpoint behavior and live status observations
Overall assessment
The Slack MCP server is documented as a hosted endpoint with Streamable HTTP/JSON-RPC and explicit limitations (no SSE, no DCR). Access requires a fixed Slack app identity with admin approval and appropriate user scopes. Token rotation and user consent are articulated, but unattended, non-interactive use is not proven. Practical setup steps exist for a single-connector configuration, but exact tool IDs, complete tool list, and full per-tool authorization guarantees are not publicly verifiable. The presence of plan limitations, India-specific MCP access, and full lifecycle capabilities (including deletions) cannot be confirmed from the available sources.

Research Microsoft 365 MCP: Outlook, Teams, SharePoint/OneDrive
Research exactly this subject for Sentinel using web search and opening primary-source pages. Date context 2026-10-30; user is in India. Subject: Microsoft 365 MCP: Outlook, Teams, SharePoint/OneDrive. Scope: Per workload owner official/community; transport/spec; delegated/app auth and unattended gateway/client restrictions; permissions/consent/admin requirements, India plans; exact tools/annotations/effects; cost/setup. Mark products separately.. Prioritize official vendor docs, MCP specs/changelogs, GitHub repos/releases/issues/security advisories; label secondary sources. Every material claim needs URL, date/version, type, direct quote under 25 words and status DOCUMENTED/REPORTED/INFERRED. Explicitly say NOT FOUND or UNVERIFIED rather than guess. Flag sources older than six months or version-sensitive claims. Include plan/tier and India region limits or unknown, counter-evidence, exact annotation names only when documented, and practical single-connector setup where relevant. Do not rely on snippets alone. Return concise substantive findings and source records in required JSON.
Subtask completed
Result
Concise summary of the structured results on Microsoft 365 MCP: Outlook, Teams, SharePoint/OneDrive
Key conclusion
The recommended/current product for new work is Microsoft Work IQ MCP (Microsoft-owned). Legacy, workload-specific Microsoft-hosted MCP tools for Mail, Teams, SharePoint, and OneDrive are described as backward compatibility-only and not advised for production or new projects.
What is Work IQ MCP
Scope: Work IQ covers Outlook mail, Teams messages, and OneDrive/SharePoint documents, with a single MCP endpoint and a unified workload surface.
API surface and tools: Work IQ exposes generic tools (fetch, fetch_blob, create_entity, update_entity, delete_entity, do_action, call_function) and Copilot tools (ask, retrieve, list_agents), plus schema tools (get_schema, search_paths). Workload access is navigated via paths such as /me/messages, /me/chats/{id}/messages, and drive-related paths.
Auth: Delegated Entra authentication with on-behalf-of (OBO) flow is supported; application-only authentication is not documented as supported. Unattended operation requires a valid user context; a service-principal-only setup is not documented.
Mutations: Mutations (create/update/delete/action) are denied by default; tenant admins can enable allowed mutations through the admin center policy. Policy is tenant-wide and changes can take up to 24 hours to apply.
Governance: A tenant admin must enable Work IQ and grant consent (WorkIQAgent.Ask). Policy governs mutations; enforcement is at the tenant level.
Endpoint and deployment notes
Remote MCP endpoint: workiq.svc.cloud.microsoft/mcp. The live endpoint and CLI integration are supported via Copilot CLI or local stdio client.
Local/stdio setup: For local use, install the Work IQ CLI (npm install -g @microsoft/workiq or npx). Start with workiq mcp, and use the live server for tool discovery via tools/list. Mutations should be blocked by default until policy allows them.
Tool discovery caveat: The live tools list may differ from published references; the authoritative source is the live server’s tools/list.
Gaps and uncertainties to verify in your tenant
India availability and data residency for Work IQ MCP: Not established; India-specific eligibility and data-processing commitments are unverified.
Exact tool annotations and values: Work IQ’s public references do not disclose actual tool annotation fields or their emitted values; do not rely on inferred hints to determine read-only or destructive nature.
Older admin guidance vs current API: There are older admin/docs references listing per-user licenses and Graph scopes that may not reflect the current API setup or licensing model; verify against your tenant’s configuration.
Legacy tools and backward compatibility: Legacy Mail/Teams/SharePoint/OneDrive MCP references exist but are not intended for production use; confirm tenant policy and live tool availability before implementation.
Practical guidance for implementation
Start with Work IQ as the single MCP path; have the tenant admin enable Work IQ and grant consent.
Use tools/list to discover available capabilities; confirm the exact workload paths your tenant supports.
Enforce policy to block mutations by default; enable only the mutations your organization approves, and monitor policy propagation (up to ~24 hours).
Be aware of 5 MB file-size limits for legacy MCP tool references; Work IQ supports broader capabilities but verify path-specific limits in live documentation.
Plan for ongoing validation of the live tool list, since published tool counts and names may diverge from the actual server state.
Facts preserved from the result
Work IQ MCP is the recommended/current product for new projects.
Legacy Mail/Teams/SharePoint/OneDrive tools are backward compatibility-only.
Delegated authentication (OBO) is required; app-only authentication is not documented as supported.
Mutations are blocked by default; tenant policy governs enabling mutations.
Endpoint for Work IQ MCP is workiq.svc.cloud.microsoft/mcp.
5 MB limits apply to legacy SharePoint/OneDrive tool references.
India availability/residency for Work IQ MCP is UNVERIFIED.
The live tools list may vary by tenant/region/rollout.
If you want, I can extract a minimal action checklist or a tenant-specific validation plan based on these findings.

Research Atlassian Jira and Confluence MCP
Research exactly this subject for Sentinel using web search and opening primary-source pages. Date context 2026-10-30; user is in India. Subject: Atlassian Jira and Confluence MCP. Scope: Official/community, transport/spec, OAuth/PAT/unattended viability, scopes, pricing/rate limits, exact tools/annotations and consequential actions, setup and feasibility. Mark separately.. Prioritize official vendor docs, MCP specs/changelogs, GitHub repos/releases/issues/security advisories; label secondary sources. Every material claim needs URL, date/version, type, direct quote under 25 words and status DOCUMENTED/REPORTED/INFERRED. Explicitly say NOT FOUND or UNVERIFIED rather than guess. Flag sources older than six months or version-sensitive claims. Include plan/tier and India region limits or unknown, counter-evidence, exact annotation names only when documented, and practical single-connector setup where relevant. Do not rely on snippets alone. Return concise substantive findings and source records in required JSON.
Subtask completed
Result
Summary of validated MCP findings for Atlassian Jira and Confluence
Core MCP offering and endpoint
Atlassian’s Rovo MCP is a cloud-hosted MCP server connecting AI clients to Atlassian Cloud apps.
Current endpoint cited: https://mcp.atlassian.com/v2/mcp
One connector is intended to access Jira and Confluence sites/apps; authorization occurs in the compatible client.
Public docs describe a URL-only MCP server setup and OAuth initiation in the client.
The MCP transport variant deployed by Atlassian is not explicitly identified as Streamable HTTP in the reviewed Atlassian setup docs; Streamable HTTP is defined separately in MCP specs.
Auth and unattended usage
Interactive authentication: OAuth 2.1 is the recommended path (user consent, existing permissions, site/cloudId scope).
Unattended / headless use: Atlassian documents API-token authentication options (personal token via Basic auth; admin-created service-account API key via Bearer).
Jira and Confluence tool catalogs indicate support for both OAuth 2.1 and API-token usage.
API-token caveats: limited tool availability, tokens not bound to a site/cloudId (cloudId must be supplied when required), OAuth domain allowlists do not apply; IP allowlists still apply.
Best practices: apply least privilege, enforce token rotation/storage/audit, enable only necessary permission groups.
Scopes and catalog
Catalog and tool-scopes are version-sensitive; Atlassian’s tools guide was last updated Oct 27, 2026.
Required permission-group scopes (examples):
Jira: read/write/search/delete/manage for agent-interface; plus related read/write scopes for specific Jira actions.
Confluence: read/write/search for agent-interface.
Admins grant/revoke group access; each tool inherits the assigned group.
Common tools and tool-annotations (e.g., atlassianUserInfo, discover, executeRead/Write/Destructive) exist in the catalog; exact per-tool annotation values in MCP schema are not publicly published.
Consequential actions and safety
Sensitive actions like delete_jira and manage_jira are disabled by default; require admin enablement.
Confluence write capabilities include content changes, permissions management, and public-link controls; public list shows archive/unarchive but not a dedicated permanent delete group.
Some actions, such as updateJiraScreen, produce a plan by default and require explicit commit.
The runtime UX for confirmations is client-dependent.
Plan, pricing, credits, and limits
Connecting MCP is described as free; credits (Rovo) may apply to enriched context via the Teamwork Graph.
Current included allowances: 25 credits/user/month for Jira/Confluence Standard; 70 for Premium; 150 for Enterprise (org-level pool).
Most enriched calls are stated as 1–10 credits; some Confluence actions may be 15–30.
Extra billing begins Dec 3, 2026; current price cited as $0.01/credit.
Subscription seat pricing, India-local pricing/taxes, and Free-tier eligibility are not explicitly verified.
Quota and rate-limiting
No official MCP per-second or per-hour quota publicly documented in the reviewed materials.
A community post cites 1,000 calls/hour plus 20 per user (up to 10,000/hour cap) but this is unverified and not corroborated by vendor docs.
Jira REST API rate limits exist (external to MCP) and are separate from MCP quotas.
India hosting and residency
Atlassian data-residency shows India (Asia Pacific, Mumbai) regions exist.
App data default to Global unless pinned; user location in India does not automatically pin data to India.
No explicit statement on MCP processing residency in Mumbai or India-specific MCP endpoints.
Source caveats and gaps
Atlassian docs are living pages; catalog date is Oct 27, 2026.
The official MCP repo releases API returned no entries as of 2026-10-30; no formal release record found there.
Some items (per-tool annotation values; India-specific MCP processing commitments) remain unverified or not found publicly.
No authenticated, live tools list was executed; tool names derive from the public Oct 27 catalog.
If you want, I can extract a concise checklist for enabling MCP with Jira/Confluence (including recommended auth mode per scenario) or map the exact scopes to a specific integration use case.

Research Notion MCP
Research exactly this subject for Sentinel using web search and opening primary-source pages. Date context 2026-10-30; user is in India. Subject: Notion MCP. Scope: Official/community, remote/local transport/spec, OAuth and unattended gateway viability/client restrictions, scopes/integration sharing, exact tools/annotations/write/delete actions, pricing/setup/time.. Prioritize official vendor docs, MCP specs/changelogs, GitHub repos/releases/issues/security advisories; label secondary sources. Every material claim needs URL, date/version, type, direct quote under 25 words and status DOCUMENTED/REPORTED/INFERRED. Explicitly say NOT FOUND or UNVERIFIED rather than guess. Flag sources older than six months or version-sensitive claims. Include plan/tier and India region limits or unknown, counter-evidence, exact annotation names only when documented, and practical single-connector setup where relevant. Do not rely on snippets alone. Return concise substantive findings and source records in required JSON.
Subtask completed
Result
Summary of Notion MCP findings (as of 2026-10-30)
Notion-hosted MCP is recommended over the self-hosted MCP server. Hosted endpoints: Streamable HTTP at https://mcp.notion.com/mcp (recommended) and SSE at https://mcp.notion.com/sse (fallback). Setup involves a client-side server entry and Notion OAuth; no user-managed deployment is described. No official setup-time estimate is provided.
OAuth, unattended operation, and clients
A custom client must support OAuth 2.0 Authorization Code with PKCE, Streamable HTTP or SSE, refresh-token handling, and secure token storage. Dynamic client registration is documented.
Live OAuth metadata indicates scopes default to default and ema_issuer:manage, plus grants including authorization_code, refresh_token, and JWT-bearer. The meaning or eligibility of ema_issuer:manage and JWT-bearer flow is not explained; unattended MCP via JWT-bearer is unverified.
Devin’s organization-access option exists but is client-specific and not general evidence of a universal gateway grant.
Some clients support remote MCP directly; forstdio-only clients, a bridge like mcp-remote can be used; self-hosted server remains a last resort and is unmaintained. Enterprise admins can apply MCP Governance controls; detailed user-usage visibility is not yet available.
Access, sharing, and scopes
Hosted MCP operates with the connected user’s Notion permissions; it does not bypass them.
The live resource metadata shows the scope default; there is no documented per-page OAuth scope segmentation for hosted MCP.
Access aligns with the user’s permissions rather than a per-call privilege boundary.
This hosted flow is distinct from public REST API integrations and from legacy local MCP; tooling and features vary by connection mode.
Tools and effects
Official hosted tool references include notion-search, notion-fetch (search/read); notion-get-self, notion-get-tool-access, notion-query-data-sources, notion-query-multiple-data-sources, and various comment/user/attachment tools.
Connected-source search is notion-connector-search; legacy notion-ai-search remains callable for cached clients but is not the active hosted listing.
Tool availability is conditional on authorization, plan, client, and connection mode; query tools via tools/list or notion-get-tool-access for the actual connection.
Content, schema, and destructive operations
Documented content/schema writes include: notion-create-pages, notion-update-page, notion-create-database, notion-update-data-source, notion-create-view, notion-update-view, notion-move-pages, notion-duplicate-page, notion-create-comment; additional tools cover file/attachment and Skills.
Page/database deletions are destructive tools: notion-delete-pages (up to 20 pages) and notion-delete-databases (up to 20 databases including their rows); require user_confirmed: true, move items to Trash, reject locked items, and require update-content capability. notion-restore-pages can recover eligible items.
Public tooling page documents destructiveHint: true for delete tools.
Comment-related actions: notion-delete-comment, notion-update-comment; discussion state changes also exist.
MCP schema and protocol notes
Current MCP schema (2026-07-28) lists annotation names: title, readOnlyHint, destructiveHint, idempotentHint, openWorldHint (all as hints, not guarantees).
Public tool documentation confirms destructiveHint: true for delete tools but does not publish a complete per-tool annotation manifest.
A community issue in the legacy local server concerns annotation misclassification; this is not evidence about the hosted service.
Plan, cost, time, and geography
Tool listings and plan gates may affect access; enterprise is required for certain governance controls.
Notion pricing is USD-denominated; no MCP-specific charge was found in reviewed pricing materials.
India-specific MCP availability and pricing were not found or were unverified.
No official setup-duration estimate was located.
Gaps and uncertainties to note
Time-to-connect/setup estimate is not provided.
JWT-bearer grant meaning and eligibility for unattended MCP are not explained in public docs.
No published per-page OAuth scope model or granular read/write scope names for hosted MCP.
No MCP-specific pricing data found; this does not prove free features apply to all related Notion capabilities.
India-specific availability and regional details remain unverified.
Public tool manifests do not cover every conditional tool or exact annotation values; actual tool sets can vary by plan, client, and connection mode.
Hosted docs and changelogs are dynamic and not versioned in a single release, leading to potential version sensitivity.
If you’d like, I can extract a compact checklist for a concrete implementation plan (e.g., for a specific client type or enterprise setup) or summarize the exact endpoints and tool names to test in a given environment.

Research Linear MCP
Research exactly this subject for Sentinel using web search and opening primary-source pages. Date context 2026-10-30; user is in India. Subject: Linear MCP. Scope: Official/community, transport/spec, OAuth/PAT and unattended gateway/client restrictions, scopes, exact tools/annotations/consequential actions, plans/limits/setup.. Prioritize official vendor docs, MCP specs/changelogs, GitHub repos/releases/issues/security advisories; label secondary sources. Every material claim needs URL, date/version, type, direct quote under 25 words and status DOCUMENTED/REPORTED/INFERRED. Explicitly say NOT FOUND or UNVERIFIED rather than guess. Flag sources older than six months or version-sensitive claims. Include plan/tier and India region limits or unknown, counter-evidence, exact annotation names only when documented, and practical single-connector setup where relevant. Do not rely on snippets alone. Return concise substantive findings and source records in required JSON.
Subtask completed
Result
Summary: Linear MCP (as of 2026-10-30) is documented to use a primary hosted endpoint at https://mcp.linear.app/mcp with SSE at /sse (deprecated). The system supports read/write operations via OAuth 2.1 flows and/or API keys, with read-only access available at /mcp/readonly. Live OAuth metadata shows scopes read and write for resource access, while the authorization server metadata also lists openid and email as identity scopes. Client ID Metadata Documents are advertised alongside a registration endpoint, reflecting a move away from Dynamic Client Registration (DCR in the MCP spec).
Key findings
Transport and endpoints
Primary: https://mcp.linear.app/mcp (read-write by default)
Read-only: https://mcp.linear.app/mcp/readonly
SSE endpoint at /sse is deprecated; /mcp is the preferred connection path
Unauthenticated probe to /mcp returns HTTP 401 with WWW-Authenticate: Bearer
Authentication and scopes
OAuth scopes observed: read and write for MCP resources
Authorization server metadata includes read, write, openid, and email
Client ID Metadata Documents supported; registration endpoint advertised
The MCP spec notes DCR deprecation in favor of Client ID Metadata Documents, but Linear docs still reference DCR
Credentials and access control
Authorization: Bearer token or Linear API key accepted
API keys can be limited by scope (Read, Write, Admin, Create issues, Create comments) and by workspace teams
Admins can enforce key creation restrictions; keys can be viewed and revoked
There is no explicit guarantee documented for unattended service accounts or long-lived refresh tokens specific to MCP
Tools, actions, and scope
Linear supports finding, creating, and updating issues, projects, and comments
The default MCP connection is read-write; least-privilege practice recommended
Not found in official docs: a complete, current per-tool catalog (tools/list) or per-tool annotation values; authenticated live checks are needed for exact inventories
Limits and plan
MCP is included in Free, Basic, Business, and Enterprise plans; no MCP-specific quota published
General GraphQL limits are documented (API-key 2,500 requests/hour; OAuth app 5,000/hour; per-query complexity limits), but these are not MCP-specific quotas
Region and version notes
No India-specific MCP availability or data residency found; region behavior remains unknown
Latest MCP spec cited is 2026-07-28; deprecates DCR, supports Client ID Metadata Documents; live metadata cites both approaches
SSE deprecation noted, but some reports indicate registry inconsistencies; current docs favor /mcp while still acknowledging SSE as legacy
Gaps and caveats
Current authenticated MCP tools/list output, exact tool names/schemas, and per-tool annotation values are not verified beyond documented hints; live inspection required for precise catalog
No explicit, published MCP-specific quotas or concurrency limits beyond general GraphQL limits
No explicit guarantee for unattended service accounts or token rotation policies specific to MCP
India-region availability and data residency are not established
Some old/reported items (e.g., certain tool endpoints or names) may be outdated; treat as historical context
Bottom line
Use the primary endpoint https://mcp.linear.app/mcp for new MCP connections; /sse is deprecated
Authentication via Bearer tokens or API keys is supported; use read scope for read-only tasks and write scope for changes
Read-only access is available at /mcp/readonly
Expect a shift toward Client ID Metadata Documents in registration and metadata, with DCR retained for backward compatibility
Exact tool catalog, quotas, and unattended-service guarantees require live verification of current authenticated session and workspace context

Research Postgres and Supabase MCP
Research exactly this subject for Sentinel using web search and opening primary-source pages. Date context 2026-10-30; user is in India. Subject: Postgres and Supabase MCP. Scope: Separate Supabase owner server from PostgreSQL reference/community servers; repo maintenance, transport/spec, database/API/service-role credentials and unattended gateway viability, exact tools/annotations and SQL write/destructive effects, free tier/setup.. Prioritize official vendor docs, MCP specs/changelogs, GitHub repos/releases/issues/security advisories; label secondary sources. Every material claim needs URL, date/version, type, direct quote under 25 words and status DOCUMENTED/REPORTED/INFERRED. Explicitly say NOT FOUND or UNVERIFIED rather than guess. Flag sources older than six months or version-sensitive claims. Include plan/tier and India region limits or unknown, counter-evidence, exact annotation names only when documented, and practical single-connector setup where relevant. Do not rely on snippets alone. Return concise substantive findings and source records in required JSON.
Subtask completed
Result
Summary of the untrusted MCP findings for Postgres and Supabase
Key conclusions
Supabase MCP is a hosted gateway for projects via https://mcp.supabase.com/mcp, with project-scoped access and a typical single connector per Supabase project; direct-Postgres connections require a separate database URI/password. Unattended use should rely on project-scoped PATs with read-only permissions where possible.
Supabase’s own server management notes emphasize the need to set project_ref and limit features for safety; the latest release v0.15.0 (dated 2026-10-29) added submit_feedback and delete_feedback tools, with the docs’ tool inventory not fully synchronized to reflect those names.
Direct PostgreSQL connectors use standard database credentials; avoid secret keys like service_role for MCP access. A least-privilege database role is recommended for direct connectors.
The Supabase tool surface exposes a broad set of tools (database operations, migrations, logs, project management, branching, Edge Functions, storage config, etc.) with both read and write capabilities; destructive actions require appropriate gating and server-side permissions. Some mutations (e.g., execute_sql, apply_migration) can be blocked under read-only mode.
The MCP annotations in the source are hints, not guarantees; read-only mode can block certain operations, but client implementations and server permissions determine actual behavior.
The archived MCP PostgreSQL reference (modelcontextprotocol/servers-archived) is explicitly unmaintained; there is a historical security-vulnerability report indicating possible bypasses in that legacy server, but no current official advisory for the MCP stack.
A community alternative, CrystalDBA/postgres-mcp, provides SSE and stdio transports with read-only and read/write modes; however, its security posture, current commits, and authentication setup are not consistently verified in the inspected materials.
Notable details and numbers
Supabase MCP owner server release: mcp-server-supabase-v0.15.0, dated 2026-10-29; added submit_feedback and delete_feedback.
Supabase free plan: two free projects; free projects pause after one week of inactivity; branching requires a paid plan. Regions include South Asia (Mumbai, ap-south-1). Mumbai availability for free plans is UNVERIFIED.
Authentication: interactive OAuth for MCP; unattended use may employ a project-scoped PAT in the Authorization header; PATs must be kept secret and scoped to needed tools.
Direct PostgreSQL access uses a standard URI with a postgres user; avoid service_role keys for MCP access.
Annotation semantics (MCP schema): ToolAnnotations include readOnlyHint, destructiveHint, idempotentHint, openWorldHint; exact values are version-sensitive and subject to change.
Gaps and cautions
No current official security advisory or verified patched release for the archived modelcontextprotocol PostgreSQL package; the Datadog report is historical and secondary.
Region and plan limitations for the Free plan (especially Mumbai) are UNVERIFIED; pricing/tier restrictions are time-sensitive.
Supabase docs show potential drift with actual tool availability (e.g., query_logs vs get_logs); actual tool lists should be confirmed via tools/list at runtime.
CrystalDBA’s PostgreSQL MCP is a separate community project; authentication/remote access controls for public exposure were not found in inspected setup instructions and remain UNVERIFIED.
Exact annotation values for CrystalDBA and other community MCP servers were NOT FOUND in the inspected primary documentation.
Practical guidance (condensed)
For read-only MCP use with Supabase: configure a single MCP server entry with read_only=true and narrow features (e.g., database, docs); authenticate via OAuth and consider a scoped PAT for unattended scenarios if secret storage is secure.
For direct Postgres access: use a dedicated least-privilege database role and a connection URI/password; avoid service_role keys for MCP connections.
Validate tool capabilities at runtime via tools/list before relying on any mutation capability; acknowledge that some mutations may be gated by server permissions or plan constraints.
Treat archived reference implementations as historical context only; rely on current Supabase MCP docs and latest server releases for operational guidance and security posture.
If you’d like, I can extract a shorter bullet-point brief or tailor a setup checklist for a read-only Supabase MCP integration based on these notes.

Research MCP filesystem server
Research exactly this subject for Sentinel using web search and opening primary-source pages. Date context 2026-10-30; user is in India. Subject: MCP filesystem server. Scope: Official/reference status, maintenance/security, stdio vs remote, spec, auth/gateway concerns, exact tools/annotations/file write-delete effects, cost/setup and subprocess privilege risk.. Prioritize official vendor docs, MCP specs/changelogs, GitHub repos/releases/issues/security advisories; label secondary sources. Every material claim needs URL, date/version, type, direct quote under 25 words and status DOCUMENTED/REPORTED/INFERRED. Explicitly say NOT FOUND or UNVERIFIED rather than guess. Flag sources older than six months or version-sensitive claims. Include plan/tier and India region limits or unknown, counter-evidence, exact annotation names only when documented, and practical single-connector setup where relevant. Do not rely on snippets alone. Return concise substantive findings and source records in required JSON.
Subtask completed
Result
Summary of MCP filesystem server (based on the provided structured result)
Status and maintenance
The upstream repository is an official MCP Steering Group-maintained collection. It explicitly states its servers are educational reference implementations, not production-ready products.
Maintenance is active as of 2026-10-30. Latest release notes show server-filesystem 2.1.0 with fixes (bounded realpath/readdir waits, cross-filesystem moves, and path/root handling).
Conclusion: the server is not abandoned, but should be treated as reference software with security responsibility on deployers.
Transport, protocol, and access boundary
The upstream code uses StdioServerTransport; there is no official HTTP/remote transport in this package.
The MCP stdio model runs as a client-launched subprocess exchanging newline-delimited JSON-RPC over stdin/stdout; logs go to stderr; stdout must contain only protocol messages.
The filesystem README suggests configuring allowed directories on the command line. Roots are deprecated in the 2026-07-28 spec; new implementations should not adopt Roots.
Current MCP 2026-07-28 is stateless and uses per-request metadata; compatibility with legacy clients means version sensitivity.
Tools and effects
Documented API/tools include: read_text_file, read_media_file, read_multiple_files, write_file, edit_file, create_directory, list_directory, list_directory_with_sizes, move_file, search_files, directory_tree, get_file_info, list_allowed_directories.
Legacy read_file is deprecated.
There is a noted discrepancy: a “delete directories” bullet exists in the README, but there is no explicit delete-file/delete-directory tool in the API list. This inconsistency should be reconciled against a pinned release.
move_file performs a move/rename and removes the source path; destination must not exist.
write_file creates or overwrites in place and is non-crash-atomic; partial content can remain if interrupted.
edit_file supports dryRun; create_directory creates parents; repeated creation is a no-op.
Annotations (openWorldHint, readOnlyHint, idempotentHint, destructiveHint) accompany tools, but they are descriptive and not enforcement mechanisms.
Security and gateway/auth concerns
A CVE-2025-53110 advisory (path-validation bypass) affected older versions; fixed in July 2025. This is old relative to current releases; does not confirm current vulnerability status.
The latest 2026 release shows fixes; the repository notes caution that reference servers are not production-ready.
Authorization for MCP is optional; HTTP transports should follow OAuth, while stdio transports do not rely on HTTP OAuth and obtain credentials from the environment.
If a gateway exposes the local server remotely, the gateway must enforce remote authentication and access controls; there is no official remote filesystem service or MCP-specific OAuth for this package.
No official guidance on Origin validation beyond the MCP transport spec; localhost binding is recommended for local usage.
Setup, cost, privilege, India
Typical local setup: install Node.js, run npx -y @modelcontextprotocol/server-filesystem@2.1.0 /absolute/path/to/one/work-folder, and grant only a dedicated directory.
Node.js 24+ is recommended; patched versions such as 24.22.1 or 26.12.1 (or later) are advised as of October 2026.
Pinning the package version is recommended for reproducibility.
Docker bind-mount and read-only options are documented for isolation.
The documentation does not state any paid tier, regional hosting plan, or India-specific availability; any costs are host-dependent and unverified in the provided data.
A local stdio process has no inherent service region; if remotely hosted, India residency/plan terms are unverified.
Gaps and cautions (as reported)
No official direct delete-file/delete-directory tool is listed, though a README bullet mentions directory deletion; verify against a pinned release.
CVE information references older versions; current vulnerability status for v2.x (2.1.0) is not established here.
No official remote HTTP transport or remote-hosted filesystem service identified; gateway/auth deployment specifics (region, residency) are unverified.
Documentation and main branch content can change; always pin a release/tag and audit its files and Node runtime during implementation.
Notes for practitioners
Treat this as reference software with security responsibility on deployment; not a guaranteed production-grade solution.
When implementing, pin versions, verify tool availability against the exactRelease, and consider containerization with restricted mounts.
If remote exposure is contemplated, design gateway-layer authentication and network controls independently of the stdio transport’s scope.

Research Composio
Research exactly this subject for Sentinel using web search and opening primary-source pages. Date context 2026-10-30; user is in India. Subject: Composio. Scope: Official current architecture, credential custody/refresh, scoping, per-call policy vs auth, MCP compatibility, prices/plans/limits and India availability; commodity vs differentiated.. Prioritize official vendor docs, MCP specs/changelogs, GitHub repos/releases/issues/security advisories; label secondary sources. Every material claim needs URL, date/version, type, direct quote under 25 words and status DOCUMENTED/REPORTED/INFERRED. Explicitly say NOT FOUND or UNVERIFIED rather than guess. Flag sources older than six months or version-sensitive claims. Include plan/tier and India region limits or unknown, counter-evidence, exact annotation names only when documented, and practical single-connector setup where relevant. Do not rely on snippets alone. Return concise substantive findings and source records in required JSON.
Subtask completed
Result
Composio is described as a hosted integrations and execution control plane. Key elements include sessions that bind a user ID, toolkits, auth configuration, and connected accounts; a Tool Router for discovering and executing actions; and a default Cloud custody model where provider credentials can be stored server-side and decrypted during execution. Prebuilt connectors, OAuth, and token refresh are treated as commodity capabilities, with stronger differentiation coming from per-user/project/session scoping, execution routing, approvals/policy, proxy access, and hosted MCP. These differentiation points are inferred from documented features rather than vendor claims.
Security and credential custody
In default Composio Cloud, the vendor states custody of credentials, with API responses redacting secrets and automatic OAuth refresh where supported. Revoked or expired refresh tokens require reconnection.
Self-managed credentials are distinct: Composio states it does not store or refresh tokens that are passed in by the customer.
Enterprise deployments can use customer-managed keys via a KMS setup. These properties are vendor-documented, not independently verified here.
Scoping, authorization, and policy
Provider OAuth scopes define provider grants; Composio session filtering constrains toolkits, tools, and tags. Sessions bind stable user IDs to authenticated application users; caller-provided IDs should not be trusted.
Per-call approval is documented as experimental (requireApproval / require_approval).
Firewall behavior includes requests/results filtering; an after-execute check cannot reverse a completed action.
Proxy Execute requires separate API-key permission; toolkit allowances apply, but per-tool and per-tag restrictions do not constrain arbitrary HTTP endpoints.
Documented tag names include readOnlyHint, createHint, updateHint, destructiveHint; MCP adds readOnlyHint, destructiveHint, idempotentHint, openWorldHint as hints, not guarantees.
MCP (hosted MCP)
Composio offers hosted MCP per configured session, with session.mcp.url and SDK-provided headers. A project-key session uses an x-api-key scoped to the project; a user-only x-user-api-key can reach across the organization. Direct-tools presets provide a small fixed tool set.
MCP bypasses SDK beforeExecute/afterExecute hooks and schema transforms, and does not expose local in-process tools. The latest MCP spec reviewed is dated 2026-07-28; compatibility with that revision is unverified.
Plan: MCP support compatibility is unverified against the cited MCP spec.
Plans, pricing, and limits
Pricing page (effective 2026-08-15; grandfathering through 2026-12-31): Hobby is free with 100,000 tool calls/month, 50,000 triggers/month, and 3 team members. Pro includes a $29 monthly usage credit; a separate Pro subscription price is not clearly listed on the page. Enterprise is custom.
Rate limits per plan exist, with stated values across Hobby, Pro, and Enterprise; a separate, independent rate-limit document notes a 20,000 Hobby / 100,000 Growth per rolling 10 minutes, with some labeling/window conflicts. The exact enforcement in the dashboard may differ from the published labels.
Separate pricing for Composio-managed apps: up to 20,000 calls and 10,000 triggers included, then per-call/per-trigger overage rates apply. First 1,000 managed connections are free, after which there is a per-connection charge.
New pricing applies to signups on/after 2026-08-15; existing customers are grandfathered through 2026-12-31.
Geography, residency, and India
Composio Cloud runs in the United States. EU residency is achievable via self-hosting in an EU region. There is no official India-hosted Composio Cloud or India residency documented, and India-specific plans, payments, or INR billing eligibility are not found. The Mixpanel region for India is referenced only as a connector API region, not as hosting residency.
This India availability status is UNVERIFIED; pricing and tax implications are also unknown.
Security incident and controls
May 2026 incident disclosed: about 0.3% of active connections affected, including 5,001 GitHub connections and 5,241 potentially exposed API keys. Vendor updates emphasize token redaction, envelope encryption, hashed keys, OIDC/internal service changes, scoped keys, IP allowlisting, and optional customer-managed keys as remediation measures.
An independent breach analysis noted API keys exfiltration, but vendor language differentiates between “potentially exposed” vs “exfiltrated” tokens. The incident remains a material factor in assessing credential exposure risk.
Practical setup guidance (summary)
Create one session per app user with a stable ID, and use an allowlist of specific tools (e.g., GMAIL_FETCH_EMAILS, GMAIL_CREATE_EMAIL_DRAFT) as needed.
Use MCP only if required by the client; avoid exposing MCP endpoints to unintended origins.
Use a project key for session management and tool execution permissions; enable per-tool approvals when enabling sensitive actions like sending email.
Be aware that protocol revision support for MCP is not clearly defined; verify compatibility against current MCP specs before production.
Overall assessment
The available documentation suggests Composio is a versatile credential/execution intermediary with per-user isolation and multi-framework/MCP deployment capabilities. It differentiates itself through session-based scoping, token custody models, and policy enforcement, but certain aspects remain unverified, such as India residency, exact MCP protocol compatibility, and precise rate-limit enforcement in practice.
Before regulated or production use, confirm India residency status, current rate-limit semantics, exact MCP support status, incident assurance details, and proxy restriction behavior.

Research Arcade.dev
Research exactly this subject for Sentinel using web search and opening primary-source pages. Date context 2026-10-30; user is in India. Subject: Arcade.dev. Scope: Official current credential custody/refresh, scopes and per-call policy, MCP, price/tiers, India/region limits, version/dates and differentiated features.. Prioritize official vendor docs, MCP specs/changelogs, GitHub repos/releases/issues/security advisories; label secondary sources. Every material claim needs URL, date/version, type, direct quote under 25 words and status DOCUMENTED/REPORTED/INFERRED. Explicitly say NOT FOUND or UNVERIFIED rather than guess. Flag sources older than six months or version-sensitive claims. Include plan/tier and India region limits or unknown, counter-evidence, exact annotation names only when documented, and practical single-connector setup where relevant. Do not rely on snippets alone. Return concise substantive findings and source records in required JSON.
Subtask completed
Result
Arcade.dev is presented as a consolidated gateway for selecting and authenticating a curated set of tools across both Arcade’s own gateway and remote MCP servers. Key points from the validated result:
Credential custody and refresh
Tool-level authorization checks occur at invocation; if missing, Arcade initiates an OAuth flow and injects the token into the tool runtime context (not exposed to the client or LLM). Tokens can be reused or refreshed for subsequent calls.
OAuth2 supports authorization-code flow with or without PKCE; per-provider refresh token availability determines whether refresh is used.
Server vs. tool-level authorization
Resource Server Auth protects MCP HTTP requests, while tool-level auth governs downstream access to third-party APIs. Arcade deploy handles front-door security; production HTTP servers outside that flow require Resource Server Auth.
Scopes and per-call policy
Tools declare provider-specific scopes (e.g., GitHub repo, Reddit read). Authorization checks occur when the tool runs. If requirements are unmet, user authorization is prompted and the tool must be invoked again.
Not a universal per-action human-confirmation policy; guidance varies by gateway/client configuration. Do not assume every Arcade invocation requires approval.
Current documentation does not list exact Arcade policy/annotation names; an archived reference exists, but current hosted integrations’ wire contracts are not enumerated.
MCP and differentiated features
Arcade provides a single Streamable HTTP(S) gateway: https://api.arcade.dev/mcp/{GATEWAY_SLUG}.
Supported auth modes: Arcade Auth (browser OAuth), User Source (OIDC), Arcade Headers (API key with Arcade-User-ID).
Remote servers are registered at project/organization scope; gateways are curated, with a catalog claim of thousands of tools across many MCP servers. A vendor-claimed open-source MCP framework underpins the stack.
Practical single-connector setup
Steps: create a gateway, select needed tools, choose Arcade Auth or User Source, add gateway URL as a remote MCP connector, complete OAuth. Use Arcade Headers only when browser-based authentication/refresh is not possible.
Pricing
Live pricing observed: Free ($0/month) with 2,000 auth events and 2,000 tool calls; Team ($25/month) plus usage; Enterprise is custom.
No region-specific pricing or INR details identified on the observed page.
India data residency
Arcade Cloud storage/processing is in the United States; self-hosting is offered for residency control. No India-hosted Cloud region is documented, and India-specific legal/billing terms were not found in the primary sources.
Versioning and date caveats
Arcade MCP server framework on PyPI is 1.33.0 (released 2026-10-29). Hosted-service version numbers were not found.
Changelog notes (latest dated 2026-07-26) are older than the observed October documentation; reflect behavior annotations and token-scoped flows but do not provide a current, unified annotation name list.
An archived TypeScript MCP port and related issues indicate historical metadata paths but are not current service contracts.
Gaps and cautions to verify before procurement
No confirmed current Arcade Cloud/Engine service build or release version beyond the open-source Python MCP server 1.33.0.
No official India-region Arcade Cloud deployment or India-specific terms confirmed; self-hosting is possible but India-residency specifics require direct clarification.
Exact names for MCP behavior annotation properties are not enumerated in current vendor sources.
Pricing page lacks a published revision date; confirm current terms and regional applicability before commitment.
The MCP protocol reference used is from 2025-06-18 and may lag behind newer practice; rely on the latest vendor and MCP spec updates for integration work.
If you’d like, I can summarize potential decision implications (security posture, residency considerations, and procurement questions) or extract a concise checklist for vendor discussions based on these findings.

Research Keycard
Research exactly this subject for Sentinel using web search and opening primary-source pages. Date context 2026-10-30; user is in India. Subject: Keycard. Scope: Resolve exact current product identity from primary sources; credential custody, scopes, per-call policy, MCP, pricing/availability; if ambiguous state NOT FOUND/UNVERIFIED.. Prioritize official vendor docs, MCP specs/changelogs, GitHub repos/releases/issues/security advisories; label secondary sources. Every material claim needs URL, date/version, type, direct quote under 25 words and status DOCUMENTED/REPORTED/INFERRED. Explicitly say NOT FOUND or UNVERIFIED rather than guess. Flag sources older than six months or version-sensitive claims. Include plan/tier and India region limits or unknown, counter-evidence, exact annotation names only when documented, and practical single-connector setup where relevant. Do not rely on snippets alone. Return concise substantive findings and source records in required JSON.
Subtask completed
Result
Summary of Keycard research results
Identity and scope
Keycard is positioned as an AI-agent identity, runtime authorization, and credential-brokering platform. It is not a physical access-card product.
Core materials emphasize agent identity, policy, and audit; the About page and product announcements support this framing. The homepage foregrounds an Agent Baseline white paper rather than a detailed product overview.
Credential custody and token behavior
Secret materials stored in Keycard’s database include OAuth access/refresh tokens, customer static credentials, signing keys, and provider secrets, with zone-level envelope encryption and an Enterprise KMS option.
Apps receive time-limited tokens; revocation can prevent future issuance/refresh but may not invalidate already-issued tokens immediately (tokens may remain valid until expiry; typical access-token defaults are 24 hours, configurable per resource down to one minute).
Scopes are resource/provider-specific rather than universal; MCP-related example scopes (e.g., mcp:tools) are documented as examples, not universal Keycard scopes.
Per-call policy and MCP (machine credential provisioning)
Policy is Cedar-based and evaluated at credential issuance; enforcement can occur on protected/gateway paths or within an MCP handled flow, but per-call enforcement is not universal for all Keycard use.
In practice: a gateway path or protected resource triggers per-call checks; MCP token exchange is supported, with token issuance flows for upstream APIs. If the MCP server is API-key-backed, a Unified Access Gateway pattern is recommended.
Documentation distinguishes between session credential hydration (for a coding agent’s session) and per-call policy enforcement.
MCP integration and tooling
MCP-related materials describe OAuth metadata, bearer verification, and audit wiring; a single-connector pattern is suggested: register an MCP server as a Keycard Resource, bind OAuth metadata to the Resource audience, and use token-exchange flows for upstream APIs.
MCP annotations like readOnlyHint, destructiveHint, idempotentHint, openWorldHint exist in the MCP spec as hints, not authorization guarantees. No Keycard-specific MCP annotation names or policy enforcement tied to those hints were found.
Commercial status and geography
Pricing page (as of 2026-10-30): Starter tier at 5,000 transactions/month (hard cap); Team at $500/month for 100,000 transactions plus $1 per 1,000 overage; Enterprise with custom terms. Enterprise supports dedicated, BYOC/on-prem deployments, private networking, and customer-managed KMS. Billing counts transactions differently for protected resources vs. brokered resource access.
Product launch posts (Coding Agents and Multi-Agent Apps) labeled Early Access with date-bound status; no definitive present GA/signup status established.
India-specific hosting, data residency, and in-country availability are not found/unverified. BYOC/on-prem is documented for Enterprise but India suitability remains unverified.
Secondary sources (e.g., WorkOS comparison) cite undisclosed pricing, which is contradicted by the current official pricing page.
Documentation and repository notes
Official docs cover usage, security architecture (tokens stored in secure database), audit logs and sessions (revocation behavior), and MCP server guides.
GitHub presence shows no public releases for the Go SDK and no explicit SECURITY.md on the connected repo; this is a repository-evidence caveat rather than proof of absence of security processes elsewhere.
Gaps and caveats to verify
Current GA/self-service signup eligibility and general availability remain unverified; several 2026 launch posts are date-bound.
India-specific hosting, data residency, and local sales/availability require verification.
No Keycard-specific MCP tool-annotation names or evidence of policy enforcement based on MCP ToolAnnotations found; MCP hints are not confirmed as access controls.
Exact retention/location of authorization event data and whether payloads are logged are not found in reviewed sources.
Legal contracting entity details were not confirmed from official pages.
Uncertainty notes
MCP specification cited is dated 2025-11-25 and older than six months relative to the context date; protocol-sensitive implementation details should be cross-checked against the latest MCP spec.



### Sources
<!-- paste the sources table below this line -->
"sources": [
    {
      "url": "https://github.com/github/github-mcp-server/blob/main/README.md",
      "date_or_version": "Mutable `main`; checked 2026-10-30",
      "source_type": "Primary — official GitHub repository README",
      "quote_under_25_words": "The remote GitHub MCP Server is hosted by GitHub and provides the easiest method for getting up and running.",
      "supports": "Official status, hosted remote service, endpoint/client configuration, exact tool catalog and tool descriptions.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://api.github.com/repos/github/github-mcp-server/releases/tags/v1.12.2",
      "date_or_version": "v1.12.2; published 2026-09-16",
      "source_type": "Primary — official GitHub Releases API",
      "quote_under_25_words": "\"published_at\": \"2026-09-16T10:58:24Z\"",
      "supports": "Version and published date of the latest release observed in the official releases page at research time.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://github.com/github/github-mcp-server/blob/main/docs/server-configuration.md",
      "date_or_version": "Mutable `main`; checked 2026-10-30",
      "source_type": "Primary — official GitHub repository documentation",
      "quote_under_25_words": "The server uses the default toolsets: context, issues, pull_requests, repos, users.",
      "supports": "Default toolsets, remote HTTP endpoint configuration, tool selection, read-only and scope-filter behavior.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://modelcontextprotocol.io/specification/2026-07-28/basic/transports",
      "date_or_version": "MCP specification 2026-07-28",
      "source_type": "Primary — official MCP specification",
      "quote_under_25_words": "each message is an HTTP POST to a single MCP endpoint",
      "supports": "Current Streamable HTTP message transport semantics.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization",
      "date_or_version": "MCP specification 2026-07-28",
      "source_type": "Primary — official MCP specification",
      "quote_under_25_words": "MCP client MUST obtain a client ID through one of three registration mechanisms",
      "supports": "OAuth client registration requirement; spec also says refresh-token issuance cannot be assumed.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://modelcontextprotocol.io/specification/2026-07-28/schema",
      "date_or_version": "MCP schema 2026-07-28",
      "source_type": "Primary — official MCP schema reference",
      "quote_under_25_words": "readOnlyHint?: boolean; destructiveHint?: boolean; idempotentHint?: boolean; openWorldHint?: boolean;",
      "supports": "Exact standard annotation field names and defaults; properties are advisory hints.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://docs.github.com/en/copilot/how-tos/copilot-in-your-ide/customize-copilot/extend-copilot-with-tools-and-context/set-up-the-github-mcp-server",
      "date_or_version": "Official docs; checked 2026-10-30; version-sensitive setup page",
      "source_type": "Primary — GitHub product documentation",
      "quote_under_25_words": "The GitHub MCP server is available to all GitHub users regardless of plan type.",
      "supports": "Plan availability, OAuth/PAT setup, host and enterprise policies, and tool licensing caveat.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://github.com/github/github-mcp-server/blob/main/docs/oauth-login.md",
      "date_or_version": "Mutable `main`; checked 2026-10-30",
      "source_type": "Primary — official GitHub repository documentation",
      "quote_under_25_words": "OAuth login applies to the stdio server only.",
      "supports": "Device-code/headless fallback is documented for local stdio; local non-interactive guidance points to GitHub App auth.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens",
      "date_or_version": "Official docs; checked 2026-10-30",
      "source_type": "Primary — GitHub product documentation",
      "quote_under_25_words": "For long-lived integrations, you should use a GitHub App.",
      "supports": "PAT is user-bound; fine-grained PAT owner/repository/permission setup and GitHub App recommendation.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://docs.github.com/en/rest/authentication/permissions-required-for-fine-grained-personal-access-tokens",
      "date_or_version": "Official docs; checked 2026-10-30",
      "source_type": "Primary — GitHub REST API documentation",
      "quote_under_25_words": "You will receive the X-Accepted-GitHub-Permissions header.",
      "supports": "Endpoint-level permission discovery for fine-grained PATs; no blanket tool-to-token mapping inferred.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://github.com/github/github-mcp-server/issues/3281",
      "date_or_version": "Issue filed 2026-09-15; describes v1.12.1",
      "source_type": "Primary — GitHub repository issue (reported implementation behavior) ",
      "quote_under_25_words": "Some clearly non-destructive/additive GitHub MCP tools set ReadOnlyHint: false but omit DestructiveHint: false.",
      "supports": "Reported annotation omissions for additive writes and resulting confirmation friction; not proof of current v1.12.2 behavior.",
      "status": "REPORTED"
    },
    {
      "url": "https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api",
      "date_or_version": "Official docs; checked 2026-10-30; limits can change",
      "source_type": "Primary — GitHub REST API documentation",
      "quote_under_25_words": "All of these requests count towards your personal rate limit of 5,000 requests per hour.",
      "supports": "REST API primary rate limits, including PAT/OAuth authenticated user baseline; separate from any unannounced MCP quota.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://docs.github.com/en/copilot/get-started/plans",
      "date_or_version": "Official plan page; checked 2026-10-30; highly version-sensitive",
      "source_type": "Primary — GitHub Copilot plan documentation",
      "quote_under_25_words": "Copilot Student: Available to verified students. Get access to Copilot's features for free.",
      "supports": "Copilot Student price/eligibility and MCP plan matrix; AI-credit allowances and plan features vary by tier.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://docs.github.com/en/copilot/concepts/billing-and-usage/individuals/usage-limits",
      "date_or_version": "Official docs; checked 2026-10-30; version-sensitive usage policies",
      "source_type": "Primary — GitHub Copilot billing documentation",
      "quote_under_25_words": "Your Copilot plan includes an allowance of AI credits.",
      "supports": "Student/Free access is not an unlimited Copilot usage guarantee; usage/rate limits apply.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://docs.github.com/en/education/about-github-education/github-education-for-students/apply-to-github-education-as-a-student",
      "date_or_version": "Official docs; checked 2026-10-30",
      "source_type": "Primary — GitHub Education documentation",
      "quote_under_25_words": "Navigate to your Education benefits settings. Under GitHub Education, click Start an application.",
      "supports": "Student verification application steps and eligibility; no approval-time guarantee stated.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://github.com/github/github-mcp-server/security/advisories",
      "date_or_version": "Advisory list checked 2026-10-30; entries dated 2026-06-09 and 2026-07-20",
      "source_type": "Primary — official GitHub repository security advisories",
      "quote_under_25_words": "Nil Pointer Dereference DoS in completion/complete Handler — GHSA-w4q6-qw23-4rg7 — High.",
      "supports": "Repository advisories visible as of review; list does not itself resolve current hosted-service version applicability.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://github.com/advisories/GHSA-w4q6-qw23-4rg7",
      "date_or_version": "Advisory filed 2026-04-06; affected/fixed version not verified from extracted page",
      "source_type": "Primary — GitHub Security Advisory",
      "quote_under_25_words": "This allows any unauthenticated client to cause a complete denial of service.",
      "supports": "Reported vulnerability impact for the local/server implementation; current hosted endpoint exposure and fixed versions remain unverified.",
      "status": "REPORTED"
    },
    {
      "url": "https://github.com/advisories/GHSA-pjp5-fpmr-3349",
      "date_or_version": "Listed 2026-06-09; affected/fixed version not verified from extracted page",
      "source_type": "Primary — GitHub Security Advisory",
      "quote_under_25_words": "Lockdown mode singleton in HTTP server causes cross-user GraphQL client confusion.",
      "supports": "Reported multi-user HTTP lockdown-mode issue; does not establish exposure in GitHub's current hosted service.",
      "status": "REPORTED"
    }
  ],

"sources": [
    {
      "url": "https://developers.google.com/workspace/gmail/api/guides/configure-mcp-server",
      "date_or_version": "Accessed 2026-10-30; page update date not displayed",
      "source_type": "Official Google product setup documentation",
      "quote_under_25_words": "The following tools are available for the Gmail MCP server",
      "supports": "Gmail first-party ownership, prerequisite preview enrollment, URL, OAuth scopes/client setup, Streamable HTTP, and tool list.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://developers.google.com/workspace/calendar/api/guides/configure-mcp-server",
      "date_or_version": "2026-10-12 per search result; accessed 2026-10-30",
      "source_type": "Official Google Calendar API setup documentation",
      "quote_under_25_words": "The Google Calendar MCP server provides a standardized way for AI agents to",
      "supports": "Calendar setup, preview prerequisite, global URL/transport/OAuth, scopes, tool inventory and client requirements.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://developers.google.com/drive/api/guides/configure-mcp-server",
      "date_or_version": "2026-10-12 per search result; accessed 2026-10-30",
      "source_type": "Official Google Drive API setup documentation",
      "quote_under_25_words": "Membership in the Google Workspace Developer Preview Program.",
      "supports": "Drive preview prerequisite, API enablement, OAuth configuration/scopes, remote URL, and guide-listed tools.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://developers.google.com/workspace/docs/api/guides/configure-mcp-server",
      "date_or_version": "2026-10-12 per search result; accessed 2026-10-30",
      "source_type": "Official Google Docs API setup documentation",
      "quote_under_25_words": "The following tools are available for the Google Docs MCP server",
      "supports": "Docs preview prerequisite, scopes, endpoint/transport and documented read_doc/update_doc tools.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://developers.google.com/workspace/sheets/api/guides/configure-mcp-server",
      "date_or_version": "2026-10-12 per search result; accessed 2026-10-30",
      "source_type": "Official Google Sheets API setup documentation",
      "quote_under_25_words": "The following tools are available for the Google Sheets MCP server",
      "supports": "Sheets preview prerequisite, scope set, URL/transport and listed tools.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://developers.google.com/workspace/preview",
      "date_or_version": "Accessed 2026-10-30; latest-features list current on page",
      "source_type": "Official Google Workspace Developer Preview Program documentation",
      "quote_under_25_words": "MCP SERVERS Gmail MCP server Documentation Send feedback Calendar MCP server",
      "supports": "The current preview feature list includes the five Workspace MCP services; enrollment requirements, expected feature lifecycle, program terms and service-account FAQ caveat.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://docs.cloud.google.com/mcp/release-notes",
      "date_or_version": "2026-09-14 MCP protocol update; GA note 2026-05-01; accessed 2026-10-30",
      "source_type": "Official Google Cloud MCP release notes",
      "quote_under_25_words": "Individual MCP servers might be in Preview or GA",
      "supports": "Platform GA does not establish each Workspace MCP service is GA; MCP protocol 2026-07-28 support; client-auth timeline and region-rollout note.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://developers.google.com/workspace/gmail/api/auth/scopes",
      "date_or_version": "2026-09-10 per search result; accessed 2026-10-30",
      "source_type": "Official Google Gmail API OAuth scope documentation",
      "quote_under_25_words": "https://www.googleapis.com/auth/gmail.readonly — View your email messages and settings.",
      "supports": "Gmail read and compose scopes are classified Restricted; verification and security-assessment consequences.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://developers.google.com/drive/api/guides/api-specific-auth",
      "date_or_version": "Accessed 2026-10-30; page date not displayed",
      "source_type": "Official Google Drive API OAuth scope documentation",
      "quote_under_25_words": "https://www.googleapis.com/auth/drive.file — Create new Drive files, or modify existing files",
      "supports": "Drive scope classifications: drive.file non-sensitive, drive.readonly restricted; explain narrow per-file access and review burden.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://developers.google.com/workspace/docs/api/auth",
      "date_or_version": "2026-09-03 per search result; accessed 2026-10-30",
      "source_type": "Official Google Docs API OAuth scope documentation",
      "quote_under_25_words": "documents.readonly — See all your Google Docs documents. Sensitive",
      "supports": "Docs scope classification and verification requirements for sensitive and restricted scopes.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://developers.google.com/workspace/sheets/api/scopes",
      "date_or_version": "2026-09-03 per search result; accessed 2026-10-30",
      "source_type": "Official Google Sheets API OAuth scope documentation",
      "quote_under_25_words": "spreadsheets.readonly — See all your Google Sheets spreadsheets. Sensitive",
      "supports": "Sheets scope classification and note that Sheets scopes apply to the whole spreadsheet file, not individual tabs.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://developers.google.com/workspace/sheets/api/reference/mcp",
      "date_or_version": "2026-10-09 per search result; accessed 2026-10-30",
      "source_type": "Official Google Sheets MCP tool reference",
      "quote_under_25_words": "update_spreadsheet — Applies one or more updates to the spreadsheet.",
      "supports": "Sheets tools and mutating/deleting operation types; reference surface is more extensive than basic guide list; advises tools/list for current schema.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://developers.google.com/identity/protocols/oauth2",
      "date_or_version": "Accessed 2026-10-30; page date not displayed",
      "source_type": "Official Google OAuth 2.0 documentation",
      "quote_under_25_words": "A Google Cloud Platform project with an OAuth consent screen configured for an external user type and a publishing status of ‘Testing’ is issued a refresh token expiring in 7 days",
      "supports": "Testing-mode 7-day refresh-token limitation and Google OAuth token rules.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://support.google.com/cloud/answer/15549945?hl=en",
      "date_or_version": "Accessed 2026-10-30; current Google Cloud Help page, no version displayed",
      "source_type": "Official Google OAuth audience/testing policy help",
      "quote_under_25_words": "100 new users in total, after the app presents the unverified app screen",
      "supports": "Lifetime OAuth user cap for unapproved sensitive/restricted scopes in relevant unverified-app case; audience/testing distinction.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://developers.google.com/workspace/gmail/api/reference/mcp/tools_list/create_draft",
      "date_or_version": "2026-07-21 per search result; accessed 2026-10-30",
      "source_type": "Official Gmail MCP individual tool reference",
      "quote_under_25_words": "Creates a new draft email in the authenticated user's Gmail account.",
      "supports": "Draft-not-send effect, exact `create_draft` annotations and accepted OAuth scopes.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://developers.google.com/drive/api/reference/mcp/tools_list/create_file",
      "date_or_version": "Accessed 2026-10-30; page date not displayed",
      "source_type": "Official Drive MCP individual tool reference",
      "quote_under_25_words": "Call this tool to create or upload a File to Google Drive.",
      "supports": "Drive create/upload behavior, native file types, exact `create_file` annotations and scopes.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://developers.google.com/workspace/docs/api/reference/mcp/tools_list/update_doc",
      "date_or_version": "2026-10-01 per search result; accessed 2026-10-30",
      "source_type": "Official Google Docs MCP individual tool reference",
      "quote_under_25_words": "EDIT Changes are applied directly to the document.",
      "supports": "Docs update can edit directly; documents batch updates and exact tool annotation values.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://developers.google.com/workspace/sheets/api/reference/mcp/tools_list/get_values",
      "date_or_version": "Accessed 2026-10-30; page date not displayed",
      "source_type": "Official Google Sheets MCP individual tool reference",
      "quote_under_25_words": "Read Only Hint: ✅ | Open World Hint: ✅",
      "supports": "Exact documented annotations for `get_values`; does not justify extrapolation to other Sheets tools.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://developers.google.com/workspace/calendar/api/v3/reference/mcp/tools_list/create_event",
      "date_or_version": "2026-07-17 per search result; accessed 2026-10-30",
      "source_type": "Official Calendar MCP individual tool reference",
      "quote_under_25_words": "Creates an event on the given calendar.",
      "supports": "Calendar event creation, attendee/notification fields, conflicting broader write scopes, and exact tool annotations.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://developers.google.com/workspace/gmail/api/reference/quota",
      "date_or_version": "2026-10-16 per search result; accessed 2026-10-30",
      "source_type": "Official Google Gmail API and MCP quota/pricing documentation",
      "quote_under_25_words": "Per minute per project 1,200,000 quota units",
      "supports": "Gmail quota limits, daily threshold, per-method unit costs, no-additional-cost standard use and planned later-2026 overage billing.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://developers.google.com/workspace/calendar/api/guides/quota",
      "date_or_version": "Accessed 2026-10-30; page date not displayed",
      "source_type": "Official Google Calendar API and MCP quota/pricing documentation",
      "quote_under_25_words": "Per minute per project 10,000 requests",
      "supports": "Calendar per-project/user and daily thresholds, rate limiting and planned overage charges.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://developers.google.com/drive/api/guides/limits",
      "date_or_version": "Accessed 2026-10-30; page date not displayed",
      "source_type": "Official Google Drive API and MCP quota/pricing documentation",
      "quote_under_25_words": "Per minute per user per project 325,000 quota units",
      "supports": "Drive standard quotas, daily thresholds, egress limit and no-additional-cost/planned-overage language.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://developers.google.com/workspace/docs/api/limits",
      "date_or_version": "2026-09-03 per search result; accessed 2026-10-30",
      "source_type": "Official Google Docs API and MCP quota/pricing documentation",
      "quote_under_25_words": "The Docs MCP server uses read and write request metrics.",
      "supports": "Docs tool read/write quota accounting and pricing; search index provides project read/write quota values, while numeric MCP table cells did not render in extraction.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://developers.google.com/workspace/sheets/api/limits",
      "date_or_version": "2026-09-03 per search result; accessed 2026-10-30",
      "source_type": "Official Google Sheets API and MCP quota/pricing documentation",
      "quote_under_25_words": "get_values — 1 read request",
      "supports": "Sheets per-tool read/write cost and pricing; project limits are in official quota page/index; extraction did not expose all user-level numeric cells.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://developers.google.com/workspace/guides/configure-mcp-servers",
      "date_or_version": "Accessed 2026-10-30; page update date not displayed",
      "source_type": "Official Google Workspace MCP client configuration guide",
      "quote_under_25_words": "The remote MCP servers are ready to use in Antigravity.",
      "supports": "Per-product server URLs, Streamable HTTP, OAuth 2.0, Antigravity/Claude configuration, Claude plan requirements and `access_type=offline` caveat.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://github.com/taylorwilsdon/google_workspace_mcp",
      "date_or_version": "Community repository README accessed 2026-10-30; active project; see release page v1.4.8",
      "source_type": "Community GitHub repository (not a Google-maintained server)",
      "quote_under_25_words": "Supports all free Google accounts & Google Workspace plans",
      "supports": "Self-reported community service coverage, account support, local stdio/remote HTTP OAuth 2.1 modes, and deployment claims; not independently verified.",
      "status": "REPORTED"
    },
    {
      "url": "https://github.com/taylorwilsdon/google_workspace_mcp/releases",
      "date_or_version": "Latest release shown v1.4.8; search page date 2026-10-27",
      "source_type": "Community GitHub releases",
      "quote_under_25_words": "Release v1.4.8",
      "supports": "Community project is actively released and has recent OAuth compatibility/security-related changes; current feature claims remain project-reported.",
      "status": "REPORTED"
    },
    {
      "url": "https://github.com/googleworkspace/cli",
      "date_or_version": "Accessed 2026-10-30; active-development README, version-sensitive",
      "source_type": "Google Workspace GitHub repository README; explicit support disclaimer",
      "quote_under_25_words": "This is not an officially supported Google product.",
      "supports": "Counter-evidence against treating Google’s own CLI repository as a supported official MCP server; repo describes a dynamic CLI, not the five dedicated remote MCP services.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://modelcontextprotocol.io/specification/2026-07-28/server/tools",
      "date_or_version": "MCP specification 2026-07-28; Google release notes say supported from 2026-09-14",
      "source_type": "Primary MCP protocol specification",
      "quote_under_25_words": "annotations: Optional properties describing tool behavior",
      "supports": "MCP annotations are optional; protocol key set/semantics should not be mistaken for actual server-declared values.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://github.com/github/copilot-cli/issues/4606",
      "date_or_version": "Issue opened 2026-08-25; affected Copilot CLI 1.0.81-10",
      "source_type": "Third-party client GitHub issue; user-reported",
      "quote_under_25_words": "Native HTTP MCP authentication fails for Google's official Workspace MCP endpoints",
      "supports": "Reported OAuth discovery/issuer mismatch on that specific client version; issue states workaround/proxy succeeded, not a Google endpoint outage.",
      "status": "REPORTED"
    }
  ],

"sources": [
    {
      "url": "https://docs.slack.dev/ai/slack-mcp-server",
      "date_or_version": "Undated; accessed 2026-10-30; version-sensitive",
      "source_type": "Official Slack Developer Docs — technical reference",
      "quote_under_25_words": "We do not support SSE-based connections or Dynamic Client Registration at this time.",
      "supports": "Hosted Slack MCP endpoint, Streamable HTTP/JSON-RPC, unsupported SSE and DCR, app identity/distribution, tool capabilities, scope map, rate tiers and IP allowlist.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://docs.slack.dev/ai/slack-mcp-server/connect-to-harnesses",
      "date_or_version": "Undated; accessed 2026-10-30; version-sensitive",
      "source_type": "Official Slack Developer Docs — setup guide",
      "quote_under_25_words": "codex mcp add --transport http slack https://mcp.slack.com/mcp",
      "supports": "Single remote connector setup; OAuth login; app client ID; admin approval; only Marketplace/internal apps; examples for Codex, Claude Code and Pi.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://docs.slack.dev/changelog/2026/05/13/new-mcp-tools",
      "date_or_version": "2026-05-13 (older than six months as of 2026-10-30)",
      "source_type": "Official Slack Developer Changelog",
      "quote_under_25_words": "We've added the following tools to the Slack MCP server:",
      "supports": "Dated additions: reactions, channel/conversation creation, member listing, emoji listing, file reading.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://slack.com/help/articles/115004846068-Slack-updates-and-changes",
      "date_or_version": "August 2026 section; accessed 2026-10-30",
      "source_type": "Official Slack Help Center — product updates",
      "quote_under_25_words": "Org Owners and Org Admins can manage access to individual MCP server tools",
      "supports": "Org-level per-tool access controls and defaults for new MCP tools; source also notes file/list management but does not enumerate deletion tools.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://modelcontextprotocol.io/specification/2026-07-28/schema",
      "date_or_version": "MCP specification 2026-07-28",
      "source_type": "Primary MCP protocol schema specification",
      "quote_under_25_words": "readOnlyHint?: boolean; destructiveHint?: boolean; idempotentHint?: boolean; openWorldHint?: boolean;",
      "supports": "Exact protocol annotation field names and warning that annotations are hints, not guaranteed tool behavior; does not document Slack's values.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization",
      "date_or_version": "MCP specification 2026-07-28",
      "source_type": "Primary MCP protocol authorization specification",
      "quote_under_25_words": "MUST NOT assume refresh tokens will be issued; the AS retains discretion",
      "supports": "OAuth client registration options, protected-resource discovery, DCR status in MCP protocol, refresh-token caveat and confidentiality requirements.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://docs.slack.dev/reference/methods/oauth.v2.user.access",
      "date_or_version": "Undated; accessed 2026-10-30",
      "source_type": "Official Slack API method reference",
      "quote_under_25_words": "This method is used to initiate the OAuth flow using just user scopes (no bot scopes)",
      "supports": "User-token OAuth, PKCE code_verifier, desktop MCP use case, refresh-token request parameter, and admin-approval errors.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://docs.slack.dev/authentication/using-token-rotation",
      "date_or_version": "Undated; accessed 2026-10-30; version-sensitive",
      "source_type": "Official Slack Developer Docs — authentication guide",
      "quote_under_25_words": "With token rotation, it expires every 12 hours.",
      "supports": "Rotatable user tokens, one-use refresh token replacement, 12-hour lifetime, secure token persistence and timely background refresh.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://slack.com/blog/news/slackbot-mcp-security",
      "date_or_version": "Undated; accessed 2026-10-30; version-sensitive",
      "source_type": "Official Slack corporate security blog",
      "quote_under_25_words": "The Slackbot MCP Client uses remote HTTP/SSE transport only.",
      "supports": "Separate Slackbot-as-MCP-client architecture, remote external servers, user OAuth, admin gates, confirmation model; not the Slack MCP server transport.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://slack.com/pricing",
      "date_or_version": "Undated; accessed 2026-10-30; rolling plan page",
      "source_type": "Official Slack pricing page",
      "quote_under_25_words": "Slack Free and Pro users will have the chance to explore Slackbot’s capabilities firsthand through a limited trial experience.",
      "supports": "Slackbot trial language and ongoing paid-tier availability; does not state a plan prerequisite for third-party clients using Slack MCP server.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://slack.com/help/articles/115003205446-Slack-plans-and-features",
      "date_or_version": "Undated; accessed 2026-10-30; version-sensitive",
      "source_type": "Official Slack Help Center — plan matrix",
      "quote_under_25_words": "Slackbot ✓ ✓",
      "supports": "Plan comparison places Slackbot on paid tiers, which should be read alongside the pricing page's planned limited Free/Pro trial.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://slack.com/help/articles/360035633934-Data-residency-for-Slack",
      "date_or_version": "Undated; accessed 2026-10-30; version-sensitive",
      "source_type": "Official Slack Help Center — data residency",
      "quote_under_25_words": "Mumbai, India",
      "supports": "India data-residency region, Hyderabad backup region, paid-plan requirement and caveat that residency only covers selected data at rest.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://docs.slack.dev/changelog/2026/02/17/slack-mcp",
      "date_or_version": "2026-02-17 (older than six months as of 2026-10-30)",
      "source_type": "Official Slack Developer Changelog — launch announcement",
      "quote_under_25_words": "The MCP server enables AI agents to interact with Slack content through tools",
      "supports": "Dated first-party announcement of Slack MCP server and search-scope changes; flags older launch context as potentially stale.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://github.com/slack-samples/bolt-js-slack-mcp-server",
      "date_or_version": "Repository page accessed 2026-10-30; release/commit version not established",
      "source_type": "Official Slack samples GitHub repository",
      "quote_under_25_words": "This functionality is being tested and may change before general availability.",
      "supports": "Sample app's beta warning, user-token use, individual installations, and example app/client workflow; not proof of production compatibility.",
      "status": "REPORTED"
    },
    {
      "url": "https://mcp.slack.com/mcp",
      "date_or_version": "Live unauthenticated POST observed 2026-10-30",
      "source_type": "Primary Slack MCP endpoint — direct response",
      "quote_under_25_words": "missing_token",
      "supports": "Unauthenticated endpoint rejected initialize with HTTP 401; could not inspect authenticated tools/list or verify exact wire-level tool IDs.",
      "status": "REPORTED"
    },
    {
      "url": "https://modelcontextprotocol.io/specification/2026-07-28/basic/transports",
      "date_or_version": "MCP specification 2026-07-28",
      "source_type": "Primary MCP protocol transport specification",
      "quote_under_25_words": "each message is an HTTP POST to a single MCP endpoint",
      "supports": "Current Streamable HTTP transport mechanics, distinguishing the MCP protocol's transport model from Slackbot's separate client support.",
      "status": "DOCUMENTED"
    }
  ],

"sources": [
    {
      "url": "https://learn.microsoft.com/en-us/microsoft-agent-365/tooling-servers-overview",
      "date_or_version": "2026-10-12",
      "source_type": "Official Microsoft Learn; primary vendor documentation",
      "quote_under_25_words": "Application-specific Microsoft 365 MCP tools ... are only intended for backward compatibility purposes",
      "supports": "Separates Work IQ from legacy hosted Mail/Teams/SharePoint/OneDrive tools; warns tools registry availability varies by tenant, region, rollout, licensing, admin approval and policy; recommends Work IQ for new projects.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://learn.microsoft.com/en-us/microsoft-365/copilot/extensibility/work-iq/mcp/overview",
      "date_or_version": "2026-10-13 (search-index date; live page checked 2026-10-30)",
      "source_type": "Official Microsoft Learn; primary vendor documentation",
      "quote_under_25_words": "The Work IQ MCP server ... through a single MCP endpoint",
      "supports": "Work IQ MCP product overview, generic categories/tools, workload paths, Entra auth discovery, and mutation model overview.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://learn.microsoft.com/en-us/microsoft-365/copilot/extensibility/work-iq/api-overview",
      "date_or_version": "2026-08-21 (search-index date; live page checked 2026-10-30)",
      "source_type": "Official Microsoft Learn; primary vendor documentation",
      "quote_under_25_words": "Application-only authentication isn't supported.",
      "supports": "Protocols (A2A, local/remote MCP, REST), workload coverage, delegated auth/OBO, no app-only, public endpoint family, Copilot Credit usage billing.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://learn.microsoft.com/en-us/microsoft-365/copilot/extensibility/work-iq/mcp/quickstart/github-copilot-cli",
      "date_or_version": "2026-09-25 (search-index date; live page checked 2026-10-30)",
      "source_type": "Official Microsoft Learn; primary vendor documentation",
      "quote_under_25_words": "https://workiq.svc.cloud.microsoft/mcp",
      "supports": "Remote Work IQ endpoint and Copilot CLI plugin setup, Entra sign-in, user permission and policy dependencies.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://github.com/microsoft/work-iq",
      "date_or_version": "Repository README; version/release not stated in extracted page; checked 2026-10-30",
      "source_type": "Microsoft-owned GitHub repository; primary project documentation",
      "quote_under_25_words": "Start the MCP server: workiq mcp",
      "supports": "Official Microsoft Work IQ CLI; local stdio launch and package install; repo declares public preview and admin consent requirement.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://learn.microsoft.com/en-us/microsoft-365/copilot/extensibility/work-iq/permissions",
      "date_or_version": "2026-06-17 (search-index date; live page checked 2026-10-30)",
      "source_type": "Official Microsoft Learn; primary vendor documentation",
      "quote_under_25_words": "An organization administrator must enable Work IQ in your organization",
      "supports": "Current Work IQ API app URI and delegated WorkIQAgent.Ask scope; organization-level enablement and consent requirement.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://learn.microsoft.com/en-us/microsoft-365/copilot/extensibility/work-iq/mcp/policy-governance-mcp",
      "date_or_version": "2026-06-17 (search-index date; live page checked 2026-10-30)",
      "source_type": "Official Microsoft Learn; primary vendor documentation",
      "quote_under_25_words": "By default, mutation operations aren't allowed for safety.",
      "supports": "Tenant policy/admin UI, default deny for mutations, policy scope and delay, authorization layers.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/tools/work-iq",
      "date_or_version": "2026-09-29 (search-index date; live page checked 2026-10-30); preview warnings apply to Foundry integration",
      "source_type": "Official Microsoft Learn; primary vendor documentation",
      "quote_under_25_words": "Authentication uses On-Behalf-Of (OBO) so the request runs in the context of the signed-in user.",
      "supports": "Foundry setup prerequisites, tenant Global Admin consent for WorkIQAgent.Ask, API billing versus connector licensing, user context and boundary warning.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://learn.microsoft.com/en-us/microsoft-365/copilot/extensibility/work-iq/mcp/tool-reference",
      "date_or_version": "2026-10-13 (search-index date; live page checked 2026-10-30)",
      "source_type": "Official Microsoft Learn; primary vendor documentation",
      "quote_under_25_words": "A separate tenant policy layer evaluates each tool request and blocks mutation operations by default.",
      "supports": "Exact generic tools and their read/create/update/delete/action/function/search/schema behaviors, result limits, paths, and published list_agent/list_agents discrepancy.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://modelcontextprotocol.io/specification/2026-07-28/schema",
      "date_or_version": "MCP protocol specification 2026-07-28",
      "source_type": "Official Model Context Protocol specification; primary protocol source",
      "quote_under_25_words": "readOnlyHint?: boolean; destructiveHint?: boolean; idempotentHint?: boolean; openWorldHint?: boolean;",
      "supports": "Exact protocol annotation names and their optional/hint semantics; does not establish which values Work IQ actually emits.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://modelcontextprotocol.io/specification/2026-07-28/server/tools",
      "date_or_version": "MCP protocol specification 2026-07-28",
      "source_type": "Official Model Context Protocol specification; primary protocol source",
      "quote_under_25_words": "Clients send a tools/list request",
      "supports": "MCP tool discovery/call methods and optional behavior annotations; supports use of live discovery rather than assuming a static tool list.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://www.microsoft.com/en-us/licensing/news/work-iq-general-availability",
      "date_or_version": "2026-06-02 announcement; states GA on June 16, 2026",
      "source_type": "Official Microsoft licensing news; primary vendor source",
      "quote_under_25_words": "There is no separate Work IQ API subscription, SKU, or per-user license.",
      "supports": "Consumption billing through Copilot Credits, variable query usage, static Work IQ Tool API usage at 0.1 credits per API call; illustrative prices/scenarios.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://github.com/microsoft/work-iq/blob/main/ADMIN-INSTRUCTIONS.md",
      "date_or_version": "Document says v1.4, last updated March 2026; older than six months as of 2026-10-30",
      "source_type": "Microsoft-owned GitHub repository; primary project doc but stale/version-sensitive",
      "quote_under_25_words": "Microsoft 365 Copilot license for each user who will use Work IQ",
      "supports": "Older CLI/admin guide lists seven Graph delegated scopes and per-user Copilot license. Conflicts in scope/path with current Work IQ API docs; counter-evidence only, not relied on as current API policy.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://learn.microsoft.com/en-us/microsoft-365/enterprise/m365-dr-service-copilot-offerings?view=o365-worldwide",
      "date_or_version": "2026-10-08 (search-index date; live page checked 2026-10-30)",
      "source_type": "Official Microsoft Learn; primary vendor documentation",
      "quote_under_25_words": "Tenant has a sign-up country/region included in ... India",
      "supports": "India appears in specified Microsoft 365 Copilot Chat tenant country conditions and page documents applicable Copilot data residency arrangements; not Work IQ-specific.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://learn.microsoft.com/en-us/microsoft-copilot-studio/mcp-mail-tools",
      "date_or_version": "Preview reference; page date not exposed; checked 2026-10-30",
      "source_type": "Official Microsoft Learn; primary vendor documentation",
      "quote_under_25_words": "only intended for backward compatibility purposes",
      "supports": "Legacy Microsoft Mail server ID and documented mail operation effects; preview warning and backward compatibility status.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://learn.microsoft.com/en-us/microsoft-copilot-studio/mcp-teams-tools",
      "date_or_version": "Preview reference; page date not exposed; checked 2026-10-30",
      "source_type": "Official Microsoft Learn; primary vendor documentation",
      "quote_under_25_words": "Microsoft Teams tools to manage chats, channels, and users or messages within them.",
      "supports": "Legacy Teams server ID/scope and documented chat/channel/member/message operation effects, including sends/deletes.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://learn.microsoft.com/en-us/microsoft-copilot-studio/mcp-sharepoint-tools",
      "date_or_version": "Preview reference; page date not exposed; checked 2026-10-30",
      "source_type": "Official Microsoft Learn; primary vendor documentation",
      "quote_under_25_words": "File operations are limited to files that are 5 MB or less.",
      "supports": "Legacy SharePoint server ID and file/list/site/share operations; 5 MB restriction and sensitivity label capability.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://learn.microsoft.com/en-us/microsoft-copilot-studio/mcp-onedrive-tools",
      "date_or_version": "Preview reference; page date not exposed; checked 2026-10-30",
      "source_type": "Official Microsoft Learn; primary vendor documentation",
      "quote_under_25_words": "All file operations limited to ≤5MB.",
      "supports": "Legacy OneDrive server ID and documented read/write/share/label/move/copy effects; 5 MB limit.",
      "status": "DOCUMENTED"
    }
  ],

"sources": [
    {
      "url": "https://developer.atlassian.com/cloud/rovo-mcp/",
      "date_or_version": "Last updated Sep 2, 2026",
      "source_type": "Official Atlassian developer documentation",
      "quote_under_25_words": "The Atlassian Rovo MCP Server is a cloud-hosted Model Context Protocol (MCP) server that connects AI-powered clients to your Atlassian Cloud apps.",
      "supports": "Cloud-hosted service and Atlassian Cloud product boundary; endpoint and permission model.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://support.atlassian.com/atlassian-ai-gateway/docs/get-started-with-the-atlassian-remote-mcp-server/",
      "date_or_version": "Not stated; accessed 2026-10-30",
      "source_type": "Official Atlassian Support documentation",
      "quote_under_25_words": "https://mcp.atlassian.com/v2/mcp",
      "supports": "Canonical v2 endpoint, client setup examples, OAuth as default and optional API-token authentication.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://developer.atlassian.com/cloud/rovo-mcp/guides/supported-tools/",
      "date_or_version": "Last updated Oct 27, 2026; MCP v2",
      "source_type": "Official Atlassian developer documentation",
      "quote_under_25_words": "Deferred tools are found at runtime through the discover tool, which takes a natural-language description of what you want to do.",
      "supports": "Exact Jira/Confluence tool identifiers, group scopes, Primary/deferred exposure, destructive/manage defaults, high-impact actions, explicit commit behavior.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://developer.atlassian.com/cloud/rovo-mcp/guides/configuring-authentication-via-api-token",
      "date_or_version": "Last updated Sep 2, 2026",
      "source_type": "Official Atlassian developer documentation",
      "quote_under_25_words": "Use this option for non-interactive or machine-to-machine scenarios.",
      "supports": "Headless viability, personal-token Basic and service-account Bearer methods, required scopes, admin enablement, limitations, v2 setup.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://support.atlassian.com/atlassian-ai-gateway/docs/configure-oauth-2-1/",
      "date_or_version": "Not stated; accessed 2026-10-30",
      "source_type": "Official Atlassian Support documentation",
      "quote_under_25_words": "With OAuth 2.1, access tokens are typically consented for a specific cloud ID (site).",
      "supports": "Interactive user consent, site/cloudId scope and existing app permissions.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://support.atlassian.com/rovo/docs/rovo-usage-limits/",
      "date_or_version": "Living documentation; pricing applies to usage/forecasts starting Aug 31, 2026; extra billing starts Dec 3, 2026",
      "source_type": "Official Atlassian Support documentation",
      "quote_under_25_words": "Rovo credits are Atlassian's unit of measurement for usage of AI capabilities and access to enriched context via the Teamwork Graph (TWG).",
      "supports": "Included plan allowances, credit pooling/consumption, current metering distinctions, overage timing and price.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://developer.atlassian.com/cloud/jira/platform/rate-limiting/",
      "date_or_version": "Last updated Oct 23, 2026",
      "source_type": "Official Atlassian developer documentation",
      "quote_under_25_words": "API token-based traffic is not affected by this change, and will continue to be governed by existing burst rate limits.",
      "supports": "Jira REST rate-limit changes; distinction from an undocumented Atlassian MCP request quota.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://raw.githubusercontent.com/modelcontextprotocol/modelcontextprotocol/main/schema/2026-07-28/schema.ts",
      "date_or_version": "MCP protocol schema 2026-07-28",
      "source_type": "Primary MCP GitHub schema",
      "quote_under_25_words": "readOnlyHint; destructiveHint; idempotentHint; openWorldHint",
      "supports": "Exact standardized optional MCP ToolAnnotations field names and their hint semantics; does not establish Atlassian’s per-tool values.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://modelcontextprotocol.io/specification/2026-07-28/basic/transports",
      "date_or_version": "MCP specification 2026-07-28",
      "source_type": "Primary MCP protocol specification",
      "quote_under_25_words": "Streamable HTTP: each message is an HTTP POST to a single MCP endpoint.",
      "supports": "Current protocol transport definition; Atlassian does not explicitly say this is its deployed variant.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://support.atlassian.com/security-and-access-policies/docs/understand-data-residency/",
      "date_or_version": "Not stated; accessed 2026-10-30",
      "source_type": "Official Atlassian Support documentation",
      "quote_under_25_words": "India consists of Asia Pacific (Mumbai) regions.",
      "supports": "India data-residency region and default Global hosting; not MCP-specific processing location.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://community.atlassian.com/forums/discussion/3264359/clarification-on-atlassian-rovo-mcp-server-rate-limits-10-000-calls-on-enterprise-plan",
      "date_or_version": "Community post July 19, 2026",
      "source_type": "Atlassian Community user discussion (secondary/user-generated)",
      "quote_under_25_words": "Enterprise customers can make 1,000 calls per hour plus an additional 20 calls per user, up to a maximum of 10,000 calls per hour.",
      "supports": "Reported hourly quota claim only; the post itself characterizes its interpretation as not guaranteed and current vendor docs reviewed do not corroborate it.",
      "status": "REPORTED"
    },
    {
      "url": "https://github.com/atlassian/atlassian-mcp-server/issues/283",
      "date_or_version": "Opened Oct 22, 2026; v2 report",
      "source_type": "GitHub issue in Atlassian's official repository; user-reported",
      "quote_under_25_words": "when the grant is stale, the resources endpoint still returns 200 but silently omits scopes",
      "supports": "A reported OAuth stale-grant symptom and reconnect workaround; not an Atlassian-confirmed incident or security advisory.",
      "status": "REPORTED"
    },
    {
      "url": "https://api.github.com/repos/atlassian/atlassian-mcp-server/releases",
      "date_or_version": "Checked Oct 30, 2026",
      "source_type": "GitHub REST API for official Atlassian repository releases",
      "quote_under_25_words": "[]",
      "supports": "No release entries returned by this API at retrieval; does not establish that no versioned docs/releases exist elsewhere.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://support.atlassian.com/security-and-access-policies/docs/understand-atlassian-mcp-server/",
      "date_or_version": "Not stated; accessed 2026-10-30",
      "source_type": "Official Atlassian Support security documentation",
      "quote_under_25_words": "IP allowlists also apply when users access Jira, Confluence, Compass, or Rovo through Atlassian MCP.",
      "supports": "Admin access controls, allowed domains, IP allowlists and permission inheritance.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://www.atlassian.com/blog/company-news/team26-europe-atlassian-mcp",
      "date_or_version": "Oct 6, 2026",
      "source_type": "Official Atlassian company blog",
      "quote_under_25_words": "Atlassian MCP now connects more Atlassian products to the AI clients you love to use.",
      "supports": "Current GA marketing context and fast-changing total tools claim; not a substitute for the dated supported-tools catalog.",
      "status": "DOCUMENTED"
    }
  ],

"sources": [
    {
      "url": "https://developers.notion.com/guides/mcp/overview",
      "date_or_version": "Undated live vendor documentation; accessed 2026-10-30",
      "source_type": "Primary vendor documentation",
      "quote_under_25_words": "Notion MCP is a remote MCP server hosted by Notion.",
      "supports": "Hosted-vs-local distinction and OAuth-authenticated Notion MCP overview.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://developers.notion.com/guides/mcp/get-started-with-mcp",
      "date_or_version": "Undated live vendor documentation; accessed 2026-10-30",
      "source_type": "Primary vendor documentation",
      "quote_under_25_words": "Streamable HTTP (recommended): https://mcp.notion.com/mcp; SSE fallback: https://mcp.notion.com/sse",
      "supports": "Official endpoints, preferred transport, OAuth client setup, bridge fallback, local-server caveat, and Devin organization-access option.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://developers.notion.com/guides/mcp/build-mcp-client",
      "date_or_version": "Undated live vendor documentation; accessed 2026-10-30",
      "source_type": "Primary vendor technical documentation",
      "quote_under_25_words": "OAuth 2.0 Authorization Code flow with PKCE",
      "supports": "Client requirements for OAuth/PKCE, remote transports, token refresh, secure storage, and dynamic registration; also documents limits of identity scopes.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://mcp.notion.com/.well-known/oauth-protected-resource",
      "date_or_version": "Live metadata; accessed 2026-10-30",
      "source_type": "Primary live OAuth metadata",
      "quote_under_25_words": "\"scopes_supported\":[\"default\"]",
      "supports": "Hosted MCP protected-resource advertised scope and bearer-header support.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://mcp.notion.com/.well-known/oauth-authorization-server",
      "date_or_version": "Live metadata; accessed 2026-10-30",
      "source_type": "Primary live OAuth metadata",
      "quote_under_25_words": "\"grant_types_supported\":[\"authorization_code\",\"refresh_token\",\"urn:ietf:params:oauth:grant-type:jwt-bearer\"]",
      "supports": "Advertised auth grants, scope names, PKCE S256, registration and token endpoints; meaning/eligibility of nonstandard or JWT-bearer scopes/grants is not explained here.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://developers.notion.com/guides/mcp/mcp-supported-tools",
      "date_or_version": "Undated live vendor documentation; accessed 2026-10-30",
      "source_type": "Primary vendor tool reference",
      "quote_under_25_words": "The call must set user_confirmed: true.",
      "supports": "Tool inventory and semantics; conditional tool access; user confirmation, delete/restore effects, comment actions, async writes, plan gates and API rate limits.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://developers.notion.com/page/changelog",
      "date_or_version": "Live changelog; accessed 2026-10-30; individual extracted entry dates not rendered",
      "source_type": "Primary vendor changelog",
      "quote_under_25_words": "Two new Notion MCP tools move content to Trash after the user confirms.",
      "supports": "Change history for delete tools and confirmation behavior; tool set is version-sensitive.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://www.notion.com/help/notion-mcp",
      "date_or_version": "Undated live vendor help article; accessed 2026-10-30",
      "source_type": "Primary vendor Help Center",
      "quote_under_25_words": "MCP tools act with your full Notion permissions—they can access everything you can access.",
      "supports": "User-permission model, Enterprise MCP governance, enterprise-managed connections and connected-source caveats.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://developers.notion.com/docs/authorization",
      "date_or_version": "Undated live REST API authorization guide; accessed 2026-10-30",
      "source_type": "Primary vendor API documentation; not the hosted MCP guide",
      "quote_under_25_words": "After a user authorizes a public connection, only that user is able to interact or share pages and databases with the connection.",
      "supports": "REST public-connection page-sharing model, explicitly distinguished from hosted remote MCP.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://www.notion.com/pricing",
      "date_or_version": "Undated live pricing page; accessed 2026-10-30; page states USD",
      "source_type": "Primary vendor pricing page",
      "quote_under_25_words": "Price in USD",
      "supports": "Pricing is presented in USD; reviewed page did not list an MCP-specific charge or India-specific quote.",
      "status": "NOT FOUND"
    },
    {
      "url": "https://github.com/makenotion/notion-mcp-server",
      "date_or_version": "Live official repository README; accessed 2026-10-30; README references API versions 2025-09-03 and 2026-03-11",
      "source_type": "Primary official GitHub repository",
      "quote_under_25_words": "This repository is a separate, self-hosted MCP server implementation that is no longer actively maintained or supported.",
      "supports": "Legacy local server distinction, support status, token/manual page sharing model, transport options and version-sensitive API details.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://modelcontextprotocol.io/specification/2026-07-28/schema",
      "date_or_version": "MCP schema version 2026-07-28",
      "source_type": "Primary protocol specification/schema",
      "quote_under_25_words": "title?: string; readOnlyHint?: boolean; destructiveHint?: boolean; idempotentHint?: boolean; openWorldHint?: boolean;",
      "supports": "Exact standard annotation property names; specification says these are behavioral hints, not guarantees.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://modelcontextprotocol.io/specification/2026-07-28/server/tools",
      "date_or_version": "MCP specification version 2026-07-28",
      "source_type": "Primary protocol specification",
      "quote_under_25_words": "Clients SHOULD prompt for user confirmation on sensitive operations.",
      "supports": "General MCP confirmation guidance; client approval behavior is not guaranteed by annotations alone.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://github.com/makenotion/notion-mcp-server/issues/333",
      "date_or_version": "Issue reported 2025-10-17 per GitHub search result; accessed 2026-10-30; over six months old",
      "source_type": "Community report in the official local-server repository",
      "quote_under_25_words": "The implementation keeps an explicit allowlist for POST-based read operations instead of relying solely on the HTTP verb.",
      "supports": "Reported annotation bug/fix context in legacy local server; not evidence of current hosted MCP annotations.",
      "status": "REPORTED"
    }
  ],


"sources": [
    {
      "url": "https://linear.app/docs/mcp",
      "date_or_version": "Undated official docs; accessed 2026-10-30",
      "source_type": "Primary vendor documentation",
      "quote_under_25_words": "Our MCP server uses Streamable HTTP as the primary transport",
      "supports": "Primary transport and hosted MCP connection",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://linear.app/docs/mcp",
      "date_or_version": "Undated official docs; accessed 2026-10-30",
      "source_type": "Primary vendor documentation",
      "quote_under_25_words": "Connect to https://mcp.linear.app/mcp/readonly, which only ever exposes read tools",
      "supports": "Read-only endpoint; docs also support requesting read scope",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://linear.app/docs/mcp",
      "date_or_version": "Undated official docs; accessed 2026-10-30",
      "source_type": "Primary vendor documentation",
      "quote_under_25_words": "supports passing OAuth token and API keys directly in the Authorization: Bearer <yourtoken> header",
      "supports": "Direct bearer credential alternative, including API key or OAuth token",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://linear.app/docs/mcp",
      "date_or_version": "Undated official docs; accessed 2026-10-30",
      "source_type": "Primary vendor documentation",
      "quote_under_25_words": "finding, creating, and updating objects in Linear like issues, projects, and comments",
      "supports": "Broad documented read/write object categories, not an exact tool catalog",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://linear.app/docs/mcp",
      "date_or_version": "Undated official docs; accessed 2026-10-30",
      "source_type": "Primary vendor documentation",
      "quote_under_25_words": "claude mcp add --transport http linear-server https://mcp.linear.app/mcp",
      "supports": "Practical single-connector setup for Claude Code",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://mcp.linear.app/.well-known/oauth-protected-resource/mcp",
      "date_or_version": "Live metadata observed 2026-10-30",
      "source_type": "Primary live OAuth protected-resource metadata",
      "quote_under_25_words": "\"scopes_supported\":[\"read\",\"write\"]",
      "supports": "Linear MCP resource-level OAuth scope names",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://mcp.linear.app/.well-known/oauth-authorization-server",
      "date_or_version": "Live metadata observed 2026-10-30",
      "source_type": "Primary live OAuth authorization-server metadata",
      "quote_under_25_words": "\"scopes_supported\":[\"read\",\"write\",\"openid\",\"email\"]",
      "supports": "Authorization-server scopes; distinguish identity scopes from MCP resource scopes",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://mcp.linear.app/.well-known/oauth-authorization-server",
      "date_or_version": "Live metadata observed 2026-10-30",
      "source_type": "Primary live OAuth authorization-server metadata",
      "quote_under_25_words": "\"client_id_metadata_document_supported\":true",
      "supports": "Client ID Metadata Documents advertised alongside registration endpoint in server metadata",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://linear.app/docs/api-and-webhooks",
      "date_or_version": "Undated official docs; accessed 2026-10-30",
      "source_type": "Primary vendor documentation",
      "quote_under_25_words": "Read, Write, Admin, Create issues, Create comments",
      "supports": "Available Linear personal API-key permission restrictions",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://linear.app/docs/api-and-webhooks",
      "date_or_version": "Undated official docs; accessed 2026-10-30",
      "source_type": "Primary vendor documentation",
      "quote_under_25_words": "You can also limit an API key’s access to specific teams in your workspace.",
      "supports": "Team-limited API keys",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://linear.app/docs/api-and-webhooks",
      "date_or_version": "Undated official docs; accessed 2026-10-30",
      "source_type": "Primary vendor documentation",
      "quote_under_25_words": "Admins can choose whether or not Members can create their own API keys",
      "supports": "Workspace admin control over member API-key creation",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://linear.app/pricing",
      "date_or_version": "Pricing page accessed 2026-10-30; undated/version-sensitive",
      "source_type": "Primary vendor pricing page",
      "quote_under_25_words": "MCP access Included Included Included Included",
      "supports": "MCP listed as included in Free, Basic, Business, and Enterprise plan columns",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://linear.app/developers/rate-limiting",
      "date_or_version": "Undated official docs; accessed 2026-10-30; version-sensitive",
      "source_type": "Primary vendor developer documentation",
      "quote_under_25_words": "When authenticated using an API key you can make up to 2,500 requests per hour.",
      "supports": "General GraphQL API-key request cap; not a declared MCP-specific quota",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://linear.app/developers/rate-limiting",
      "date_or_version": "Undated official docs; accessed 2026-10-30; version-sensitive",
      "source_type": "Primary vendor developer documentation",
      "quote_under_25_words": "OAuth App | 5,000 | User (or App User) | 1 hour",
      "supports": "General GraphQL OAuth-app request cap and quota attribution",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://linear.app/docs/login-methods",
      "date_or_version": "Undated official docs; accessed 2026-10-30",
      "source_type": "Primary vendor documentation",
      "quote_under_25_words": "Login restrictions are available to workspaces on our Business and Enterprise plans.",
      "supports": "General login restriction tier availability; MCP-specific applicability not stated",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://linear.app/docs/login-methods",
      "date_or_version": "Undated official docs; accessed 2026-10-30",
      "source_type": "Primary vendor documentation",
      "quote_under_25_words": "SAML authentication and IP restrictions are only available to workspaces on our Enterprise plan.",
      "supports": "Enterprise-only SAML/IP login features; no claim that IP rules target MCP",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://modelcontextprotocol.io/specification/2026-07-28/changelog",
      "date_or_version": "MCP specification 2026-07-28; current published version located as of 2026-10-30",
      "source_type": "Primary protocol specification changelog",
      "quote_under_25_words": "Deprecate the OAuth 2.0 Dynamic Client Registration Protocol (RFC7591) as a client registration mechanism in favor of Client ID Metadata Documents",
      "supports": "Current MCP DCR status; retained for backwards compatibility",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://modelcontextprotocol.io/specification/2026-07-28/server/tools",
      "date_or_version": "MCP specification 2026-07-28",
      "source_type": "Primary protocol specification",
      "quote_under_25_words": "The set MAY vary by the authorization presented on the request",
      "supports": "Why current tools/list inventory may depend on credentials/scopes",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://raw.githubusercontent.com/modelcontextprotocol/modelcontextprotocol/main/schema/2026-07-28/schema.ts",
      "date_or_version": "Schema version 2026-07-28; official GitHub source",
      "source_type": "Primary protocol schema",
      "quote_under_25_words": "readOnlyHint?: boolean; destructiveHint?: boolean; idempotentHint?: boolean; openWorldHint?: boolean;",
      "supports": "Exact standardized optional annotation names; not Linear annotation values",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization",
      "date_or_version": "MCP specification 2026-07-28",
      "source_type": "Primary protocol specification",
      "quote_under_25_words": "MCP clients MUST NOT send tokens to the MCP server other than ones issued by the MCP server’s authorization server.",
      "supports": "OAuth token audience/issuer restriction for MCP clients and gateway designs",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://mcp.linear.app/mcp",
      "date_or_version": "Direct unauthenticated probe 2026-10-30",
      "source_type": "Primary live service behavior",
      "quote_under_25_words": "HTTP 401; WWW-Authenticate: Bearer; scope=\"read write\"",
      "supports": "Unauthenticated initialization is gated; no public tool list obtained in this check",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://github.com/linear/linear/issues/1049",
      "date_or_version": "Issue opened 2026-02-25; older than six months at research date; version-sensitive",
      "source_type": "GitHub report in Linear repository; reported behavior",
      "quote_under_25_words": "update_issue is gone from tools/list, replaced by save_issue",
      "supports": "Historical report of tool rename and stale client catalog behavior; not a current verified catalog",
      "status": "REPORTED"
    },
    {
      "url": "https://github.com/linear/linear/issues/1223",
      "date_or_version": "Issue opened 2026-07-28; reported endpoint probe; version-sensitive",
      "source_type": "GitHub community issue in Linear repository; reported behavior",
      "quote_under_25_words": "POST https://mcp.linear.app/sse -> 404; POST https://mcp.linear.app/mcp -> 401",
      "supports": "Counter-evidence about stale MCP registry endpoint; report says /mcp was live and gated",
      "status": "REPORTED"
    },
    {
      "url": "https://linear.app/docs/mcp",
      "date_or_version": "Undated official docs; accessed 2026-10-30",
      "source_type": "Primary vendor documentation",
      "quote_under_25_words": "The SSE endpoint at https://mcp.linear.app/sse is a deprecated fallback",
      "supports": "Linear’s documented legacy transport position; use /mcp for new connections",
      "status": "DOCUMENTED"
    }
  ],

 "sources": [
    {
      "url": "https://supabase.com/docs/guides/ai-tools/mcp",
      "date_or_version": "Live vendor docs; accessed 2026-10-30 (page did not expose a revision date)",
      "source_type": "Primary — Supabase documentation",
      "quote_under_25_words": "If no project is selected, all projects will be accessible.",
      "supports": "Hosted endpoint, OAuth setup, project/read-only/features parameters, tool inventory, mutation/confirmation caveats, unattended guidance, branching plan constraint.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://github.com/supabase/mcp/releases/tag/mcp-server-supabase-v0.15.0",
      "date_or_version": "v0.15.0, 2026-10-29",
      "source_type": "Primary — vendor GitHub release",
      "quote_under_25_words": "submit_feedback and delete_feedback tools (#474)",
      "supports": "Latest release at research date and newly released tool names; shows rapid ongoing changes and docs/tool-surface drift.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://github.com/supabase/mcp/blob/main/packages/mcp-server-supabase/src/tools/database-operation-tools.ts",
      "date_or_version": "Mutable main source checked 2026-10-30; current version-sensitive implementation",
      "source_type": "Primary — vendor source code",
      "quote_under_25_words": "readOnlyHint: false, destructiveHint: true, idempotentHint: false, openWorldHint: true",
      "supports": "Exact current annotations for apply_migration and execute_sql; source also marks read-only mode as blocking apply_migration and execute_sql as adaptable.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://supabase.com/docs/guides/platform/personal-access-tokens",
      "date_or_version": "Live vendor docs; accessed 2026-10-30",
      "source_type": "Primary — Supabase documentation",
      "quote_under_25_words": "A token used to authenticate the MCP server can only call the tools its granted permissions unlock.",
      "supports": "PATs authenticate MCP/Management API; token permission scoping, CI use, and tool-to-permission mapping; reveals get_logs vs query_logs naming drift.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://supabase.com/docs/guides/getting-started/api-keys",
      "date_or_version": "Live vendor docs; accessed 2026-10-30",
      "source_type": "Primary — Supabase documentation",
      "quote_under_25_words": "A secret key bypasses every Row Level Security policy you have.",
      "supports": "Secret/service_role elevated access and the distinction from OAuth/PAT credentials; advises server-only handling.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://github.com/modelcontextprotocol/servers-archived",
      "date_or_version": "Repository archived 2025-05-29 (GitHub archive status); checked 2026-10-30",
      "source_type": "Primary — MCP organization GitHub repository",
      "quote_under_25_words": "These servers are no longer maintained",
      "supports": "Reference implementations including PostgreSQL are archived; no security guarantees, fixes, or maintenance.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://github.com/modelcontextprotocol/servers-archived/tree/main/src/postgres",
      "date_or_version": "Archived source; historical implementation, checked 2026-10-30",
      "source_type": "Primary — MCP organization GitHub README/source",
      "quote_under_25_words": "All queries are executed within a READ ONLY transaction",
      "supports": "Reference tool `query`, schema resources, read-only transaction design, and stdio/npx/Docker connection examples.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://securitylabs.datadoghq.com/articles/mcp-vulnerability-case-study-SQL-injection-in-the-postgresql-mcp-server/",
      "date_or_version": "2025-08-21; older than six months at research date",
      "source_type": "Secondary — Datadog Security Labs vulnerability analysis",
      "quote_under_25_words": "allowed us to bypass the read-only restriction and execute arbitrary SQL statements.",
      "supports": "Reported stacked-statement/COMMIT read-only bypass, legacy package risk, and Zed fork fix v0.1.4; not an official advisory and historical remediation caveat applies.",
      "status": "REPORTED"
    },
    {
      "url": "https://github.com/crystaldba/postgres-mcp",
      "date_or_version": "README checked 2026-10-30; version-sensitive project documentation",
      "source_type": "Primary — community project GitHub README",
      "quote_under_25_words": "Postgres MCP Pro supports both the Standard Input/Output (stdio) and Server-Sent Events (SSE) transports",
      "supports": "Community alternative’s documented transports, modes, SQL/read-write behavior and tool names.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://api.github.com/repos/crystaldba/postgres-mcp",
      "date_or_version": "GitHub metadata checked 2026-10-30; pushed_at 2026-08-17",
      "source_type": "Primary — GitHub repository API metadata",
      "quote_under_25_words": "\"pushed_at\": \"2026-08-17T05:06:35Z\"",
      "supports": "Repository is not archived and had a recent push; activity does not by itself establish support or security quality.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://api.github.com/repos/crystaldba/postgres-mcp/releases",
      "date_or_version": "Latest exposed release v0.3.0, 2025-05-16; older than six months",
      "source_type": "Primary — GitHub releases API",
      "quote_under_25_words": "Release v0.3.0 adds windows support and index optimization by LLM",
      "supports": "Last tagged release observed; contrast with more recent repository push and flag release freshness.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://modelcontextprotocol.io/specification/2025-06-18/schema",
      "date_or_version": "MCP schema version 2025-06-18; older than six months",
      "source_type": "Primary — MCP specification schema",
      "quote_under_25_words": "all properties in ToolAnnotations are hints. They are not guaranteed to provide a faithful description of tool behavior",
      "supports": "Exact annotation field names and non-guarantee semantics; version-age caveat applies.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://modelcontextprotocol.io/specification/2026-07-28/basic/transports",
      "date_or_version": "MCP specification 2026-07-28",
      "source_type": "Primary — MCP specification",
      "quote_under_25_words": "Streamable HTTP: each message is an HTTP POST to a single MCP endpoint",
      "supports": "Current transport distinction: stdio and Streamable HTTP; differentiates this from community README’s SSE mode.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://supabase.com/docs/guides/platform/billing-on-supabase",
      "date_or_version": "Live vendor docs; accessed 2026-10-30",
      "source_type": "Primary — Supabase billing documentation",
      "quote_under_25_words": "You are granted two free projects.",
      "supports": "Free plan project entitlement and billing distinctions.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://supabase.com/pricing",
      "date_or_version": "Live pricing page; accessed 2026-10-30",
      "source_type": "Primary — Supabase pricing page",
      "quote_under_25_words": "Free projects are paused after 1 week of inactivity. Limit of 2 active projects.",
      "supports": "Free project pause and active-project limit; plan/tier figures are time-sensitive.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://supabase.com/docs/guides/platform/regions",
      "date_or_version": "Live vendor docs; accessed 2026-10-30",
      "source_type": "Primary — Supabase documentation",
      "quote_under_25_words": "South Asia (Mumbai) ap-south-1",
      "supports": "Mumbai is a listed specific Supabase region; this page does not establish Free-tier eligibility.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://supabase.com/docs/guides/database/connecting-to-postgres",
      "date_or_version": "Live vendor docs; accessed 2026-10-30",
      "source_type": "Primary — Supabase documentation",
      "quote_under_25_words": "postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres",
      "supports": "Direct database URI/password model used by generic PostgreSQL connectors, contrasted with Supabase MCP PAT/OAuth.",
      "status": "DOCUMENTED"
    }
  ],

"sources": [
    {
      "url": "https://github.com/modelcontextprotocol/servers/blob/main/README.md",
      "date_or_version": "Current repository README; accessed 2026-10-30 (unversioned, recheck if changed)",
      "source_type": "Official primary-source repository documentation",
      "quote_under_25_words": "not as production-ready solutions",
      "supports": "Official/reference status; project responsibility and licensing context.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://github.com/modelcontextprotocol/servers/releases/latest",
      "date_or_version": "Latest release page; ledger v2.2.0; server-filesystem package 2.1.0; accessed 2026-10-30; version-sensitive",
      "source_type": "Official primary-source release notes",
      "quote_under_25_words": "fix(filesystem): bound realpath/readdir waits and recursive walks",
      "supports": "Current active maintenance and recent filesystem fixes; Node runtime notice recommends patched releases.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://raw.githubusercontent.com/modelcontextprotocol/servers/main/src/filesystem/index.ts",
      "date_or_version": "Current main branch source; accessed 2026-10-30 (unversioned; pin tag for audit)",
      "source_type": "Official primary-source source code",
      "quote_under_25_words": "const transport = new StdioServerTransport();",
      "supports": "Package implementation starts stdio; source registers `read_file` as deprecated; no HTTP transport in this entrypoint.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/stdio",
      "date_or_version": "MCP specification 2026-07-28 (within six months)",
      "source_type": "Official normative specification",
      "quote_under_25_words": "The server reads JSON-RPC messages from stdin and writes JSON-RPC messages to stdout.",
      "supports": "Stdio framing, subprocess communication, stdout/stderr contract and process lifecycle.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://modelcontextprotocol.io/specification/2026-07-28/changelog",
      "date_or_version": "MCP specification 2026-07-28 (within six months)",
      "source_type": "Official specification changelog",
      "quote_under_25_words": "Make MCP stateless: remove the initialize / notifications/initialized handshake.",
      "supports": "2026-07-28 breaking changes and Roots deprecation context.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://modelcontextprotocol.io/specification/2026-07-28/deprecated",
      "date_or_version": "MCP specification deprecated registry 2026-07-28 (within six months)",
      "source_type": "Official normative specification registry",
      "quote_under_25_words": "new implementations SHOULD NOT adopt them",
      "supports": "Roots deprecation state and migration path; feature remains deprecated, not removed.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://github.com/modelcontextprotocol/servers/blob/main/src/filesystem/README.md",
      "date_or_version": "Current main branch README; accessed 2026-10-30 (unversioned; version-sensitive)",
      "source_type": "Official primary-source package documentation",
      "quote_under_25_words": "This is the only method that works on every protocol version",
      "supports": "CLI allowed-directory setup, full API tools, annotations, effects, Node requirement, Docker read-only bind-mount example; contains a feature/API delete inconsistency.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://raw.githubusercontent.com/modelcontextprotocol/servers/main/src/filesystem/index.ts",
      "date_or_version": "Current main branch source; accessed 2026-10-30 (unversioned; version-sensitive)",
      "source_type": "Official primary-source source code",
      "quote_under_25_words": "title: \"Read File (Deprecated)\"",
      "supports": "Additional deprecated legacy `read_file` registration; current source-level implementation detail.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://modelcontextprotocol.io/specification/2026-07-28",
      "date_or_version": "MCP specification 2026-07-28 (within six months)",
      "source_type": "Official normative specification overview",
      "quote_under_25_words": "descriptions of tool behavior such as annotations should be considered untrusted",
      "supports": "Tool hints are not enforcement; consent and trust guidance.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://github.com/advisories/GHSA-hc55-p739-j48w",
      "date_or_version": "Published 2025-07-01; updated 2025-07-02 (older than six months; version-sensitive advisory)",
      "source_type": "GitHub-reviewed security advisory for official package",
      "quote_under_25_words": "Patched versions 2025.7.1",
      "supports": "CVE-2025-53110 affected and patched version ranges; advisory reports path-validation bypass via colliding prefix.",
      "status": "REPORTED"
    },
    {
      "url": "https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization",
      "date_or_version": "MCP authorization spec 2026-07-28 (within six months)",
      "source_type": "Official normative specification",
      "quote_under_25_words": "Implementations using an STDIO transport SHOULD NOT follow this specification",
      "supports": "OAuth authorization scope limited to HTTP transports; stdio credentials should be environmental.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http",
      "date_or_version": "MCP specification 2026-07-28 (within six months)",
      "source_type": "Official normative transport specification",
      "quote_under_25_words": "Servers MUST validate the Origin header on all incoming connections",
      "supports": "Gateway/remote HTTP security: Origin validation, localhost binding recommendation, authentication recommendation.",
      "status": "DOCUMENTED"
    }
  ],

"sources": [
    {
      "url": "https://docs.composio.dev/docs/how-composio-works",
      "date_or_version": "Undated live documentation; accessed 2026-10-30",
      "source_type": "Official vendor documentation",
      "quote_under_25_words": "A session is the runtime context for an agentic run: the scoped environment an AI agent works in while it acts for one of your users.",
      "supports": "Session model, user/toolkit/auth/account scoping and execution routing.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://docs.composio.dev/docs/authentication",
      "date_or_version": "Undated live documentation; accessed 2026-10-30",
      "source_type": "Official vendor documentation",
      "quote_under_25_words": "Composio manages their tokens for you.",
      "supports": "Per-user managed authentication and automatic refresh/reconnect lifecycle.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://docs.composio.dev/docs/configuring-sessions",
      "date_or_version": "Undated live docs; accessed 2026-10-30; approval settings marked experimental",
      "source_type": "Official vendor documentation",
      "quote_under_25_words": "An explicit empty allowlist means no app toolkits at all.",
      "supports": "Session toolkit/tool/tag filters, approval configuration and direct-tools preset.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://docs.composio.dev/docs/security/token-custody",
      "date_or_version": "Undated live documentation; accessed 2026-10-30",
      "source_type": "Official vendor security documentation",
      "quote_under_25_words": "In the default Composio Cloud deployment, Composio has custody of those credentials.",
      "supports": "Token custody, API redaction, proxy execution and KMS deployment options.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://docs.composio.dev/docs/sessions-via-mcp",
      "date_or_version": "Undated live docs; accessed 2026-10-30; SDK minimums @composio/core 0.19.1 and Python composio 0.22.1",
      "source_type": "Official vendor documentation",
      "quote_under_25_words": "The MCP endpoint and session.tools() are backed by the same session.",
      "supports": "Hosted MCP, headers, project-vs-user API key scope, fixed tool set, MCP execution limitations.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://docs.composio.dev/docs/firewall",
      "date_or_version": "Undated live documentation; accessed 2026-10-30",
      "source_type": "Official vendor documentation",
      "quote_under_25_words": "An after_execute hook can't undo the tool call, since the tool has already run.",
      "supports": "Per-call/result policy timing and Firewall behavior.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://composio.dev/pricing",
      "date_or_version": "Live pricing page accessed 2026-10-30; new pricing effective 2026-08-15; grandfathering through 2026-12-31",
      "source_type": "Official vendor pricing page",
      "quote_under_25_words": "100,000 tool calls, 50,000 triggers, and 3 team members included free each month.",
      "supports": "Hobby/Pro/Enterprise plans, allowances, overages, managed-app pricing, rate limits and effective dates.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://docs.composio.dev/reference/rate-limits",
      "date_or_version": "Undated live reference accessed 2026-10-30; plan labels/windows conflict with pricing page",
      "source_type": "Official vendor documentation",
      "quote_under_25_words": "Rate limits are enforced per organization and reset on a rolling 10-minute window.",
      "supports": "Separate per-plan limits and the discrepancy versus pricing page.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://composio.dev/blog/composio-may-2026-security-incident",
      "date_or_version": "May 2026 disclosure, updated 2026-09-16",
      "source_type": "Official vendor incident disclosure",
      "quote_under_25_words": "The May disclosure reported leaked connections representing about 0.3% of active connections, including 5,001 GitHub connections.",
      "supports": "Incident scale, potentially exposed API keys and vendor incident response.",
      "status": "REPORTED"
    },
    {
      "url": "https://composio.dev/content/how-composio-rebuilt-credential-security-after-may-2026",
      "date_or_version": "2026-10-21; remediation documented in August/September 2026",
      "source_type": "Official vendor security article",
      "quote_under_25_words": "Composio API keys and session keys are stored only as hashes, with no recoverable copy.",
      "supports": "Post-incident controls, KMS, Proxy Execute constraints and AppSecure assessment claims.",
      "status": "REPORTED"
    },
    {
      "url": "https://composio.dev/blog/two-questions-every-security-review-asks-us",
      "date_or_version": "2026-09-09",
      "source_type": "Official vendor security architecture article",
      "quote_under_25_words": "Composio Cloud runs in the United States. For EU residency, use a self-hosted deployment in an EU region.",
      "supports": "Vendor-stated Composio Cloud region and EU residency route; India region not stated.",
      "status": "REPORTED"
    },
    {
      "url": "https://docs.composio.dev/reference/changelog",
      "date_or_version": "Undated current changelog entry; accessed 2026-10-30; version not visible",
      "source_type": "Official vendor changelog",
      "quote_under_25_words": "map regions to correct API hosts (EU, India, or Standard).",
      "supports": "Mixpanel provider-region routing only, not Composio-hosted residency.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://modelcontextprotocol.io/specification/2026-07-28/server/tools",
      "date_or_version": "MCP specification 2026-07-28",
      "source_type": "Official MCP specification",
      "quote_under_25_words": "The protocol itself does not mandate any specific user interaction model.",
      "supports": "Current MCP tools interaction model and protocol revision to test against.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://modelcontextprotocol.io/specification/2026-07-28/schema",
      "date_or_version": "MCP schema 2026-07-28",
      "source_type": "Official MCP specification schema",
      "quote_under_25_words": "All properties in ToolAnnotations are hints. They are not guaranteed to provide a faithful description of tool behavior.",
      "supports": "Exact MCP annotation names and their non-authoritative nature.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://github.com/ComposioHQ/composio",
      "date_or_version": "Live repository README accessed 2026-10-30; captured page has no commit date",
      "source_type": "Official vendor GitHub repository",
      "quote_under_25_words": "This is the Composio SDK monorepo.",
      "supports": "Official TypeScript/Python SDK and adapter repository.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://material.security/resources/the-composio-breach-one-token-10242-doors",
      "date_or_version": "2026-06-03",
      "source_type": "Secondary security analysis",
      "quote_under_25_words": "attackers exfiltrated approximately 5,241 API keys and 5,001 GitHub OAuth tokens.",
      "supports": "Secondary incident account; stronger API-key wording differs from Composio’s ‘potentially exposed’ wording.",
      "status": "REPORTED"
    }
  ],

"sources": [
    {
      "url": "https://docs.arcade.dev/en/build/create-tools/tool-basics/create-tool-auth",
      "date_or_version": "Undated live docs; accessed 2026-10-30",
      "source_type": "Official Arcade documentation",
      "quote_under_25_words": "Arcade checks if the user has already authorized the scopes required by the tool.",
      "supports": "Tool-level authorization is checked at invocation; missing authorization invokes OAuth; token injected into runtime context, not client/LLM; refresh/reuse; least-privilege guidance.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://docs.arcade.dev/en/learn/server-level-vs-tool-level-auth",
      "date_or_version": "Undated live docs; accessed 2026-10-30",
      "source_type": "Official Arcade documentation",
      "quote_under_25_words": "Arcade manages the entire OAuth flow, including token refresh and secure storage.",
      "supports": "Differentiates downstream tool authorization from server-level Resource Server Auth and describes arcade deploy, HTTP and stdio distinctions.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://docs.arcade.dev/references/auth-providers/oauth2",
      "date_or_version": "Undated live docs; accessed 2026-10-30",
      "source_type": "Official Arcade documentation",
      "quote_under_25_words": "If not provided, refresh tokens will not be used.",
      "supports": "Custom OAuth2 authorization-code flow and conditional refresh-token configuration; custom OAuth provider settings.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://docs.arcade.dev/guides/mcp-gateways",
      "date_or_version": "Search index dates page 2026-10-28; accessed 2026-10-30",
      "source_type": "Official Arcade documentation",
      "quote_under_25_words": "Simplify configuration - One gateway URL instead of multiple server configurations",
      "supports": "Gateway federation, endpoint format, auth modes including Arcade Auth/User Source/Arcade Headers and authorization headers; useful single-connector setup.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://www.arcade.dev/pricing",
      "date_or_version": "Live pricing page observed 2026-10-30; no page revision date displayed",
      "source_type": "Official Arcade pricing page",
      "quote_under_25_words": "Auth events at $0.10 each; Tool calls at $0.01 each",
      "supports": "Free, Team, Enterprise tiers, posted monthly/platform prices, included monthly usage and per-unit metering as displayed on access date.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://docs.arcade.dev/operate/deploy/arcade-cloud",
      "date_or_version": "Undated live docs; accessed 2026-10-30",
      "source_type": "Official Arcade documentation",
      "quote_under_25_words": "All of Arcade Cloud’s infrastructure is located in the United States",
      "supports": "US-only Arcade Cloud storage/processing; customer-controlled residency through self-hosting/on-premises/preferred cloud region; enterprise VPC peering availability.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://docs.arcade.dev/operate/governance/remote-mcp-servers",
      "date_or_version": "2026-10-19 (search-indexed page date); accessed 2026-10-30",
      "source_type": "Official Arcade documentation",
      "quote_under_25_words": "Prompts, resources, and sampling are not supported yet.",
      "supports": "Remote server registration and scope; runtime user OAuth; current documented remote server transport and tools-only limitation.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://docs.arcade.dev/references/changelog",
      "date_or_version": "Latest dated entry in retrieved content: 2026-07-26; accessed 2026-10-30",
      "source_type": "Official Arcade changelog",
      "quote_under_25_words": "Add MCP behavior annotations to Arcade builtin tools.",
      "supports": "Dated platform history and July 17 MCP features, including behavior annotations, stateless tools/list and tools/call, scope handling and token-refresh tests. Changelog is older than six months only if measured from a future date; as of research date it is about three months old, but still older than the October docs.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://github.com/ArcadeAI/arcade-mcp",
      "date_or_version": "Current repository README accessed 2026-10-30; no README revision date captured",
      "source_type": "Official Arcade GitHub repository",
      "quote_under_25_words": "It powers the 7,500+ prebuilt tools across 81 MCP servers at Arcade.dev",
      "supports": "Open-source Python framework positioning, vendor-stated tool/server counts, token injection/refresh/scoping, generic and built-in auth helper support.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://pypi.org/project/arcade-mcp-server/1.33.0/",
      "date_or_version": "1.33.0; released 2026-10-29; provenance verified by PyPI 2026-10-29",
      "source_type": "Package registry primary record (PyPI; package owner Arcade.dev)",
      "quote_under_25_words": "Released: Oct 29, 2026",
      "supports": "Latest open-source Python MCP server framework package version and date as of 2026-10-30; requires Python >=3.10. Not the Arcade Cloud service version.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://modelcontextprotocol.io/specification/2025-06-18/basic/authorization",
      "date_or_version": "MCP specification 2025-06-18; older than six months at 2026-10-30",
      "source_type": "MCP protocol specification (primary standard; not Arcade vendor source)",
      "quote_under_25_words": "Implementations using an HTTP-based transport SHOULD conform to this specification.",
      "supports": "Dated baseline for HTTP transport authorization, OAuth/resource server roles, token handling and protocol-side security; MCP client confirmation is a SHOULD rather than Arcade per-call behavior.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://docs.arcade.dev/en/get-started/quickstarts/call-tool-client",
      "date_or_version": "Undated live docs; accessed 2026-10-30",
      "source_type": "Official Arcade documentation",
      "quote_under_25_words": "An MCP Gateway lets you pick the tools for this workflow",
      "supports": "Practical curated gateway setup, tool selection and one client endpoint; documents OAuth versus header authentication use cases.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://github.com/ArcadeAI/arcade-mcp-ts/releases",
      "date_or_version": "Repository archived 2026-10-14; release v0.18.3 visible; release date not shown in extracted page",
      "source_type": "Official Arcade GitHub repository release page (archived TypeScript project)",
      "quote_under_25_words": "This repository was archived by the owner on Oct 14, 2026.",
      "supports": "Counter-evidence/caveat: archived TypeScript project; v0.18.3 notes `_meta.arcade.requirements.authorization`, but not a current hosted service or Python framework contract.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://github.com/ArcadeAI/arcade-mcp-ts/issues/58",
      "date_or_version": "Archived TypeScript port issue; accessed 2026-10-30",
      "source_type": "Official Arcade GitHub issue (project-owned repository; stale/version-sensitive)",
      "quote_under_25_words": "behavior→annotation mapping, _meta.arcade structure",
      "supports": "Source indicates an implementation mapping exists; does not enumerate exact current Arcade annotation names, so no name list is asserted in findings.",
      "status": "DOCUMENTED"
    }
  ],

"sources": [
    {
      "url": "https://www.keycard.ai/about/",
      "date_or_version": "Undated official page; accessed 2026-10-30",
      "source_type": "Primary vendor About page",
      "quote_under_25_words": "identity, policy, and audit from day one.",
      "supports": "Company positioning and product identity as agent identity/policy infrastructure.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://www.keycard.ai/blog/announcing-keycard-for-coding-agents/",
      "date_or_version": "2026-03-19; older than six months on 2026-10-30",
      "source_type": "Primary vendor product announcement",
      "quote_under_25_words": "Keycard for Coding Agents: identity, access, and governance",
      "supports": "Coding-agent product line and launch positioning; launch availability label is date-bound.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://www.keycard.ai/blog/announcing-keycard-for-multi-agent-apps/",
      "date_or_version": "2026-05-13; date/version-sensitive",
      "source_type": "Primary vendor product announcement",
      "quote_under_25_words": "identity, access, and telemetry for developers building agents",
      "supports": "Multi-Agent Apps identity, per-hop credentialing, supported frameworks/protocols and launch-time early-access status.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://www.keycard.ai/",
      "date_or_version": "Live page accessed 2026-10-30; undated",
      "source_type": "Primary vendor homepage",
      "quote_under_25_words": "A shared framework for deploying enterprise AI agents",
      "supports": "Current homepage foregrounds the Agent Baseline white paper rather than serving as a detailed product overview.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://www.keycard.ai/pricing/",
      "date_or_version": "Live pricing page accessed 2026-10-30; undated and commercially version-sensitive",
      "source_type": "Primary vendor pricing page",
      "quote_under_25_words": "5,000 transactions/mo (hard cap)",
      "supports": "Current listed Starter, Team and Enterprise tiers; monthly transaction allocations and overage pricing; enterprise deployments and features.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://docs.keycard.ai/admin/usage/",
      "date_or_version": "Live official docs accessed 2026-10-30; undated",
      "source_type": "Primary vendor usage/billing documentation",
      "quote_under_25_words": "the CLI brokers credentials for a coding agent’s session; it does not enforce policy on each tool call.",
      "supports": "Critical distinction between per-call enforcement and session credential hydration; transaction counting across protected and brokered access.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://docs.keycard.ai/reference/security-architecture/",
      "date_or_version": "Live official docs accessed 2026-10-30; undated, token details version-sensitive",
      "source_type": "Primary vendor security architecture documentation",
      "quote_under_25_words": "Stored in Keycard’s secure database",
      "supports": "Docs list OAuth tokens, static credentials, signing keys and provider secrets as stored secret materials; architecture describes encryption and KMS.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://docs.keycard.ai/admin/audit-log-and-sessions/",
      "date_or_version": "Live official docs accessed 2026-10-30; undated",
      "source_type": "Primary vendor audit/revocation documentation",
      "quote_under_25_words": "A credential already issued remains valid until it expires",
      "supports": "Revoking authorization prevents further issuance/refresh but may not invalidate an already-issued token immediately.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://docs.keycard.ai/guides/access-apis-on-behalf-of-users/",
      "date_or_version": "Live official docs accessed 2026-10-30; undated",
      "source_type": "Primary vendor integration guide",
      "quote_under_25_words": "Each tool call triggers a fresh credential exchange.",
      "supports": "Per-request delegated token exchange for the documented MCP-to-upstream API pattern; example flow and audit events.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://docs.keycard.ai/sdk/mcp/",
      "date_or_version": "Live official SDK reference accessed 2026-10-30; undated",
      "source_type": "Primary vendor SDK documentation",
      "quote_under_25_words": "requiredScopes: [\"mcp:tools\"]",
      "supports": "Exact example scope name, bearer verification and SDK MCP OAuth metadata; establishes this as an example, not a universal Keycard scope.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://docs.keycard.ai/admin/access-policies/",
      "date_or_version": "Live official docs accessed 2026-10-30; undated",
      "source_type": "Primary vendor policy documentation",
      "quote_under_25_words": "Keycard checks it every time it issues a credential.",
      "supports": "Cedar policy sets are checked at credential issuance; policy evaluation is distinct from session-level credential hydration.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://docs.keycard.ai/guides/mcp-server/",
      "date_or_version": "Live official guide accessed 2026-10-30; undated",
      "source_type": "Primary vendor MCP integration guide",
      "quote_under_25_words": "every tool call is tied to a verified user, scoped to explicit permissions, and logged for audit.",
      "supports": "Practical SDK setup for an owned MCP server, OAuth metadata, bearer-token validation and audit; supports the single-connector setup path.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization",
      "date_or_version": "MCP specification version 2025-11-25; older than six months on 2026-10-30",
      "source_type": "Primary MCP specification",
      "quote_under_25_words": "Authorization is OPTIONAL for MCP implementations.",
      "supports": "MCP authorization is optional and transport-level for HTTP-based transports; version-sensitive protocol context.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://modelcontextprotocol.io/specification/2025-11-25/schema",
      "date_or_version": "MCP schema version 2025-11-25; older than six months on 2026-10-30",
      "source_type": "Primary MCP specification schema",
      "quote_under_25_words": "readOnlyHint?: boolean; destructiveHint?: boolean; idempotentHint?: boolean; openWorldHint?: boolean",
      "supports": "These are official MCP ToolAnnotations names, defined as hints; no evidence they are Keycard authorization controls.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://workos.com/blog/keycard-vs-workos-agent-credentials-enterprise-authentication",
      "date_or_version": "2025-11-04; secondary and older than six months on 2026-10-30",
      "source_type": "Secondary vendor comparison (WorkOS; competitor source)",
      "quote_under_25_words": "Keycard pricing is not publicly disclosed.",
      "supports": "Counter-evidence/outdated pricing claim; contradicted by Keycard’s current public pricing page.",
      "status": "REPORTED"
    },
    {
      "url": "https://github.com/keycardai/go-sdk/releases",
      "date_or_version": "GitHub Releases page accessed 2026-10-30",
      "source_type": "Primary vendor GitHub repository metadata",
      "quote_under_25_words": "There aren’t any releases here",
      "supports": "No public GitHub Releases appear for this repository at access time; does not prove no package versioning elsewhere.",
      "status": "DOCUMENTED"
    },
    {
      "url": "https://github.com/keycardai/go-sdk/security/policy",
      "date_or_version": "GitHub Security page accessed 2026-10-30",
      "source_type": "Primary vendor GitHub security metadata",
      "quote_under_25_words": "No security policy detected",
      "supports": "No SECURITY.md policy detected for this repository at access time; repository-scoped caveat only.",
      "status": "DOCUMENTED"
    }
  ],

### Your notes



### Checked by Claude
Checked 30 Oct 2026 against primary pages (GitHub's README and `docs/remote-server.md`, FastMCP's docs and PyPI) and a handful of web searches. Only the claims below were checked. Everything else in the raw report stays **UNVERIFIED**: it came with no URLs or quotes, and its own text calls itself "untrusted".

**Confirmed from primary sources (GitHub)**
- **CONFIRMED.** The remote server is at `https://api.githubcopilot.com/mcp/`. Source: [remote-server.md](https://github.com/github/github-mcp-server/blob/main/docs/remote-server.md): "URL: https://api.githubcopilot.com/mcp/".
- **CONFIRMED.** A personal access token in an `Authorization: Bearer` header works. The README has a "Using a GitHub PAT" config, and says "Any host application that supports remote MCP servers should support the remote GitHub server with PAT authentication." That is what lets an unattended gateway connect without a browser.
- **CONFIRMED.** Read-only mode: add `/readonly` to the URL, or send `X-MCP-Readonly: true`. Toolsets: `X-MCP-Toolsets: repos,issues`, or `/x/{toolset}` for one.
- **CONFIRMED, and new (not in the report).** `X-MCP-Lockdown` hides public issue details written by people without push access. The docs call it "a best-effort content filter, not a security boundary." That is GitHub's own admission of the toxic-flow problem Sentinel handles (R7 and R8).
- **CONFIRMED.** Write tools in the README: `issue_write`, `add_issue_comment`, `create_gist`, `discussion_comment_write` (including delete), and `actions_run_trigger`. All of them are outbound-capable.

**Not confirmed (GitHub)**
- **NOT FOUND:** the report's "latest release v1.12.2, 2026-09-16". The README's Releases section was empty and showed no such version.
- **NOT FOUND:** the report's claim that the remote server works with a free student account and no Copilot licence. The docs neither require nor exclude a licence. This is the first thing to test.
- **NOT FOUND:** that fine-grained PATs work on the remote server. Classic PATs are the documented form.
- **NOT FOUND:** `readOnlyHint` or any MCP tool annotation in the docs. We would classify every tool ourselves, which we do anyway.
- **Summary only:** the names of the pull-request, file and repository tools (`create_pull_request`, `delete_file`, `delete_repository`, ...) came from a summary of the README's unread tail, not verbatim. Run `tools/list` before classifying.

**Confirmed (other)**
- **CONFIRMED, official changelog:** the MCP spec `2026-07-28` is stable. It is stateless, with no initialize handshake and no `Mcp-Session-Id`. HTTP+SSE is deprecated, and Dynamic Client Registration is deprecated in favour of Client ID Metadata Documents. Source: [changelog](https://modelcontextprotocol.io/specification/2026-07-28/changelog). **Correction (made later the same day):** I first wrote that the report's "Roots are deprecated" was imprecise. That was wrong. The changelog does both: it says "Deprecate the Roots, Sampling, and Logging features (SEP-2577)", and it removes some messages (`ping`, `logging/setLevel`, `notifications/roots/list_changed`) and replaces server-initiated requests such as `roots/list` and `sampling/createMessage` with a multi-round-trip pattern. The report was right.
- **CONFIRMED, vendor's own bulletin:** the Composio May 2026 incident. About 0.3% of active connections were affected, including about 5,001 GitHub connections, and an auxiliary cache likely exposed 5,241 API keys. Source: [composio.dev](https://composio.dev/blog/composio-may-2026-security-incident). A credential-brokering product was breached, which is exactly the risk of Sentinel holding every credential (roadmap W9).
- **CONFIRMED, FastMCP docs:** `create_proxy(url)` proxies a remote Streamable HTTP server, and `mcp.mount(create_proxy(url), namespace="x")` makes tool names `x_toolname`. Parent middleware "runs for all requests, including those routed to mounted servers". Progress, sampling, elicitation and roots are forwarded by default. Each request gets an isolated upstream session by default. Latest stable FastMCP is 4.1.4 (26 Oct 2026). Sources: [proxy](https://gofastmcp.com/servers/proxy), [composition](https://gofastmcp.com/servers/composition), [middleware](https://gofastmcp.com/servers/middleware), [PyPI](https://pypi.org/project/fastmcp/).
- **Not documented (FastMCP):** an `Authorization` header on the upstream connection. The docs show only `x-api-key`. Proxies forward incoming headers, including `Authorization`, to the backend by default, so we must set `forward_incoming_headers=False`. We already do that in Sentinel (spike C5), which is a strong reason to keep doing it for proxied upstreams.
- **Also NOT stated for proxies:** the docs do not say the parent's `on_call_tool` middleware runs on proxied tools. It is documented for mounted servers, and a proxy mounted with `mount()` is one, but we must test it before relying on it.

**Weaker support (secondary sources only, from search)**
- **Gmail (Google's own server):** a directory page lists 10 tools in Preview, with `create_draft` and no send tool; the report listed 9. If Google's server has no send tool, the "send an e-mail through Gmail" attack would not exist through it, but the Claude.ai Gmail connector does have a send tool. Not checked against Google's own docs.
- **Linear:** Bearer API key is described by two third-party docs, and the `/mcp/readonly` path by one (LiteLLM). Not confirmed on Linear's own docs.

**Problems with the report itself**
- No URLs, quotes or sources table, so under our rules every claim in it is unverified until checked.
- Not covered: all of Part 2 and the four deliverables.
- It was assembled from per-service sub-reports. Several contain internal hedges ("untrusted structured result", "trust but unverified"). Do not quote it as fact on the site.

**What it means for the F2 decision (provisional)**
- **GitHub is the best first real connector for tomorrow.** It is the only one where we have confirmed, from primary docs, a remote endpoint, a bearer token that needs no browser, a read-only switch, and write tools that send data outward. A public-repo comment or issue is a clean "data leaves" demo.
- **Linear and Supabase are the backups.** Both look workable with API-key or PAT headers, but our evidence is secondary.
- **Gmail, Slack and Microsoft 365 are not a one-day job:**
  - Gmail: Google's server is in Preview, and Google restricts Gmail access in testing mode (the report says 7-day refresh tokens and a 100-user cap; not checked against Google).
  - Slack: needs a Marketplace or internal app.
  - Microsoft 365: delegated sign-in only, and an admin has to approve it.
- **Still to test:** that a classic PAT works through our proxy, and that Sentinel's middleware sees proxied calls.

#### Update: the pasted sources were checked (30 Oct 2026, later the same day)
Navdeep pasted the sources for six services: GitHub, Google, Slack, Microsoft 365, Atlassian and Notion. I fetched every cited page and tested whether the quoted text is on it: **25 of 25 quotes are there** (two GitHub docs differed only in markdown formatting, and the text is right). The GitHub API results below were read live. The Slack endpoint answered 401 `missing_token` as the table says. Sources for Linear, Supabase, the filesystem server, Composio, Arcade and Keycard have not been pasted yet, so those claims stay unchecked.

**These change my earlier notes above:**
- **GitHub v1.12.2: the release is real but not the latest.** It was published 2026-09-16. The latest is **v2.0.3, published 2026-10-21**, after v2.0.0 on 2026-10-06. My "NOT FOUND" was wrong: the README's Releases box was empty, but the Releases API has it. The report calling v1.12.2 the latest was out of date by a major version.
- **GitHub v2.0.0 changed tool outputs.** Its release notes: structured outputs and output schemas, advertised only to clients that support MCP 2026-07-28 or later. Tool results from GitHub may therefore arrive as structured content, not only text. Our gateway reads `structured_content` in one place (`gateway.py:279`); I haven't tested it against GitHub v2 results, so test before we rely on it.
- **GitHub plan: CONFIRMED.** Quote from GitHub's own setup page: "The GitHub MCP server is available to all GitHub users regardless of plan type." My "no Copilot licence statement found" is superseded (the sources table adds a licensing caveat for some Copilot-specific tools). Fine-grained PATs on the **remote** server are still not documented; test with a throwaway token.
- **Gmail has no send tool: CONFIRMED from Google's own page** ([configure-mcp-server](https://developers.google.com/workspace/gmail/api/guides/configure-mcp-server)). The nine tools: `create_draft`, `get_thread`, `label_message`, `label_thread`, `list_drafts`, `list_labels`, `search_threads`, `unlabel_message`, `unlabel_thread`. The page says a created draft sits in the Drafts folder, "which lets you review and send it from Gmail". The scopes are `gmail.readonly` and `gmail.compose`. The earlier directory page said 10 tools; Google's page lists 9.
- **Gmail needs Google's Developer Preview Program: CONFIRMED** (the page names the program as a prerequisite). That is an enrolment step before we can connect at all. Also confirmed in Google's docs: a testing-mode app gets refresh tokens that expire in 7 days, and unverified apps with sensitive scopes are capped at 100 new users.
- **A quote worth using:** Google's Gmail MCP page tells integrators to "screen prompts and responses for malicious content or prompt injection attacks", with Google's Model Armor "or your own solution". The vendor's own documentation says the screening has to come from the integrator. Use it as written; don't paraphrase it into a claim that Google endorses Sentinel.

**Other confirmed points:** Slack's MCP server does not support SSE or dynamic client registration, and only Marketplace or internal apps can use it. Microsoft's Work IQ is delegated-only ("Application-only authentication isn't supported") and mutations are off by default, with the older Mail/Teams/SharePoint/OneDrive tools marked backward-compatibility only. Atlassian documents an API-token route for "non-interactive or machine-to-machine scenarios". Notion's hosted server advertises a single `default` scope, and its self-hosted repo says it is "no longer actively maintained or supported".

**Small mismatches in the sources table (not blockers):** the two GitHub security advisories carry later publication dates in GitHub's API (2026-07-28 and 2026-06-25) than the table says, and the API shows no patched-version field for either, so "fixed in version X" is not established.

**Unchanged recommendation:** GitHub first. The docs support a remote endpoint, a token with no browser step, a read-only switch and outbound write tools. Gmail is a second phase, now with two known prerequisites (the Preview Program and Google Cloud consent-screen setup), and with no send tool on Google's server the demo would be about drafts and read access unless we use a community server or Claude's own Gmail connector.

#### Update 2: second batch of sources checked (Linear, Supabase, filesystem, Composio, Arcade, Keycard)
Same method: fetch every cited page and test whether the quote is on it. **63 of 70 quotes found.** The seven that were not, and what each means:
- **Arcade pricing page:** the page is built in the browser, so the check is inconclusive. Not a contradiction.
- **Arcade PyPI `arcade-mcp-server` 1.33.0:** the page blocks scripts, but PyPI's JSON API confirms version 1.33.0 uploaded 2026-10-29. **Confirmed.**
- **Keycard revocation:** the page says "an outstanding short-lived token keeps working against the Resource until it expires". The table's quote is a paraphrase, not verbatim, but the claim is supported.
- **Filesystem server, `index.ts` (two quotes):** the code on `main` has changed since the table was made. The transport line is now `new StdioServerTransport(stdin, stdout)`, so it is still stdio, but the quoted line and the "Read File (Deprecated)" title are not in that file now. Pin a release tag instead of `main`.
- **Composio rate limits:** the page says limits apply "per organization over a fixed one-minute window". The table quotes a "rolling 10-minute window". **The quote is not on the page.** Composio's own pages disagree with each other, as the report hinted. Do not state a Composio rate limit.
- **Arcade changelog "MCP behavior annotations":** not found in the page text. Treat Arcade's annotation support as **unconfirmed**.

**Confirmed from vendors' own pages:**
- **Linear:** the official docs have the read-only endpoint `https://mcp.linear.app/mcp/readonly` ("only ever exposes read tools") and accept a Linear API key or OAuth token in `Authorization: Bearer`. My earlier "only a third-party page says this" is superseded. A live probe returns 401 with `WWW-Authenticate: Bearer ... scope="read write"`. API keys can be limited by permission (Read, Write, Admin, Create issues, Create comments) and to specific teams. MCP is listed as included on every plan.
- **Supabase:** v0.15.0 is the latest release (2026-10-29, confirmed via GitHub's API). In the vendor's source code, `execute_sql` and `apply_migration` are annotated `destructiveHint: true`, `readOnlyHint: false`. Without a project selected, "all projects will be accessible". Personal access tokens can be scoped to the tools their permissions unlock. A secret key "bypasses every Row Level Security policy". The Free plan gives two projects, paused after a week of inactivity, and Mumbai (`ap-south-1`) is a listed region.
- **The archived Postgres reference server** is archived (confirmed via GitHub's API), and Datadog's write-up reports a read-only bypass. The community alternative `crystaldba/postgres-mcp` is not archived, but its last tagged release is v0.3.0 from 16 May 2025.
- **Filesystem reference server:** the official repository README says it is "not as production-ready solutions"; the latest release of the repository is v2.2.0 (2026-10-28). The README lists "Create/list/delete directories", but no delete tool exists in the API list (`move_file` "Deletes source file"), which is the inconsistency the report flagged. A path-validation advisory from 2025 exists for older versions.
- **MCP spec:** the stdio spec, the "MUST validate the Origin header" rule for Streamable HTTP, "MUST NOT send tokens to the MCP server other than ones issued by the MCP server's authorization server" and "annotations should be considered untrusted" are all on the spec pages. The last two matter directly for a gateway that holds credentials.
- **Composio:** the May 2026 incident figures are on Composio's own bulletin; a secondary analysis says "exfiltrated" where Composio says "potentially exposed". Composio says its cloud runs in the United States, and the docs say per-call approval is experimental and that an `after_execute` hook "can't undo the tool call".
- **Arcade:** Arcade Cloud runs in the United States; remote MCP servers are tools-only ("Prompts, resources, and sampling are not supported yet"); its TypeScript repository was archived on 14 Oct 2026.
- **Keycard:** its CLI "does not enforce policy on each tool call", and policy is checked "every time it issues a credential"; for an MCP server it describes a fresh credential exchange per tool call. A revoked authorization does not kill a token already issued.

**What this means for the pitch (and where to be careful):**
- Keycard, Arcade and Composio decide **which identity and which scope** a call runs with. None of the pages you pasted describes a rule that follows where a value was read and where it is being sent, or that holds an action because the session read untrusted content. That is the gap Sentinel fills. Say "the pages I read do not describe", not "nobody does".
- These vendors **hold credentials**, and Composio's own incident shows what happens when one is breached. For the same reason Sentinel must treat its own credential store as a first-class risk (roadmap W9).
- The first batch's connectors plus Linear and Supabase give us four realistic first connectors. Updated order for one day of work: **GitHub, Linear, Supabase, then Gmail** (Preview Program and Cloud setup needed; no send tool).

---

## Prompt 2: client hooks

- Tool used:
- Date run:
- Status: (complete / partial / not run yet)
- What is missing, if partial:

### Raw report
<!-- paste below this line -->



### Sources
<!-- paste the sources table below this line -->



### Your notes



### Checked by Claude
<!-- leave empty -->

---

## Prompt 3: closed chat apps

- Tool used:
- Date run:
- Status: (complete / partial / not run yet)
- What is missing, if partial:

### Raw report
<!-- paste below this line -->



### Sources
<!-- paste the sources table below this line -->



### Your notes



### Checked by Claude
<!-- leave empty -->

---

## Decisions this research should feed
Filled in together after the reports are checked.

| Decision | Answer | Based on |
|---|---|---|
| Which real connector to wire up first (F2) | | Prompt 1 |
| Which clients get an enforced hook (F1) | | Prompt 2 |
| The sentence we can truthfully say about chat apps | | Prompt 3 |
