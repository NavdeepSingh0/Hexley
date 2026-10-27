# API contract (site ↔ backend)

The site calls these through `site/src/api/client.js`. Until a backend phase lands, the same shapes come from `site/src/mocks/` (`VITE_USE_MOCKS=1`). **If a field you need is missing, ask; never invent one.** Status of each endpoint: *planned* until the named core phase passes.

## Conventions
- New endpoints live under `/api/v1/`. Existing endpoints used by the console (`/runs`, `/audit/*`, `/approvals/*`, `/scenarios`, `/recordings`) keep their paths.
- **Auth:** `Authorization: Bearer <API token>` on every call. The token reaches the browser once in the URL fragment (`#token=…`), is moved to `sessionStorage['sentinel.token']` and removed from the address bar. Never log or display it.
- Errors: HTTP status + JSON `{"detail": "plain-English message"}`. Show `detail` to the user.
- Times are ISO 8601 UTC strings; durations are seconds.
- Decision words are always one of `ALLOWED`, `DENIED`, `NEEDS_APPROVAL`, `QUARANTINED`, `PENDING` (display with spaces: "NEEDS APPROVAL").

## Connect (core phase B1, B8)
`GET /api/v1/connect`
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
`public_url` is `null` when Sentinel runs locally only (no tunnel). `status` ∈ `tested | should_work | planned`; only `tested` may carry a `screenshot`. `snippet` placeholders: `{mcp_url}`, `{header_value}`.

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
- `POST /api/v1/chat` body `{"preset": "quotation"}` → **ChatView** (status `awaiting_confirmation`)
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
`retry` is `{"attempt": 2, "waiting_s": 8}` while `status` is `model_busy`. `role` ∈ `user | assistant | system`.

## Evidence (core phase B8)
Static file `site/public/evidence.json`, generated from `eval/results/` by `scripts/export_evidence.py`. The site never types a number.
```json
[{"label": "Disguised leaks that got past Sentinel", "value": "0 of 31", "n": 31, "ci95": [0.0, 0.11],
  "source_file": "eval/results/scripted-20261026T185710.json",
  "caveat": "Cases written from the matcher's own documented list; shows it does what we say, not that nothing else gets through."}]
```

## Mascot state (core phase B7)
`GET /api/v1/mascot/state` → `{"state": "denied", "message": "…", "session_id": "ses_…", "ts": "…"}` (latest event of the most recent active session; `sleeping` when none). Used by the browser extension.
