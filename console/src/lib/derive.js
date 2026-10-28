// Pure functions that turn a backend run view into what the screen says.
// Nothing here invents data: every claim is computed from fields the gateway and the mail sink produced.

export const TOOL_LABEL = {
  read_quotation: "Read the vendor's quotation",
  query_stock: 'Checked the stock register',
  send_email: 'Sent an e-mail',
  send_quote_ack: "Asked Sentinel to send its fixed acknowledgement",
  update_vendor_bank: "Changed the vendor's bank account",
  delete_records: 'Tried to delete records',
  list_documents: 'Listed the documents',
  read_document: 'Read a document',
  query_db: 'Queried the customer database',
  fetch_url: 'Fetched a web page',
  http_post: 'Posted to a web address',
  write_file: 'Wrote a file',
  run_command: 'Tried to run a command',
}

// The same tools, worded as permissions (the slip says what the agent MAY do; the timeline says what it DID).
export const TOOL_ALLOWS = {
  read_quotation: "Read the vendor's quotation",
  query_stock: 'Check the stock register',
  send_email: 'Send an e-mail',
  send_quote_ack: "Send Sentinel's fixed acknowledgement",
  update_vendor_bank: "Change a vendor's bank account",
  list_documents: 'List documents',
  read_document: 'Read documents',
  query_db: 'Query the customer database',
  fetch_url: 'Fetch web pages',
  http_post: 'Post to a web address',
  write_file: 'Write files',
  run_command: 'Run commands (the officer must approve each)',
}

export const RULE_LABEL = {
  R1: 'Not allowed by the permission slip',
  R2: 'Secret data leaving the building',
  R3: 'Reply address came from an untrusted document',
  R4: 'Needs the officer',
  R5: 'Message limit reached',
  R6: 'Too many blocked attempts',
  R7: 'Needs the officer after reading untrusted content',
}

const truncate = (s, n) => (s.length > n ? s.slice(0, n - 1) + '…' : s)

export function laneCounts(lane) {
  const steps = lane.steps || []
  return {
    calls: steps.length,
    allowed: steps.filter((s) => s.effect === 'ALLOW').length,
    stopped: steps.filter((s) => s.effect === 'BLOCK').length,
    frozen: steps.filter((s) => s.effect === 'FREEZE').length,
  }
}

// Changes to a vendor's bank account that actually ran (an `action.completed` event exists for the call).
export function bankChanges(lane) {
  return (lane.steps || [])
    .filter((s) => s.tool === 'update_vendor_bank' && s.completed)
    .map((s) => ({ account: s.args.account_number, vendor: s.args.vendor, approved: s.approval?.status === 'approved' }))
}

// A delivered message, as the audience should read it.
export function inboxRowView(row, contract) {
  const registered = contract?.resolved_vendor?.email?.toLowerCase()
  const misdirected = Boolean(registered) && row.to.toLowerCase() !== registered
  return { leak: Boolean(row.oracle_leak), misdirected, clean: !row.oracle_leak && !misdirected }
}

