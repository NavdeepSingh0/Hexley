import { useEffect, useState } from 'react'
import { getRecordings, getScenarios } from '../api.js'
import { TOOL_ALLOWS, groupSlips, pickDefaultRecording } from '../lib/derive.js'

const SOURCES = [
  ['scripted', 'Scripted', 'A fixed, fully compromised agent: the same attack every time.'],
  ['replay', 'Replay', 'A real AI model’s recorded behaviour, replayed. Hexley still decides live.'],
  ['live', 'Live', 'A real AI model right now. Needs the model API; behaviour varies.'],
]

export function StartScreen({ onCreate, onGuided, error, busy, playlist, visitor }) {
  const [scenarios, setScenarios] = useState([])
  const [recordings, setRecordings] = useState([])
  const [source, setSource] = useState('scripted')
  const [recId, setRecId] = useState({})
  useEffect(() => {
    getScenarios().then(setScenarios).catch(() => {})
    getRecordings().then(setRecordings).catch(() => {})
  }, [])

  const recFor = (sid) => recordings.filter((r) => r.scenario === sid).sort((a, b) => a.attempt - b.attempt)
  const chosen = (sid) => recId[sid] ?? pickDefaultRecording(recordings, sid)?.recording_id
  const hint = SOURCES.find(([id]) => id === source)[2]

  return (
    <div className="screen">
      <p className="s-label">Hexley console</p>
      <h1 className="screen-title">Watch an AI agent get attacked</h1>
      <p className="screen-sub">The same hostile input goes to three setups. Only one of them stops it.</p>
      {visitor ? <p className="source-hint">You are trying this as a visitor: you play the officer, on synthetic data and mock tools. If someone else is mid-run, try again in a minute.</p> : null}
      <div className="start-actions">
        <button className="s-btn s-btn--primary s-btn--big" disabled={busy} onClick={onGuided}>
          Run the guided demo <span className="s-kbd">Enter</span>
        </button>
        <span className="start-count">{playlist.length} situations, about five minutes</span>
      </div>

      <div className="source-row">
        <p className="s-label">Or pick one yourself</p>
        <div className="source-picker" role="radiogroup" aria-label="Where the agent’s behaviour comes from">
          {SOURCES.filter(([id]) => !visitor || id !== 'live').map(([id, name]) => (
            <button key={id} role="radio" aria-checked={source === id} className={`s-btn s-btn--small source${source === id ? ' source-on' : ''}`}
              onClick={() => setSource(id)}>{name}</button>
          ))}
        </div>
        <p className="source-hint">{hint}</p>
      </div>

      <div className="cards">
        {scenarios.map((s) => {
          const recs = recFor(s.id)
          const noRec = source === 'replay' && recs.length === 0
          return (
            <div key={s.id} className="s-panel card">
              <h2 className="card-title">{s.title}</h2>
              <p className="card-desc">{s.description}</p>
              {source === 'replay' && recs.length ? (
                <select className="select" value={chosen(s.id)} onChange={(e) => setRecId({ ...recId, [s.id]: e.target.value })}>
                  {recs.map((r) => (
                    <option key={r.recording_id} value={r.recording_id}>
                      attempt {r.attempt}/{r.attempts_total} — {r.lanes.map((l) => l.outcome).join(' / ')}
                    </option>
                  ))}
                </select>
              ) : null}
              {noRec ? <p className="card-note">No recording of this scenario yet.</p> : null}
              <button className="s-btn s-btn--ghost s-btn--small" disabled={busy || noRec}
                onClick={() => onCreate(s.id, source, source === 'replay' ? chosen(s.id) : undefined)}>
                Draft the permission slip
              </button>
            </div>
          )
        })}
      </div>
      {error ? <p className="error-text">{error}</p> : null}
    </div>
  )
}

export function SlipScreen({ view, onConfirm, busy, error }) {
  const groups = groupSlips(view.lanes)
  return (
    <div className="screen">
      <p className="s-label">The permission slip</p>
      <h1 className="screen-title">Before the agent starts, it gets exactly one job</h1>
      <p className="screen-sub">Nothing runs until the officer confirms the slip.</p>
      {groups.map((g, i) => {
        const c = g.contract
        return (
          <div key={i} className="s-panel is-active slip">
            <p className="s-label">
              {groups.length === 1 ? `Issued identically to all ${g.columns.length} setups` : `Issued to: ${g.titles.join(', ')}`}
            </p>
            <p className="slip-objective">{c.objective}</p>
            <dl className="slip-grid">
              <dt>May do</dt>
              <dd>{c.allowed_tools.map((t) => TOOL_ALLOWS[t] ?? t).join(' · ')}</dd>
              <dt>May write to</dt>
              <dd>{(c.allowed_recipient_domains || []).join(', ') || 'nobody'}</dd>
              <dt>Restricted data may go to</dt>
              <dd>{(c.internal_destinations || []).join(', ') || 'nowhere outside'}</dd>
              {c.resolved_vendor ? (<><dt>Vendor on file</dt><dd>{c.resolved_vendor.name} · {c.resolved_vendor.email}</dd></>) : null}
              <dt>Message limit</dt>
              <dd>{c.max_messages}</dd>
              {c.egress_template ? (<><dt>Only message allowed</dt><dd>“{c.egress_template.body}”</dd></>) : null}
            </dl>
          </div>
        )
      })}
      <div className="slip-confirm">
        <button className="s-btn s-btn--primary s-btn--big" disabled={busy} onClick={onConfirm}>
          Confirm as officer <span className="s-kbd">Enter</span>
        </button>
        <span className="start-count">{view.officer}</span>
      </div>
      {error ? <p className="error-text">{error}</p> : null}
    </div>
  )
}
