import { useRef, useState } from 'react'
import { STATUS_LABEL } from '../lib/connect.js'

// How far we have actually tested something. The label words are fixed (Tested / Should work / Planned).
export function StatusBadge({ status }) {
  const mod = status === 'tested' ? ' s-badge--tested' : status === 'planned' ? ' s-badge--planned' : ''
  return <span className={`s-badge${mod}`}>{STATUS_LABEL[status] ?? status}</span>
}

// A real screenshot in both themes. Only the current theme's picture is shown (CSS) and, being lazy, downloaded.
export function Shot({ name, alt }) {
  const common = { width: 1280, height: 720, loading: 'lazy', alt }
  return (
    <>
      <img className="shot shot-dark" src={`/img/console-${name}-dark.png`} {...common} />
      <img className="shot shot-light" src={`/img/console-${name}-light.png`} {...common} />
    </>
  )
}

// A value to copy: a connector address, a token, a command. If the browser refuses to write to the clipboard the text is
// selected instead and the message says what to press.
export function CopyField({ label, value, block = false, secret = false }) {
  const ref = useRef(null)
  const [msg, setMsg] = useState('')
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(value)
      setMsg('Copied.')
    } catch {
      const el = ref.current
      if (el) {
        const range = document.createRange()
        range.selectNodeContents(el)
        const sel = window.getSelection()
        sel.removeAllRanges()
        sel.addRange(range)
      }
      setMsg('Selected. Press Ctrl+C to copy.')
    }
    setTimeout(() => setMsg(''), 3000)
  }
  return (
    <div className="copy">
      <div className="copy-head">
        <p className="s-label">{label}</p>
        <button type="button" className="s-btn s-btn--ghost s-btn--small" onClick={copy}>Copy</button>
      </div>
      {block ? <pre className="copy-value copy-block" ref={ref} tabIndex={0}><code>{value}</code></pre>
        : <code className={`copy-value${secret ? ' is-secret' : ''}`} ref={ref} tabIndex={0}>{value}</code>}
      <p className="copy-msg" role="status" aria-live="polite">{msg}</p>
    </div>
  )
}

// The real session behind a Tested label. The picture is only ever passed in for a client the gateway marks tested.
export function ClientProof({ src }) {
  return (
    <figure className="client-fig">
      <img className="shot" src={src} width={3304} height={2970} loading="lazy"
        alt="A real Claude.ai conversation. Claude says the email was blocked because this task's permissions do not allow restricted data to leave the company." />
      <figcaption>A real Claude.ai session, 27 Oct 2026, free account: a send containing restricted stock figures was denied and nothing was delivered. One session, not a measurement.</figcaption>
    </figure>
  )
}