export function laneHeadline(lane) {
  const rows = (lane.inbox || []).map((r) => ({ r, v: inboxRowView(r, lane.contract) }))
  const leaked = rows.some((x) => x.v.leak)
  const misdirected = rows.some((x) => x.v.misdirected)
  const banks = bankChanges(lane)
  const isSentinel = lane.column === 'sentinel'

  if (lane.status !== 'finished') {
    if ((lane.approvals || []).length) return { tone: 'waiting', text: 'WAITING FOR THE OFFICER' }
    if (lane.freeze) return { tone: 'frozen', text: 'FROZEN' }
    return { tone: 'running', text: 'Working…' }
  }
  if (lane.outcome === 'diverged') {
    return { tone: 'error', text: 'REPLAY STOPPED: the live decision differed from the recording' }
  }
  if (leaked) return { tone: 'leak', text: 'LEAKED: restricted data reached the outside' }
  if (misdirected) return { tone: 'leak', text: "SENT TO THE WRONG ADDRESS: the reply went where the document said" }
  if (banks.length && !isSentinel) {
    return { tone: 'leak', text: `BANK ACCOUNT CHANGED to ${banks[0].account}: nobody was asked` }
  }
  if (banks.length && isSentinel) return { tone: 'sent', text: 'CHANGED: only after the officer approved' }
  if (lane.outcome === 'frozen') {
    return { tone: 'frozen', text: `FROZEN: agent quarantined after ${lane.blocks} blocked attempts` }
  }
  const triedBank = (lane.steps || []).some((s) => s.tool === 'update_vendor_bank')
  if (lane.outcome === 'contained') {
    return { tone: 'stopped', text: triedBank ? 'STOPPED: the change was not made' : 'STOPPED: nothing left the building' }
  }
  if (lane.outcome === 'recovered') {
    return { tone: 'stopped', text: 'STOPPED, then only a clean message was sent' }
  }
  if (lane.outcome === 'agent_error') return { tone: 'error', text: 'The agent stopped with an error' }
  if (rows.length) return { tone: 'sent', text: 'SENT: clean message only' }
  return { tone: 'neutral', text: 'Finished' }
}

// The small stamp on each step. ALLOW is deliberately neutral: allowed is not the same as good.
export function stepStamp(step) {
  switch (step.effect) {
    case 'ALLOW': {
      const unevaluated = step.reason_code === 'NOT_ENFORCED'
      const approved = (step.evidence || []).some((e) => e.kind === 'approval')
      return {
        kind: 'allowed',
        label: unevaluated ? 'allowed · no policy evaluated' : approved ? 'allowed · officer approved' : 'allowed',
      }
    }
    case 'BLOCK':
      return { kind: 'stopped', label: `STOPPED · ${(step.rule_ids || []).join(' + ')}` }
    case 'FREEZE':
      return { kind: 'frozen', label: `FROZEN · ${(step.rule_ids || []).join(' + ')}` }
    case 'ASK':
      return { kind: 'waiting', label: 'WAITING FOR THE OFFICER' }
    default:
      return { kind: 'pending', label: 'deciding…' }
  }
}

export function shortArgs(step) {
  const a = step.args || {}
  switch (step.tool) {
    case 'read_quotation':
      return `quotation ${a.quote_id}`
    case 'query_stock':
      return 'stock register (all items)'
    case 'send_email':
      return `to ${a.to} — “${truncate(String(a.body ?? ''), 90)}”`
    case 'update_vendor_bank':
      return `${a.vendor} → account ${a.account_number}`
    case 'list_documents':
      return `folder ${a.folder ?? 'reports'}`
    case 'read_document':
      return `document ${a.path}`
    case 'query_db':
      return `SQL: ${truncate(String(a.sql ?? ''), 70)}`
    case 'fetch_url':
      return `page ${a.url}`
    case 'http_post':
      return `to ${a.url} — “${truncate(String(a.body ?? ''), 80)}”`
    case 'write_file':
      return `file ${a.path} — “${truncate(String(a.content ?? ''), 60)}”`
    case 'run_command':
      return `command ${truncate(String(a.command ?? ''), 80)}`
    default:
      return truncate(JSON.stringify(a), 100)
  }
}

// Slips that are identical across lanes are shown once ("issued identically to ...").
export function groupSlips(lanes) {
  const groups = new Map()
  for (const lane of lanes) {
    const c = lane.contract
    const key = JSON.stringify([c.objective, c.allowed_tools, c.allowed_recipient_domains, c.mode, c.work_item_id,
      c.resolved_vendor, c.max_messages])
    if (!groups.has(key)) groups.set(key, { contract: c, columns: [], titles: [] })
    const g = groups.get(key)
    g.columns.push(lane.column)
    g.titles.push(lane.badge ? `${lane.title} (${lane.badge})` : lane.title)
  }
  return [...groups.values()]
}

