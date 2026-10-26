import { useEffect, useState } from 'react'
import { getRecordings, getScenarios } from '../api.js'
import { TOOL_ALLOWS, groupSlips, pickDefaultRecording } from '../lib/derive.js'

const SOURCES = [
  ['scripted', 'SCRIPTED', 'a fixed, fully compromised agent: the same attack every time'],
  ['replay', 'REPLAY', 'a real AI model’s recorded behaviour, replayed; Sentinel still decides live'],
  ['live', 'LIVE', 'a real AI model right now (needs the model API; behaviour varies)'],
]

export function StartScreen({ onCreate, error, busy, playlist }) {
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

  return (
    <div className="screen">
      <h1 className="screen-title">Pick a situation</h1>
      <div className="source-picker" role="radiogroup" aria-label="Where the agent’s behaviour comes from">
        {SOURCES.map(([id, name, hint]) => (
          <button key={id} role="radio" aria-checked={source === id} className={`source ${source === id ? 'source-on' : ''}`}
            onClick={() => setSource(id)}>
            <b>{name}</b><span>{hint}</span>
          </button>
        ))}
      </div>
      <div className="cards">
        {scenarios.map((s) => {
          const recs = recFor(s.id)
          const noRec = source === 'replay' && recs.length === 0
          return (
            <div key={s.id} className="card">
              <div className="card-title">{s.title}</div>
              <div className="card-desc">{s.description}</div>
              {source === 'replay' && recs.length ? (
                <select className="select" value={chosen(s.id)} onChange={(e) => setRecId({ ...recId, [s.id]: e.target.value })}>
                  {recs.map((r) => (
                    <option key={r.recording_id} value={r.recording_id}>
                      attempt {r.attempt}/{r.attempts_total} — {r.lanes.map((l) => l.outcome).join(' / ')}
                    </option>
                  ))}
                </select>
              ) : null}
              {noRec ? <div className="card-note">No recording of this scenario yet.</div> : null}
              <button className="btn btn-primary" disabled={busy || noRec}
                onClick={() => onCreate(s.id, source, source === 'replay' ? chosen(s.id) : undefined)}>
                Draft the permission slip
              </button>
            </div>
          )
        })}
      </div>
      {error ? <div className="error-text">{error}</div> : null}
      <div className="hint">Presenter: press <kbd>Enter</kbd> to run the guided demo ({playlist.length} steps), <kbd>N</kbd> skips to the next.</div>
    </div>
  )
}

export function SlipScreen({ view, onConfirm, busy, error }) {
  const groups = groupSlips(view.lanes)
  return (
    <div className="screen">
      <h1 className="screen-title">The permission slip</h1>
      <p className="lede">Before the AI agent starts, an officer gives it exactly one job. Nothing runs until the slip is confirmed.</p>
      {groups.map((g, i) => {
        const c = g.contract
        return (
          <div key={i} className="slip">
            <div className="slip-kicker">
              {groups.length === 1 ? `Issued identically to all ${g.columns.length} columns` : `Issued to: ${g.titles.join(', ')}`}
            </div>
            <div className="slip-objective">{c.objective}</div>
            <dl className="slip-grid">
              <dt>Allowed actions</dt>
              <dd>{c.allowed_tools.map((t) => TOOL_ALLOWS[t] ?? t).join(' · ')}</dd>
              <dt>May write to</dt>
              <dd>{(c.allowed_recipient_domains || []).join(', ') || 'nobody'}</dd>
              {c.resolved_vendor ? (<><dt>Vendor on file</dt><dd>{c.resolved_vendor.name} · {c.resolved_vendor.email}</dd></>) : null}
              <dt>Message limit</dt>
              <dd>{c.max_messages}</dd>
              {c.egress_template ? (<><dt>Only message allowed</dt><dd>“{c.egress_template.body}”</dd></>) : null}
            </dl>
          </div>
        )
      })}
      <button className="btn btn-primary btn-big" disabled={busy} onClick={onConfirm}>Confirm as officer ({view.officer})</button>
      {error ? <div className="error-text">{error}</div> : null}
    </div>
  )
}
