# API contract (site ↔ backend)

The site calls these through `site/src/api/client.js`. Until a backend phase lands, the same shapes come from `site/src/mocks/` (`VITE_USE_MOCKS=1`). **If a field you need is missing, ask; never invent one.** Status of each endpoint: *planned* until the named core phase passes.

## Conventions
- New endpoints live under `/api/v1/`. Existing endpoints used by the console (`/runs`, `/audit/*`, `/approvals/*`, `/scenarios`, `/recordings`) keep their paths.
- **Auth:** `Authorization: Bearer <API token>` on every call. The token reaches the browser once in the URL fragment (`#token=…`), is moved to `sessionStorage['sentinel.token']` and removed from the address bar. Never log or display it.
- Errors: HTTP status + JSON `{"detail": "plain-English message"}`. Show `detail` to the user.
- Times are ISO 8601 UTC strings; durations are seconds.
- Decision words are always one of `ALLOWED`, `DENIED`, `NEEDS_APPROVAL`, `QUARANTINED`, `PENDING` (display with spaces: "NEEDS APPROVAL").

## Connect (core phase B1, B8)
`GET /api/v1/connect` (public)
```json
{
  "public_url": "https://example.trycloudflare.com",
  "mcp_url": "https://example.trycloudflare.com/mcp",
  "methods": [
    {"id": "oauth", "status": "tested", "steps": ["Open Customize → Connectors → Add custom connector", "Paste the URL", "Choose “Sign in now”", "Approve the permission slip with the officer code"]},
    {"id": "header", "status": "tested", "steps": ["Create a slip and token below", "Add a header Authorization with the value shown"]}
  ],
  "clients": [
    {"id": "claude-web", "name": "Claude.ai (web)", "kind": "web", "status": "tested", "method": "oauth", "snippet": null, "screenshot": "/img/real-claude-blocked-by-sentinel.png"},
    {"id": "claude-code", "name": "Claude Code", "kind": "cli", "status": "should_work", "method": "header", "snippet": "claude mcp add --transport http sentinel {mcp_url} --header \"Authorization: {header_value}\"", "screenshot": null}
  ]
}
```
(Claude.ai is `tested` by the OAuth route: a free account, 27 Oct 2026. The header route is `tested` by Claude Code: a real session, 29 Oct 2026, D-044. VS Code is `should_work`.) A `tested` client carries evidence: `screenshot` (an image path) or `transcript` (`{"url": "/proof/…txt", "caption": "…"}`, a captured session as text); both are `null` for any other status. `GET /api/v1/connect` needs no token (it holds no secret); `POST /api/v1/connect/token` does. `public_url` is `null` when Sentinel runs locally only (no tunnel). `status` ∈ `tested | should_work | planned`; only `tested` may carry a `screenshot`. `snippet` placeholders: `{mcp_url}`, `{header_value}`.

`POST /api/v1/connect/token` body `{"preset": "quotation_processing"}` → officer action
```json
{"header_value": "Bearer eyJ…", "expires_at": "2026-10-30T10:15:00Z", "slip": {"objective": "…", "allowed_tools": ["…"], "allowed_destinations": ["…"], "max_messages": 1}}
```

## OAuth consent (core phase B1)
`GET /api/v1/oauth/requests/{id}`
```json
{"request_id": "oar_…", "client_name": "Claude", "expires_in": 280,
 "slip": {"objective": "…", "allowed_tools": ["read_quotation", "query_stock", "send_email"], "allowed_destinations": ["shakti.example"], "max_messages": 1, "ttl_seconds": 900}}
```
`POST /api/v1/oauth/requests/{id}` body `{"decision": "approve" | "deny", "officer_code": "123456"}` → `{"redirect_to": "https://claude.ai/…"}`. Errors: `403` wrong officer code (may retry), `410` expired, `404` unknown request.

## Sentinel Chat (core phase B5)
- `GET /api/v1/chat/presets` → `[{"id": "quotation", "title": "Process a vendor quotation", "prompt": "…", "description": "…"}]`
- `POST /api/v1/chat` body `{"preset": "quotation", "mode": "auto"}` → **ChatView** (status `awaiting_confirmation`), `201`. `mode` is optional: `auto` (default: a live model when an NVIDIA key is configured, otherwise a scripted agent), `live` (`400` with a plain message if no key), `scripted` (a fixed sequence of calls for the preset's attack, no model) or `replay` (the model replies of an earlier real chat, returned in order; Sentinel's decisions are still computed live). For `replay` the body may carry `"recording": {...}` (the export below); without it the newest committed `recordings/chat/<preset>-*.json` is used (`404` if there is none). `officer` is optional (default "Col. R. Menon"). Presets: `quotation`, `own-pdf`, `poisoned-web`, `bank-change`.
- `GET /api/v1/chat/{id}/recording` → `{"schema": "sentinel.chat-recording/1", "model", "preset", "recorded_at", "messages": [the model's own messages]}`: an export that can be committed under `recordings/chat/` or posted back with `mode: replay`.
- `POST /api/v1/chat/{id}/confirm` → **ChatView** (status `ready`)
- `POST /api/v1/chat/{id}/messages` body `{"text": "…"}` → `202 {"message_id": "msg_…"}`
- `GET /api/v1/chat/{id}` → **ChatView**. Poll every 700 ms while `thinking` or `model_busy`, otherwise every 2.5 s.
- Approvals: existing `POST /approvals/{approval_id}` body `{"decision": "approve" | "deny"}`.

