import { useEffect, useRef, useState } from 'react'
import { decideApproval } from '../api.js'
import {
  TOOL_LABEL, RULE_LABEL, bankChanges, highlightTokens, inboxRowView, laneCounts, laneHeadline, shortArgs, stepStamp,
} from '../lib/derive.js'

const SOURCE_WORD = { scripted: 'scripted', replay: 'replayed', live: 'live' }

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

function StepCard({ step, isSentinel }) {
  const stamp = stepStamp(step)
  return (
    <li className={`step step-${stamp.kind}`}>
      <div className="step-top">
        <span className="step-tool">{TOOL_LABEL[step.tool] ?? step.tool}</span>
        <span className={`stamp stamp-${stamp.kind}`}>{stamp.label}</span>
      </div>
      <div className="step-args">{shortArgs(step)}</div>
      {step.effect === 'BLOCK' || step.effect === 'FREEZE' ? (
        <div className="step-why">
          {(step.rule_ids || []).map((r) => RULE_LABEL[r] ?? r).join(' · ')}
        </div>
      ) : null}
      {isSentinel && (step.effect === 'BLOCK' || step.effect === 'FREEZE') && step.latency_ms != null ? (
        <div className="step-meta">Sentinel decision (live) in {step.latency_ms < 0.1 ? '<0.1' : step.latency_ms.toFixed(1)} ms</div>
      ) : null}
    </li>
  )
}

function ApprovalCard({ approval, onDecided }) {
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState(null)
  const act = async (d) => {
    setBusy(true)
    setErr(null)
    try {
      await decideApproval(approval.approval_id, d)
      await onDecided()
    } catch (e) {
      setErr(e.message)
    } finally {
      setBusy(false)
    }
  }
  return (
    <div className="approval">
      <div className="approval-title">NEEDS APPROVAL: the officer decides</div>
      <div className="approval-body">
        Change <b>{approval.args.vendor}</b>’s bank account to <b>{approval.args.account_number}</b>?
        <span className="approval-note"> Runs only if you approve this exact request.</span>
      </div>
      <div className="approval-actions">
        <button className="btn btn-primary" disabled={busy} onClick={() => act('approve')}>Approve</button>
        <button className="btn" disabled={busy} onClick={() => act('deny')}>Deny</button>
        <span className="approval-expiry">expires in {approval.expires_in}s</span>
      </div>
      {err ? <div className="error-text">{err}</div> : null}
    </div>
  )
}

function Effects({ lane, view, tokens }) {
  const banks = bankChanges(lane)
  const isBank = view.scenario.id === 'bank_change'
  if (isBank) {
    return (
      <div className="effects">
        <div className="effects-title">What changed in the vendor master</div>
        {banks.length ? banks.map((b, i) => (
          <div key={i} className={`effect-row ${b.approved ? 'effect-ok' : 'effect-bad'}`}>
            Bank account of <b>{b.vendor}</b> → <b>{b.account}</b>
            <div className="effect-sub">{b.approved ? 'approved by the officer' : 'nobody was asked'}</div>
          </div>
        )) : <div className="effect-empty">No change was made.</div>}
      </div>
    )
  }
  if (view.inbox_ok === false) {
    return <div className="effects"><div className="effect-empty">The vendor’s inbox could not be read: do not treat this lane as “nothing leaked”.</div></div>
  }
  const rows = lane.inbox || []
  return (
    <div className="effects">
      <div className="effects-title">What reached the outside</div>
      {rows.length === 0 ? <div className="effect-empty">Nothing was delivered.</div> : rows.map((r, i) => {
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

function Lane({ lane, view, tokens, refresh }) {
  const stepsEnd = useRef(null)
  const stepCount = (lane.steps || []).length
  // New steps (and the FREEZE that ends a lane) arrive at the bottom: keep them in view without the presenter scrolling.
  useEffect(() => {
    const el = stepsEnd.current
    if (el) el.scrollTop = el.scrollHeight
  }, [stepCount, lane.freeze])
  const head = laneHeadline(lane)
  const counts = laneCounts(lane)
  const calls = `${counts.calls} ${counts.calls === 1 ? 'call' : 'calls'}`
  const isSentinel = lane.column === 'sentinel'
  const agent = `agent actions ${SOURCE_WORD[view.source] ?? view.source}`
  const caption = lane.column === 'unprotected' ? `no policy evaluated · ${agent}`
    : lane.column === 'r1_only' ? `R1 checks only: no data-flow links · ${agent}`
    : `${agent} · Sentinel decisions live`
  // The paraphrase the value matcher cannot see: shown plainly, it is the declared gap that hardened mode closes (D-028/D-029).
  const paraphraseNote = view.scenario.id === 'hardened' && lane.mode === 'fingerprint' && (lane.inbox || []).length > 0
  return (
    <section className={`lane lane-${lane.column} ${lane.freeze ? 'lane-quarantined' : ''}`}>
      <header className="lane-head">
        <div className="lane-title">{lane.title}</div>
        {lane.badge ? <div className="badge">{lane.badge}</div> : null}
        {caption ? <div className="lane-caption">{caption}</div> : null}
      </header>
      <div className={`headline headline-${head.tone}`} role="status">{head.text}</div>
      <div className="lane-counts">
        {lane.column === 'r1_only' && counts.calls && counts.allowed === counts.calls
          ? `${calls} · all allowed by access control`
          : `${calls} · ${counts.allowed} allowed · ${counts.denied} denied${counts.quarantined ? ` · ${counts.quarantined} quarantined the agent` : ''}`}
      </div>
      {lane.freeze ? <div className="lane-counts">Permission slip revoked: this agent can do nothing more.</div> : null}
      {paraphraseNote ? (
        <div className="gap-note">
          Delivered. Neither the value matcher nor the evaluation oracle finds a listed value in this wording, yet the sentence
          still describes stock: the declared gap that hardened mode (right) closes by allowing no free text.
        </div>
      ) : null}
      {(lane.approvals || []).map((a) => <ApprovalCard key={a.approval_id} approval={a} onDecided={refresh} />)}
      {lane.contract?.egress_template && isSentinel ? (
        <div className="template-box">
          <div className="template-title">The only message this agent can send</div>
          <div className="template-body">{lane.contract.egress_template.body}</div>
        </div>
      ) : null}
      <ol className="steps" ref={stepsEnd}>
        {(lane.steps || []).map((s) => <StepCard key={s.action_id} step={s} isSentinel={isSentinel} />)}
      </ol>
      <Effects lane={lane} view={view} tokens={tokens} />
      {lane.error ? <div className="error-text">Agent error: {lane.error}</div> : null}
    </section>
  )
}

export default function Stage({ view, refresh }) {
  const tokens = restrictedTokens(view)
  return (
    <div className={`stage stage-${view.lanes.length}`}>
      {view.lanes.map((l) => <Lane key={l.lane_id} lane={l} view={view} tokens={tokens} refresh={refresh} />)}
    </div>
  )
}
