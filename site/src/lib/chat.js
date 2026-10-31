// Pure helpers for the chat page. What the page shows comes from the ChatView the gateway builds (docs/contracts/API.md);
// nothing here decides a decision, a rule or a sentence.
import { RULES } from '../data/rules.js'

// How often to ask for the view: quickly while an answer is being written, slowly when nothing is moving, never when
// the chat is over.
export function pollDelay(status) {
  if (status === 'thinking' || status === 'model_busy') return 700
  if (status === 'ready' || status === 'awaiting_confirmation') return 2500
  return null // quarantined, ended
}

export const DECISION_WORD = { ALLOWED: 'ALLOWED', DENIED: 'DENIED', NEEDS_APPROVAL: 'NEEDS APPROVAL', QUARANTINED: 'QUARANTINED', PENDING: 'CHECKING' }
export const DECISION_KIND = { ALLOWED: 'allowed', DENIED: 'denied', NEEDS_APPROVAL: 'approval', QUARANTINED: 'quarantined', PENDING: 'pending' }

export function decisionWord(decision) {
  return DECISION_WORD[decision] ?? String(decision).replace(/_/g, ' ')
}

export function decisionKind(decision) {
  return DECISION_KIND[decision] ?? 'pending'
}

export function allActions(view) {
  return (view?.messages ?? []).flatMap((m) => m.actions ?? [])
}

// The first action waiting for the officer, if any: the approval card shows it.
export function pendingApproval(view) {
  return allActions(view).find((a) => a.decision === 'NEEDS_APPROVAL' && a.approval_id) ?? null
}

// "R2: Restricted data stays in" for a rule id, or the id alone if it is not one of the nine.
export function ruleLabel(id) {
  const r = RULES.find((x) => x.id === id)
  return r ? `${r.id}: ${r.title}` : String(id)
}

// Why the composer is closed, or '' when a message can be sent now.
export function composerBlock(view) {
  if (!view) return 'Pick a task on the left to start.'
  switch (view.status) {
    case 'awaiting_confirmation': return 'The officer must confirm the permission slip first.'
    case 'thinking': return 'Waiting for the answer...'
    case 'model_busy': return 'The model is busy. Trying again...'
    case 'quarantined': return 'This session is quarantined. Start a new chat.'
    case 'ended': return 'The permission slip has expired. Start a new chat.'
    default: return ''
  }
}

// One line about the model while it is slow: attempt and the wait, or ''.
export function busyLine(view) {
  if (view?.status !== 'model_busy' || !view.retry) return ''
  const s = Math.max(0, Math.round(view.retry.waiting_s))
  return `The model is busy. Trying again (attempt ${view.retry.attempt}${s > 0 ? `, about ${s} s` : ''}).`
}

export const MODES = [
  ['auto', 'Nemotron'],
  ['local', 'Local model (Ollama, on this computer)'],
  ['replay', 'Recorded real chat'],
  ['scripted', 'Scripted attacker (no model)'],
]

// A model on this computer is no use to someone on the hosted site.
export const modesFor = (hostname) => MODES.filter(([id]) => id !== 'local' || hostname === '127.0.0.1' || hostname === 'localhost')

// A new chat with no task chosen uses the general slip. The rest are offered as suggestions; a real connector is offered as a switch.
export const GENERAL_PRESET = 'own-doc'
export const suggestions = (presets) => (presets ?? []).filter((p) => p.id !== GENERAL_PRESET && !p.connector)

// The disclosure shown before the server has sent one (it is never absent).
export const DEFAULT_DISCLOSURE = 'Hexley Chat is our own demo host app. Every record and mailbox is synthetic and the tools are mocks.'

// ---- the chat page the way a frontier chat shows it (UI v2, U3) -------------------------------------------------------------

// One line over an assistant message's tool calls: "Used 3 tools" and, in their decision colours, how many were denied,
// held, quarantined or still being checked. Nothing here decides anything; it counts the decisions the gateway made.
export function toolSummary(actions) {
  const list = actions ?? []
  const n = list.length
  const count = (d) => list.filter((a) => a.decision === d).length
  const parts = [
    ['denied', count('DENIED'), (k) => `${k} denied`],
    ['approval', count('NEEDS_APPROVAL'), (k) => `${k} waiting for the officer`],
    ['quarantined', count('QUARANTINED'), (k) => `${k} quarantined`],
    ['pending', count('PENDING'), (k) => `${k} being checked`],
  ].filter(([, k]) => k > 0).map(([kind, k, text]) => ({ kind, text: text(k) }))
  return { n, label: n === 1 ? 'Used 1 tool' : `Used ${n} tools`, parts }
}

const clock = (iso) => {
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? '' : d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

// The small chip in the header: what state the conversation is in, in words. `kind` is only for styling, and only
// quarantine gets a loud one (decision colours are never used for anything but a decision).
export function statusChip(view) {
  if (!view) return null
  switch (view.status) {
    case 'awaiting_confirmation': return { kind: 'wait', text: 'Waiting for the officer' }
    case 'thinking': return { kind: 'busy', text: 'Working' }
    case 'model_busy': return { kind: 'busy', text: 'Model busy, trying again' }
    case 'quarantined': return { kind: 'quarantined', text: 'Quarantined' }
    case 'ended': return { kind: 'ended', text: 'Slip expired' }
    default: {
      const until = clock(view.slip?.expires_at)
      return { kind: 'ok', text: until ? `Slip confirmed until ${until}` : 'Slip confirmed' }
    }
  }
}

// A conversation's title: the task it was started from, else a plain default.
export const chatTitle = (preset, view) => view?.title || preset?.title || view?.preset || 'New chat'

// "just now", "5 min ago", "2 h ago", "3 d ago"
export function ago(ts, now = Date.now()) {
  const s = Math.max(0, Math.round((now - ts) / 1000))
  if (s < 45) return 'just now'
  if (s < 3600) return `${Math.max(1, Math.round(s / 60))} min ago`
  if (s < 86400) return `${Math.round(s / 3600)} h ago`
  return `${Math.round(s / 86400)} d ago`
}
