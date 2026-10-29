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

// "R2: Restricted data stays in" for a rule id, or the id alone if it is not one of the seven.
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
  ['auto', 'Automatic'],
  ['live', 'Live model'],
  ['replay', 'Recorded real chat'],
  ['scripted', 'Scripted attacker (no model)'],
]

// The disclosure shown before the server has sent one (it is never absent).
export const DEFAULT_DISCLOSURE = 'Sentinel Chat is our own demo host app. Every record and mailbox is synthetic and the tools are mocks.'