**ChatView**
```json
{
  "chat_id": "chat_…",
  "status": "awaiting_confirmation | ready | thinking | model_busy | quarantined | ended",
  "disclosure": "Sentinel Chat (our demo host) · model: nvidia/nemotron-3-ultra-550b-a55b via NVIDIA API · synthetic data, mock tools",
  "model": "nvidia/nemotron-3-ultra-550b-a55b",
  "slip": {"objective": "…", "allowed_tools": ["…"], "allowed_destinations": ["…"], "max_messages": 1, "expires_at": "…"},
  "messages": [
    {"id": "msg_1", "role": "user", "text": "…", "ts": "…", "actions": []},
    {"id": "msg_2", "role": "assistant", "text": "…", "ts": "…", "actions": [
      {"action_id": "act_…", "tool": "send_email", "label": "Send an e-mail", "args_preview": "to sales@shakti.example: “Dear …”",
       "decision": "DENIED", "rules": ["R2"], "reason": "Restricted data (quantity, depot code) would have left the building.", "approval_id": null}
    ]}
  ],
  "mascot": {"state": "denied", "message": "That would send restricted data out."},
  "retry": null
}
```
`retry` is `{"attempt": 2, "waiting_s": 8}` while `status` is `model_busy` (the model client is waiting on a rate limit, a resting key or a backoff). `role` ∈ `user | assistant | system` (a `system` message is the host saying the model could not be reached; it has no actions). The view also carries `mode` (`live | scripted | replay`) and `preset`. Everything on it is built from gateway events: each action's `decision`, `rules` and `reason` are the gateway's own `decision` event (the host adds no words), the `mascot` is a pure function of the session's events (the table in `MASCOT.md`; while the model is waiting it is `idle` with "The model is busy; trying again."), and `status` is `quarantined` once the session is frozen and `ended` once the slip has expired. Errors: `404` unknown preset or chat, `409` message before the officer confirmed the slip, while an answer is being written, or after quarantine, `410` slip expired, `422` empty or over-long text (2000 characters), `429` more than 30 messages in one chat. All chat routes need the officer token. A held action (`NEEDS_APPROVAL`) carries its `approval_id`; the chat waits until the officer resolves it with `POST /approvals/{id}`.

## Tools and slips for any task (core phase B2, built)
All of these need the API token (officer actions).

`GET /api/v1/tools` lists every tool the tool server offers and whether Sentinel has classified it. An unclassified tool is invisible to agents and refused by R1 until the officer classifies it.
```json
{"tools": [
  {"name": "read_quotation", "description": "…", "arguments": ["quote_id"], "classified": true, "builtin": true,
   "labels": {"capability": "read", "resource_class": "quotation_doc", "outbound": false, "consequential": false,
              "output_integrity": "untrusted", "output_confidentiality": "internal", "fingerprint_fields": [],
              "destination_args": [], "destination_kind": "email", "requires_human_verification": false}, "suggested": null},
  {"name": "delete_records", "description": "…", "arguments": ["table"], "classified": false, "builtin": false, "labels": null,
   "suggested": {"capability": "write", "consequential": true, "outbound": false, "reasons": ["the name or description suggests it changes something"]}}
 ], "unclassified": 1}
```
`suggested` is a first guess for the officer to review; it is never applied automatically.

`POST /api/v1/tools/{name}/classify` body: `capability` (`read|write|send`), `outbound`, `consequential`, `output_integrity` (`trusted|untrusted`), `output_confidentiality` (`public|internal|restricted`), optional `resource_class`, `fingerprint_fields` (`["all"]` or any of `quantity, depot_code, dispatch_date, number, date, email, phone, account, id, text`), `destination_args`, `destination_kind` (`email|url|path`), `requires_human_verification`. Returns `{name, classified: true, labels}`. Errors: `404` unknown tool, `409` built-in tool, `422` an invalid label (an outbound tool must name its destination argument), `503` audit log unavailable (nothing is saved without a durable record).

`POST /api/v1/slips` body: `objective` (5 to 500 characters), `allowed_tools`, `allowed_destinations` (domains, `path:/folder`), `internal_destinations` (domains, addresses or paths, a subset of the allowed ones: restricted data may go there and R7 does not ask), `max_messages` (0 to 50, default 1), `ttl_seconds` (60 to 86400, default 900), optional `confirm: true`. Returns `{contract_id, contract_hash, slip, confirmed}`; with `confirm: true` also `session_id`, `header_value`, `expires_at`. Without `confirm`, confirm with `POST /tasks/{contract_id}/confirm`. Refused with `422` and a plain message when a tool is unclassified or built in, an outbound tool has no destination or no message budget, or an entry is vague (wildcards, web addresses with paths).

## Evidence (core phase B8)
Static file `site/public/evidence.json`, generated from `eval/results/` by `scripts/export_evidence.py`. The site never types a number.
```json
[{"label": "Disguised leaks that got past Sentinel", "value": "0 of 31", "n": 31, "ci95": [0.0, 0.11],
  "source_file": "eval/results/scripted-20261026T185710.json",
  "caveat": "Cases written from the matcher's own documented list; shows it does what we say, not that nothing else gets through."}]
```

## Mascot state (core phase B7)
`GET /api/v1/mascot/state` → `{"state": "denied", "message": "…", "session_id": "ses_…", "ts": "…"}` (latest event of the most recent active session; `sleeping` when none). Used by the browser extension.
