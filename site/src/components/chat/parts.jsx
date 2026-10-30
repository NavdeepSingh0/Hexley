// Pieces of the chat page that sit in the conversation: messages, the one-line tool summary, the slip and approval cards, the
// welcome screen. Everything shown comes from the ChatView the gateway builds; nothing here decides a decision.
import { FileCard } from './Composer.jsx'
import { Fragment } from 'react'
import { Icon } from '../Blocks.jsx'
import { decisionKind, decisionWord, ruleLabel, toolSummary } from '../../lib/chat.js'

// **bold** in a model's reply, as React text (never as HTML).
export function Inline({ text }) {
  return text.split('**').map((part, i) => (i % 2 ? <strong key={i}>{part}</strong> : <Fragment key={i}>{part}</Fragment>))
}

// A small cube-robot mark for the assistant's messages: the same face as the mascot, static and cheap.
export function Avatar() {
  return (
    <svg className="cx-avatar" width="28" height="28" viewBox="0 0 28 28" aria-hidden="true" focusable="false">
      <rect x="1" y="1" width="26" height="26" rx="9" fill="#fff" />
      <rect x="5" y="6" width="18" height="13" rx="5" fill="#0a0a10" />
      <path d="M11 10v5M17 10v5" stroke="#a98bff" strokeWidth="2.4" strokeLinecap="round" />
    </svg>
  )
}

export function Dots() {
  return <span className="cx-dots" role="status" aria-label="Working"><i /><i /><i /></span>
}

// One tool call: the decision word in its colour, what it was, a short preview; open it for the gateway's own sentence and rule.
export function Chip({ a }) {
  const kind = decisionKind(a.decision)
  return (
    <details className={`cx-chip cx-chip--${kind}`}>
      <summary>
        <span className="cx-chip-word">{decisionWord(a.decision)}</span>
        <span className="cx-chip-label">{a.label}</span>
        <span className="cx-chip-preview">{a.args_preview}</span>
      </summary>
      <div className="cx-chip-body">
        {a.reason && <p>{a.reason}</p>}
        {a.rules?.length > 0 && <p className="cx-chip-rules">{a.rules.map(ruleLabel).join(' · ')}</p>}
      </div>
    </details>
  )
}

// "Used 3 tools · 1 denied", closed by default (open while the answer is being written, or when something waits for the officer).
export function ToolGroup({ actions, live }) {
  const s = toolSummary(actions)
  const held = actions.some((a) => a.decision === 'NEEDS_APPROVAL')
  return (
    <details className="cx-tools" open={live || held}>
      <summary>
        <Icon name="chevron" size={14} className="cx-tools-chev" />
        <span className="cx-tools-label">{s.label}</span>
        {s.parts.map((p) => <span key={p.kind} className={`cx-tools-part cx-tools-part--${p.kind}`}>{p.text}</span>)}
      </summary>
      <ul className="cx-tools-list">{actions.map((a) => <li key={a.action_id}><Chip a={a} /></li>)}</ul>
    </details>
  )
}

export function Message({ m, working }) {
  if (m.role === 'user') {
    return (
      <div className="cx-turn cx-turn--user">
        <div className="cx-user">
          {m.attachments?.length > 0 && (
            <div className="cx-files cx-files--sent">{m.attachments.map((a) => <FileCard key={a.name} file={{ ...a, status: 'ready' }} />)}</div>
          )}
          <div className="cx-bubble"><Inline text={m.text} /></div>
        </div>
      </div>
    )
  }
  if (m.role === 'system') {
    return <div className="cx-turn"><p className="cx-system"><Inline text={m.text} /></p></div>
  }
  return (
    <div className="cx-turn cx-turn--assistant">
      <Avatar />
      <div className="cx-turn-body">
        {m.text ? <p className="cx-text"><Inline text={m.text} /></p> : working && <Dots />}
        {m.checks?.length > 0 && (
          <p className="cx-check" role="note">
            Hexley removed {m.checks.length === 1 ? 'an address' : `${m.checks.length} addresses`} from this reply before
            showing it: {m.checks.map((c) => `${c.kind} to ${c.host} (${c.reasons[0]})`).join('; ')}.
          </p>
        )}
        {m.actions?.length > 0 && <ToolGroup actions={m.actions} live={working} />}
      </div>
    </div>
  )
}

const facts = (slip) => (
  <dl className="cx-facts">
    <dt>May use</dt><dd>{slip.allowed_tools.map((t) => t.replace(/_/g, ' ')).join(', ')}</dd>
    <dt>May write to</dt><dd>{slip.allowed_destinations.join(', ') || 'nobody'}</dd>
    <dt>Message limit</dt><dd>{slip.max_messages}</dd>
  </dl>
)

// The first thing in a new chat: the permission slip, waiting for the officer.
export function SlipCard({ slip, busy, onConfirm }) {
  return (
    <div className="cx-card cx-slip">
      <p className="s-label">The permission slip</p>
      <p className="cx-slip-objective">{slip.objective}</p>
      {facts(slip)}
      <p className="muted cx-slip-note">Nothing runs until the officer confirms it.</p>
      <div><button type="button" className="s-btn s-btn--primary" onClick={onConfirm} disabled={busy}>Confirm as officer</button></div>
    </div>
  )
}

// After confirming, the slip folds into one quiet line that opens to the same facts.
export function SlipCompact({ slip }) {
  return (
    <details className="cx-slip-compact">
      <summary><Icon name="lock" size={15} /> <span>Permission slip confirmed</span><Icon name="chevron" size={14} className="cx-tools-chev" /></summary>
      <div className="cx-slip-compact-body"><p>{slip.objective}</p>{facts(slip)}</div>
    </details>
  )
}

export function ApprovalCard({ a, busy, onDecide }) {
  return (
    <div className="cx-card cx-approval" role="alert">
      <p className="cx-approval-word">NEEDS APPROVAL</p>
      <p className="cx-approval-what">{a.label}</p>
      <code className="cx-approval-args">{a.args_preview}</code>
      <p className="muted">{a.reason}</p>
      <div className="cx-approval-buttons">
        <button type="button" className="s-btn s-btn--primary" onClick={() => onDecide('approve')} disabled={busy}>Approve</button>
        <button type="button" className="s-btn s-btn--ghost" onClick={() => onDecide('deny')} disabled={busy}>Deny</button>
      </div>
    </div>
  )
}

// The empty state: the mascot, a question, and the four tasks as cards.
export function Welcome({ presets, busy, onPick, errorText }) {
  return (
    <div className="cx-welcome">
      <sentinel-mascot state="sleeping" message="" size="128" />
      <h1 className="cx-welcome-title">What should the agent do?</h1>
      <p className="cx-welcome-lede muted">Pick a task. A model works on it, every tool it calls goes through Hexley first, and you see each decision as it is made.</p>
      {errorText && <p className="muted cx-welcome-error" role="status">{errorText}</p>}
      <div className="cx-suggest">
        {presets.map((p) => (
          <button key={p.id} type="button" className="cx-suggest-card" onClick={() => onPick(p.id)} disabled={busy}>
            <span className="cx-suggest-title">{p.title}</span>
            <span className="cx-suggest-desc">{p.description}</span>
          </button>
        ))}
      </div>
    </div>
  )
}
