import { useEffect, useRef, useState } from 'react'
import { decideApproval } from '../api.js'
import { approvalView } from '../lib/derive.js'

// The officer's decision, with exactly what is being asked: what, the detail, why it was held, Approve, Deny.
// Nothing runs unless the officer approves this exact request (R4); silence expires as a denial.
export default function ApprovalModal({ approval, onDecided }) {
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState(null)
  const ref = useRef(null)
  useEffect(() => { ref.current?.focus() }, [approval.approval_id])
  const v = approvalView(approval)
  const act = async (decision) => {
    setBusy(true)
    setErr(null)
    try {
      await decideApproval(approval.approval_id, decision)
      await onDecided()
    } catch (e) {
      setErr(e.message)
    } finally {
      setBusy(false)
    }
  }
  return (
    <>
      <div className="scrim" />
      <div className="modal" role="alertdialog" aria-modal="true" aria-label="The officer decides" tabIndex={-1} ref={ref}>
        <div className="s-panel s-panel--raised s-glow s-glow--approval approval-card">
          <p className="s-verdict s-verdict--approval">Needs approval</p>
          <p className="approval-what">{v.what}</p>
          <p className="approval-detail">{v.detail}</p>
          <p className="approval-why">{v.why}</p>
          <div className="approval-actions">
            <button className="s-btn s-btn--primary" disabled={busy} onClick={() => act('approve')}>Approve</button>
            <button className="s-btn s-btn--ghost" disabled={busy} onClick={() => act('deny')}>Deny</button>
            <span className="approval-expiry">expires in {approval.expires_in}s</span>
          </div>
          {err ? <p className="error-text">{err}</p> : null}
        </div>
      </div>
    </>
  )
}
