import DrawerShell from '../chrome/DrawerShell.jsx'
import { DECISION_WORD, TOOL_LABEL, RULE_LABEL, chainLinks, firstBlockedStep, highlightTokens } from '../lib/derive.js'

// The first Hexley step that was denied or quarantined, with its lane: what Enter opens.
export function verdictFor(view) {
  for (const lane of view.lanes) {
    if (lane.column !== 'sentinel') continue
    const hit = firstBlockedStep(lane)
    if (hit) return { lane, ...hit }
  }
  return null
}

// The step a "Why?" click points at, with its lane (null if it is not a denied or quarantined step).
export function targetFor(view, laneId, index) {
  const lane = view.lanes.find((l) => l.lane_id === laneId)
  const step = lane?.steps?.[index]
  return step && (step.effect === 'BLOCK' || step.effect === 'FREEZE') ? { lane, index, step } : null
}

function ChainStrip({ lane, index }) {
  const links = chainLinks(lane).filter((l) => l.to === index)
  if (!links.length) return null
  return (
    <div className="chain">
      <p className="s-label">How the data got there</p>
      {links.map((l) => (
        <div key={`${l.from}-${l.to}`} className="chain-row">
          <span className="chain-node">{TOOL_LABEL[lane.steps[l.from].tool] ?? lane.steps[l.from].tool}</span>
          <span className="chain-arrow" aria-label="carried restricted values into">→</span>
          <span className="chain-node chain-node-blocked">{TOOL_LABEL[lane.steps[l.to].tool] ?? lane.steps[l.to].tool}</span>
        </div>
      ))}
      <p className="chain-caption">Observed tool flow with value-match links, from Hexley&rsquo;s own evidence.</p>
    </div>
  )
}

// Everything about one denied step, on demand, in a drawer from the right. The stage stays readable behind it.
// `onContinue` moves the guided demo on (Enter); `onDismiss` just closes the drawer (Escape, the scrim, the close button).
// `onBack` (only when it was opened from a lane's step list) returns to that list.
export default function Drawer({ target, onContinue, onDismiss, onBack }) {
  if (!target) return null
  const { lane, index, step } = target
  const tokens = (step.evidence || []).flatMap((e) => e.matched_tokens || [])
  const message = step.args?.body ?? JSON.stringify(step.args)
  const { segments, unlocated } = highlightTokens(String(message), tokens)
  const frozen = step.effect === 'FREEZE'
  const word = DECISION_WORD[step.effect] ?? 'DENIED'
  return (
    <DrawerShell label={`${lane.title.startsWith('Hexley') ? 'Hexley' : lane.title} · ${(step.rule_ids || []).join(' + ')}`}
      onDismiss={onDismiss} onBack={onBack} ariaLabel="Why Hexley denied it">
      <p className={`s-verdict ${frozen ? 's-verdict--quarantined' : 's-verdict--denied s-glow s-glow--denied'}`}>{word}</p>
      <h2 className="drawer-title">{(step.rule_ids || []).map((r) => RULE_LABEL[r] ?? r).join(' · ')}</h2>
      <p className="drawer-summary">{step.summary}</p>

      <p className="s-label">The message the agent tried to send{step.args?.to ? ` to ${step.args.to}` : ''}</p>
      <div className="drawer-message">
        {segments.map((s, i) => (s.hit ? <mark key={i}>{s.text}</mark> : <span key={i}>{s.text}</span>))}
      </div>
      {unlocated.length ? <p className="drawer-note">Also matched (written differently in the message): {unlocated.join(', ')}</p> : null}

      <ChainStrip lane={lane} index={index} />

      {(step.evidence || []).length ? (
        <details className="evidence-box">
          <summary>Evidence ({step.evidence.length})</summary>
          <ul className="evidence">
            {step.evidence.map((e, i) => (
              <li key={i}><b>{e.kind}</b>: {e.detail}{(e.matched_tokens || []).length ? ` (${e.matched_tokens.join(', ')})` : ''}</li>
            ))}
          </ul>
        </details>
      ) : null}

      <p className="drawer-foot">
        Decided by deterministic rules, no AI in the decision
        {step.latency_ms != null ? ` · in ${step.latency_ms < 0.1 ? '<0.1' : step.latency_ms.toFixed(1)} ms` : ''}
        {' · '}recorded in the signed audit log before anything was forwarded.
      </p>
      <button className="s-btn s-btn--primary drawer-continue" onClick={onContinue}>Continue <span className="s-kbd">Enter</span></button>
    </DrawerShell>
  )
}
