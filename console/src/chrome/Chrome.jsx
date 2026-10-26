import { verifyView } from '../lib/derive.js'

const SOURCE_NAME = { scripted: 'SCRIPTED', replay: 'REPLAY', live: 'LIVE' }

export function TopBar({ view, lost }) {
  return (
    <div className="topbar">
      <div className="brand">SENTINEL <span>the AI can only do the job you gave it</span></div>
      {view ? (
        <>
          <div className={`chip chip-${view.source}`}>{SOURCE_NAME[view.source]}</div>
          <div className="disclosure">{view.disclosure}</div>
        </>
      ) : <div className="disclosure">No run yet</div>}
      {lost ? <div className="chip chip-lost">connection lost: retrying</div> : null}
    </div>
  )
}

export function AuditBar({ verify, onVerify, onTamper, busy }) {
  const v = verifyView(verify)
  return (
    <div className="auditbar">
      <div className="audit-label">Audit log (signed, hash-chained)</div>
      <div className={`audit-state audit-${v.tone}`}>{v.text}</div>
      <button className="btn" disabled={busy} onClick={onVerify}>Verify (V)</button>
      {verify?.tamper_enabled ? <button className="btn" disabled={busy} onClick={onTamper}>Tamper with a record (T)</button> : null}
    </div>
  )
}
