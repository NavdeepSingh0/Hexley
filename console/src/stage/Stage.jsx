import {
  TOOL_LABEL, RULE_LABEL, bankChanges, highlightTokens, inboxRowView, laneCaption, laneCountLine, laneLabel,
  laneVerdict, shortArgs, stepStamp,
} from '../lib/derive.js'

// Values that Sentinel's matcher identified as restricted anywhere in this run. Used only to mark them in delivered mail.
export function restrictedTokens(view) {
  const out = new Set()
  for (const lane of view.lanes) {
    for (const s of lane.steps || []) {
      for (const e of s.evidence || []) if (e.kind === 'fingerprint') (e.matched_tokens || []).forEach((t) => out.add(t))
    }
  }
  return [...out]
}

function Marked({ text, tokens }) {
  const { segments } = highlightTokens(text, tokens)
  return segments.map((s, i) => (s.hit ? <mark key={i}>{s.text}</mark> : <span key={i}>{s.text}</span>))
}

// The colour class for a verdict word. Quiet kinds (neutral, running, error) stay uncoloured: colour means a decision.
const VERDICT_CLASS = {
  allowed: 's-verdict--allowed', denied: 's-verdict--denied', approval: 's-verdict--approval', harm: 's-verdict--harm',
  quarantined: 's-verdict--quarantined', running: 's-verdict--muted', error: 's-verdict--muted', neutral: '',
}
// Glow goes on the one decisive word on the screen: the last lane (Sentinel, or the hardened lane), when it holds a decision.
// An approval is decided in the modal, which carries the glow then; the inverted QUARANTINED block is loud enough without one.
const GLOWS = new Set(['allowed', 'denied'])

// One step of a lane, as listed in the steps drawer.
export function StepCard({ step, index, isSentinel, onWhy }) {
  const stamp = stepStamp(step)
  const blocked = step.effect === 'BLOCK' || step.effect === 'FREEZE'
  return (
    <li className={`step step-${stamp.kind}`}>
      <div className="step-top">
        <span className="step-tool">{TOOL_LABEL[step.tool] ?? step.tool}</span>
        <span className={`stamp stamp-${stamp.kind}`}>{stamp.label}</span>
      </div>
      <div className="step-args">{shortArgs(step)}</div>
      {blocked ? (
        <div className="step-why">
          <span>{(step.rule_ids || []).map((r) => RULE_LABEL[r] ?? r).join(' · ')}</span>
          {isSentinel && onWhy ? <button className="s-btn s-btn--ghost s-btn--small" onClick={() => onWhy(index)}>Why?</button> : null}
        </div>
      ) : null}
      {isSentinel && blocked && step.latency_ms != null ? (
        <div className="step-meta">Sentinel decision (live) in {step.latency_ms < 0.1 ? '<0.1' : step.latency_ms.toFixed(1)} ms</div>
      ) : null}
    </li>
  )
}

// What actually reached the outside (the mail sink), or what changed in the vendor master.
export function Effects({ lane, view, tokens }) {
  const banks = bankChanges(lane)
  if (view.scenario.id === 'bank_change') {
    return (
      <div className="effects">
        <p className="s-label">What changed in the vendor master</p>
        {banks.length ? banks.map((b, i) => (
          <div key={i} className={`effect-row ${b.approved ? 'effect-ok' : 'effect-bad'}`}>
            Bank account of <b>{b.vendor}</b> → <b>{b.account}</b>
            <div className="effect-sub">{b.approved ? 'approved by the officer' : 'nobody was asked'}</div>
          </div>
        )) : <p className="effect-empty">No change was made.</p>}
      </div>
    )
  }
  if (view.inbox_ok === false) {
    return <div className="effects"><p className="effect-empty">The vendor&rsquo;s inbox could not be read: do not treat this lane as &ldquo;nothing leaked&rdquo;.</p></div>
  }
  const rows = lane.inbox || []
  return (
    <div className="effects">
      <p className="s-label">What reached the outside</p>
      {rows.length === 0 ? <p className="effect-empty">Nothing was delivered.</p> : rows.map((r, i) => {
        const v = inboxRowView(r, lane.contract)
        const registered = lane.contract?.resolved_vendor?.email
        return (
          <div key={i} className={`mail ${v.leak ? 'mail-leak' : v.misdirected ? 'mail-wrong' : 'mail-clean'}`}>
            <div className="mail-head">To <b>{r.to}</b></div>
            <div className="mail-body"><Marked text={r.body} tokens={v.leak ? tokens : []} /></div>
            <div className="mail-flag">
              {v.leak ? 'Restricted data delivered (measured by the evaluation oracle)'
                : v.misdirected ? `Not the registered vendor address (${registered})`
                : 'Clean message: no restricted data (evaluation oracle)'}
            </div>
          </div>
        )
      })}
    </div>
  )
}

// A lane is a calm card: its name, one verdict word, one sentence, the count, and a way to see the steps. It never grows.
function Lane({ lane, view, decisive, onSteps }) {
  const verdict = laneVerdict(lane, view.scenario.id)
  const glow = decisive && GLOWS.has(verdict.kind)
  return (
    <section className={`lane s-panel${decisive ? ' is-active' : ''}`} aria-label={laneLabel(lane, view.scenario.id)}>
      <header>
        <p className="s-label">{laneLabel(lane, view.scenario.id)}</p>
        <p className="lane-caption">{laneCaption(lane, view)}</p>
      </header>
      <p className={`s-verdict ${VERDICT_CLASS[verdict.kind]}${glow ? ` s-glow s-glow--${verdict.kind}` : ''}`} role="status">{verdict.word}</p>
      <p className="lane-sentence">{verdict.sentence}</p>
      <p className="lane-counts">{laneCountLine(lane)}</p>
      {lane.freeze ? <p className="lane-counts">Permission slip revoked: this agent can do nothing more.</p> : null}
      {lane.error ? <p className="error-text">Agent error: {lane.error}</p> : null}
      <button className="s-btn s-btn--ghost s-btn--small lane-toggle" onClick={() => onSteps(lane.lane_id)}>Show steps</button>
    </section>
  )
}

export default function Stage({ view, onSteps }) {
  return (
    <div className={`stage stage-${view.lanes.length}`}>
      {view.lanes.map((l, i) => (
        <Lane key={l.lane_id} lane={l} view={view} decisive={i === view.lanes.length - 1} onSteps={onSteps} />
      ))}
    </div>
  )
}
