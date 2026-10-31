import { useLayoutEffect, useRef } from 'react'
import { Icon } from '../Blocks.jsx'

// A file attached to a message, the way a frontier chat shows it: a card with the file's name and size. In the box it can
// be removed before sending; on a sent message it stays with the message.
export function FileCard({ file, onRemove }) {
  return (
    <div className={`cx-file${file.status === 'uploading' ? ' is-uploading' : ''}${file.status === 'error' ? ' is-error' : ''}`}>
      <span className="cx-file-icon" aria-hidden="true"><Icon name="book" size={18} /></span>
      <span className="cx-file-text">
        <span className="cx-file-name" title={file.name}>{file.name}</span>
        <span className="cx-file-meta">
          {file.status === 'uploading' ? 'Uploading...' : file.status === 'error' ? file.error : `PDF · ${file.pages} page${file.pages === 1 ? '' : 's'} · untrusted`}
        </span>
      </span>
      {onRemove && (
        <button type="button" className="cx-file-remove" onClick={onRemove} aria-label={`Remove ${file.name}`}><Icon name="close" size={14} /></button>
      )}
    </div>
  )
}

// The box at the bottom: it grows with what is typed, Enter sends, Shift+Enter breaks the line, and when it is closed the
// reason is written in the box itself. Files picked with + sit inside the box until they are sent with the message. The
// disclosure sits right under it, always.
export default function Composer({ draft, setDraft, onSend, block, canType = false, busy, disclosure, onAttach, attachments = [], onDetach }) {
  const ref = useRef(null)
  const fileRef = useRef(null)
  useLayoutEffect(() => {
    const el = ref.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 220)}px`
  }, [draft])
  const uploading = attachments.some((a) => a.status === 'uploading')
  const can = !block && !busy && !uploading && draft.trim().length > 0
  const pick = (e) => {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (file && onAttach) onAttach(file)
  }
  return (
    <div className="cx-composer-wrap">
      <div className={`cx-composer${block && !canType ? ' is-closed' : ''}`}>
        {attachments.length > 0 && (
          <div className="cx-files" aria-label="Files attached to this message">
            {attachments.map((a) => <FileCard key={a.name} file={a} onRemove={a.status === 'uploading' ? null : () => onDetach(a.name)} />)}
          </div>
        )}
        <div className="cx-composer-row">
          {onAttach && (
            <>
              <input ref={fileRef} type="file" accept="application/pdf,.pdf" className="visually-hidden" tabIndex={-1} onChange={pick} aria-hidden="true" />
              <button type="button" className="cx-attach" onClick={() => fileRef.current?.click()} disabled={uploading || Boolean(block)}
                aria-label="Attach a PDF" title="Attach a PDF"><Icon name="plus" size={18} /></button>
            </>
          )}
          <textarea
            ref={ref} rows={1} value={draft} onChange={(e) => setDraft(e.target.value)} disabled={Boolean(block) && !canType} autoFocus
            aria-label="Message the agent" aria-describedby="cx-disclosure"
            placeholder={canType ? 'Message Hexley Chat' : block || (attachments.length ? 'Say what to do with it' : 'Message Hexley Chat')}
            onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey && can) { e.preventDefault(); onSend() } }}
          />
          <button type="button" className="cx-send" onClick={onSend} disabled={!can} aria-label="Send"><Icon name="arrow" size={18} className="cx-send-icon" /></button>
        </div>
      </div>
      <p id="cx-disclosure" className="cx-disclosure">{disclosure}</p>
    </div>
  )
}
