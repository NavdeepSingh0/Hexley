import { useLayoutEffect, useRef } from 'react'
import { Icon } from '../Blocks.jsx'

// The box at the bottom: it grows with what is typed, Enter sends, Shift+Enter breaks the line, and when it is closed the
// reason is written in the box itself. The disclosure sits right under it, always.
export default function Composer({ draft, setDraft, onSend, block, busy, disclosure }) {
  const ref = useRef(null)
  useLayoutEffect(() => {
    const el = ref.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 220)}px`
  }, [draft])
  const can = !block && !busy && draft.trim().length > 0
  return (
    <div className="cx-composer-wrap">
      <div className={`cx-composer${block ? ' is-closed' : ''}`}>
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
