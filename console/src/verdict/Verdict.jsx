import { DECISION_WORD, TOOL_LABEL, RULE_LABEL, chainLinks, firstBlockedStep, highlightTokens } from '../lib/derive.js'

export function verdictFor(view) {
  for (const lane of view.lanes) {
    if (lane.column !== 'sentinel') continue
    const hit = firstBlockedStep(lane)
    if (hit) return { lane, ...hit }
  }
  return null
}

function ChainStrip({ lane, index }) {
  const links = chainLinks(lane).filter((l) => l.to === index)
  if (!links.length) return null
  return (
    <div className="chain">
      {links.map((l) => (
        <div key={`${l.from}-${l.to}`} className="chain-row">
          <span className="chain-node">{TOOL_LABEL[lane.steps[l.from].tool] ?? lane.steps[l.from].tool}</span>
          <span className="chain-arrow">→ carried restricted values into →</span>
          <span className="chain-node chain-node-blocked">{TOOL_LABEL[lane.steps[l.to].tool] ?? lane.steps[l.to].tool}</span>
        </div>
      ))}
      <div className="chain-caption">Observed tool flow with value-match links (from Sentinel’s own evidence).</div>
    </div>
  )
}

export default function Verdict({ view, onClose }) {
  const v = verdictFor(view)
  if (!v) return null
  const { lane, index, step } = v
  const tokens = (step.evidence || []).flatMap((e) => e.matched_tokens || [])
  const message = step.args?.body ?? JSON.stringify(step.args)
  const { segments, unlocated } = highlightTokens(String(message), tokens)
  const frozen = step.effect === 'FREEZE'
  return (
    <div className="verdict" role="dialog" aria-label="Why Sentinel denied it">
      <div className={`verdict-card ${frozen ? 'verdict-card-quarantined' : ''}`}>
        <div className="verdict-top">
          <div className="verdict-kicker">{DECISION_WORD[step.effect] ?? 'DENIED'} · {(step.rule_ids || []).join(' + ')} · {lane.title}</div>
          <button className="btn btn-primary" onClick={onClose}>Continue (Enter)</button>
        </div>
        <h2 className="verdict-title">{(step.rule_ids || []).map((r) => RULE_LABEL[r] ?? r).join(' · ')}</h2>
        <p className="verdict-summary">{step.summary}</p>
        <div className="verdict-label">The message the agent tried to send{step.args?.to ? ` to ${step.args.to}` : ''}:</div>
        <div className="verdict-message">
          {segments.map((s, i) => (s.hit ? <mark key={i}>{s.text}</mark> : <span key={i}>{s.text}</span>))}
        </div>
        {unlocated.length ? (
          <div className="verdict-note">Also matched (written differently in the message): {unlocated.join(', ')}</div>
        ) : null}
        <ChainStrip lane={lane} index={index} />
        <ul className="evidence">
          {(step.evidence || []).map((e, i) => (
            <li key={i}><b>{e.kind}</b>: {e.detail}{(e.matched_tokens || []).length ? ` (${e.matched_tokens.join(', ')})` : ''}</li>
          ))}
        </ul>
        <div className="verdict-foot">
          Decided by deterministic rules, no AI in the decision · {step.latency_ms != null ? `in ${step.latency_ms < 0.1 ? '<0.1' : step.latency_ms.toFixed(1)} ms · ` : ''}
          recorded in the signed audit log before anything was forwarded.
        </div>
      </div>
    </div>
  )
}
