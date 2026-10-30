import { useState } from 'react'
import { Icon } from '../Blocks.jsx'
import { getChatRecording, verifyAudit } from '../../api/client.js'
import { allActions, decisionKind, decisionWord } from '../../lib/chat.js'

// The right-hand drawer: the slip, every decision of this chat in order, whether the audit log is intact, the recording.
export default function Details({ view, onClose }) {
  const [audit, setAudit] = useState(null)
  const [note, setNote] = useState('')
  const actions = allActions(view)
  const verify = async () => {
    setAudit({ status: 'working' })
    try { setAudit({ status: 'done', ...(await verifyAudit()) }) } catch (e) { setAudit({ status: 'error', error: e.message }) }
  }
  const download = async () => {
    setNote('')
    try {
      const rec = await getChatRecording(view.chat_id)
      const url = URL.createObjectURL(new Blob([JSON.stringify(rec, null, 2)], { type: 'application/json' }))
      const a = document.createElement('a')
      a.href = url
      a.download = `${view.chat_id}-recording.json`
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) { setNote(e.message) }
  }
  const s = view.slip
  return (
    <aside className="cx-details" aria-label="Details of this chat">
      <div className="cx-details-head">
        <h2 className="cx-details-title">Details</h2>
        <button type="button" className="cx-icon-btn" onClick={onClose} aria-label="Close the details"><Icon name="close" size={18} /></button>
      </div>
      <section className="cx-details-sec">
        <p className="s-label">Permission slip</p>
        <p className="cx-details-strong">{s.objective}</p>
        <dl className="cx-facts">
          <dt>May use</dt><dd>{s.allowed_tools.map((t) => t.replace(/_/g, ' ')).join(', ')}</dd>
          <dt>May write to</dt><dd>{s.allowed_destinations.join(', ') || 'nobody'}</dd>
          <dt>Message limit</dt><dd>{s.max_messages}</dd>
        </dl>
      </section>
      {view.documents?.length > 0 && (
        <section className="cx-details-sec">
          <p className="s-label">What the model is given</p>
          <p className="muted cx-details-small">The exact text Hexley's PDF reader extracts, including text a person cannot see on the page. It is untrusted.</p>
          {view.documents.map((d) => (
            <details key={d.name} className="cx-doc-text">
              <summary>{d.name} · {d.pages} p · {d.chars} characters</summary>
              <pre tabIndex={0}>{d.text || '(no text could be extracted)'}</pre>
            </details>
          ))}
        </section>
      )}
      <section className="cx-details-sec">
        <p className="s-label">Decisions, in order</p>
        {actions.length === 0 && <p className="muted">None yet.</p>}
        <ol className="cx-timeline">
          {actions.map((a, i) => (
            <li key={a.action_id}>
              <span className="cx-timeline-n">{i + 1}</span>
              <span className={`cx-timeline-word cx-timeline-word--${decisionKind(a.decision)}`}>{decisionWord(a.decision)}</span>
              <span>{a.label}</span>
            </li>
          ))}
        </ol>
      </section>
      <section className="cx-details-sec">
        <p className="s-label">Audit log</p>
        <button type="button" className="s-btn s-btn--ghost s-btn--small" onClick={verify} disabled={audit?.status === 'working'}>Verify the log</button>
        <p className="cx-audit" role="status">
          {audit?.status === 'done' && (audit.ok ? `Intact: ${audit.checked} records checked.` : `Altered: the chain breaks at record ${audit.first_bad_seq ?? '?'}.`)}
          {audit?.status === 'error' && audit.error}
        </p>
      </section>
      <section className="cx-details-sec">
        <p className="s-label">This chat</p>
        <p className="muted cx-details-small">{view.disclosure}</p>
        <button type="button" className="s-btn s-btn--ghost s-btn--small" onClick={download}>Download the recording</button>
        {note && <p className="conn-error" role="alert">{note}</p>}
      </section>
    </aside>
  )
}