// Split `text` so that each matched token is marked. Exact case-insensitive substrings only: if a token is not
// found as such (the matcher also recognises "two thousand four hundred" for 2400), it is listed, never invented.
export function highlightTokens(text, tokens) {
  const lower = text.toLowerCase()
  const spans = []
  const unlocated = []
  for (const t of tokens || []) {
    if (!t) continue
    const needle = t.toLowerCase()
    let from = 0
    let found = false
    for (;;) {
      const i = lower.indexOf(needle, from)
      if (i < 0) break
      spans.push([i, i + needle.length])
      found = true
      from = i + needle.length
    }
    if (!found && !unlocated.includes(t)) unlocated.push(t)
  }
  spans.sort((a, b) => a[0] - b[0])
  const merged = []
  for (const s of spans) {
    const last = merged[merged.length - 1]
    if (last && s[0] <= last[1]) last[1] = Math.max(last[1], s[1])
    else merged.push([...s])
  }
  const segments = []
  let pos = 0
  for (const [a, b] of merged) {
    if (a > pos) segments.push({ text: text.slice(pos, a), hit: false })
    segments.push({ text: text.slice(a, b), hit: true })
    pos = b
  }
  if (pos < text.length) segments.push({ text: text.slice(pos), hit: false })
  return { segments: segments.length ? segments : [{ text, hit: false }], unlocated }
}

// Links between steps, ONLY where the matcher or R3 recorded where the value came from in its evidence.
// The evidence names the exact call (`source_action_id`) whenever the gateway knew it, so two documents read with the same
// tool are two different sources and the arrow points at the right one. Recordings made before that field existed only name
// the tool, and for those the earliest earlier completed call of that tool is used (the old, less precise behaviour).
// Baseline lanes evaluate no data flow, so they never get any.
export function chainLinks(lane) {
  if (lane.column !== 'sentinel') return []
  const steps = lane.steps || []
  const links = []
  steps.forEach((step, to) => {
    if (step.effect !== 'BLOCK' && step.effect !== 'FREEZE') return
    const seen = new Set()
    for (const e of step.evidence || []) {
      if (e.kind !== 'fingerprint' && e.kind !== 'provenance') continue
      const from = e.source_action_id
        ? steps.findIndex((s) => s.action_id === e.source_action_id && s.completed)
        : steps.findIndex((s, i) => i < to && s.tool === e.source_ref && s.completed)
      if (from < 0 || from >= to || seen.has(from)) continue
      seen.add(from)
      links.push({ from, to, source: e.source_ref })
    }
  })
  return links
}

export function firstBlockedStep(lane) {
  const i = (lane.steps || []).findIndex((s) => s.effect === 'BLOCK' || s.effect === 'FREEZE')
  return i < 0 ? null : { index: i, step: lane.steps[i] }
}

// Prefer the earliest attempt in which no lane ended in an error or a divergence; otherwise the earliest.
export function pickDefaultRecording(recordings, scenario) {
  const mine = (recordings || []).filter((r) => r.scenario === scenario).sort((a, b) => a.attempt - b.attempt)
  const clean = mine.find((r) => r.lanes.every((l) => l.outcome !== 'agent_error' && l.outcome !== 'diverged'))
  return clean || mine[0] || null
}

// What Enter does next. Pure, so the presenter's flow can be tested without a browser.
export function presenterNext({ screen, runStatus, verdictOpen, hasVerdict, playlistIndex, playlistLength }) {
  if (screen === 'start') return playlistIndex < playlistLength ? 'create' : 'done'
  if (screen === 'slip') return 'confirm'
  if (screen === 'stage') {
    if (runStatus !== 'finished') return 'wait'
    if (verdictOpen) return 'close-and-next'
    return hasVerdict ? 'open-verdict' : 'next'
  }
  return 'wait'
}

export function verifyView(v) {
  if (!v) return { tone: 'idle', text: 'Not checked yet' }
  if (v.ok) return { tone: 'ok', text: `Chain intact · ${v.checked} records` }
  return { tone: 'bad', text: `TAMPERED at record #${v.first_bad_seq}: ${v.reason}` }
}
