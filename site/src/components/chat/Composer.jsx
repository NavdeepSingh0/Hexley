import { useLayoutEffect, useRef, useState } from 'react'
import { Icon } from '../Blocks.jsx'

// The box at the bottom: it grows with what is typed, Enter sends, Shift+Enter breaks the line, and when it is closed the
// reason is written in the box itself. The disclosure sits right under it, always.
export default function Composer({ draft, setDraft, onSend, block, busy, disclosure, onUpload, documents = [] }) {
  const ref = useRef(null)
  const fileRef = useRef(null)
  const [upload, setUpload] = useState({ status: 'idle', note: '' })
  const pick = async (e) => {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file || !onUpload) return
    setUpload({ status: 'working', note: `Uploading ${file.name}...` })
    try { const d = await onUpload(file); setUpload({ status: 'idle', note: `${d.name} is ready: ${d.pages} page${d.pages === 1 ? '' : 's'}. It is treated as untrusted.` }) }
    catch (err) { setUpload({ status: 'error', note: err.message }) }
  }
  useLayoutEffect(() => {
    const el = ref.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 220)}px`
  }, [draft])
  const can = !block && !busy && draft.trim().length > 0
  return (
    <div className="cx-composer-wrap">
      {documents.length > 0 && (
        <ul className="cx-docs" aria-label="Documents in this chat">
          {documents.map((d) => <li key={d.name} className="cx-doc"><Icon name="book" size={15} /> {d.name} <span className="muted">· {d.pages} p · untrusted</span></li>)}
        </ul>
      )}
      {upload.note && <p className={`cx-upload-note${upload.status === 'error' ? ' is-error' : ''}`} role="status">{upload.note}</p>}
      <div className={`cx-composer${block ? ' is-closed' : ''}${onUpload ? ' has-attach' : ''}`}>
        {onUpload && (
          <>
            <input ref={fileRef} type="file" accept="application/pdf,.pdf" className="visually-hidden" tabIndex={-1} onChange={pick} aria-hidden="true" />
            <button type="button" className="cx-attach" onClick={() => fileRef.current?.click()} disabled={upload.status === 'working'}
              aria-label="Upload a PDF" title="Upload a PDF"><Icon name="plus" size={18} /></button>
          </>
        )}
        <textarea
          ref={ref} rows={1} value={draft} onChange={(e) => setDraft(e.target.value)} disabled={Boolean(block)}
          aria-label="Message the agent" aria-describedby="cx-disclosure"
          placeholder={block || 'Message the agent'}
          onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey && can) { e.preventDefault(); onSend() } }}
        />
        <button type="button" className="cx-send" onClick={onSend} disabled={!can} aria-label="Send"><Icon name="arrow" size={18} className="cx-send-icon" /></button>
      </div>
      <p id="cx-disclosure" className="cx-disclosure">{disclosure}</p>
    </div>
  )
}
