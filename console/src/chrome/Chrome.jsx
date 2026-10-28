import { createElement, useEffect, useState } from 'react'
import { verifyView } from '../lib/derive.js'
import { getTheme, setTheme } from '../theme.js'

const SOURCE_NAME = { scripted: 'SCRIPTED', replay: 'REPLAY', live: 'LIVE' }

export function ThemeToggle() {
  const [theme, set] = useState(getTheme)
  const flip = () => {
    const next = theme === 'dark' ? 'light' : 'dark'
    setTheme(next)
    set(next)
  }
  return (
    <button className="btn btn-small" onClick={flip} aria-label={`Switch to the ${theme === 'dark' ? 'light' : 'dark'} theme`}>
      {theme === 'dark' ? 'LIGHT' : 'DARK'}
    </button>
  )
}

// The mascot is a framework-free Web Component the website ships (docs/contracts/MASCOT.md), served at /mascot/ once the API
// serves the site. If it is not there the slot simply stays empty: nothing in the console depends on it. It sits in the top bar,
// never over the stage, so it cannot cover the evidence. Its state comes only from real data (derive.mascotFor).
export function MascotSlot({ state, message }) {
  useEffect(() => {
    if (customElements.get('sentinel-mascot')) return
    // the website's copy first, then one next to the console (so the console also works on its own)
    const sources = ['/mascot/sentinel-mascot.js', `${import.meta.env.BASE_URL}mascot/sentinel-mascot.js`]
    sources.reduce((tried, url) => tried.catch(() => import(/* @vite-ignore */ url)), Promise.reject()).catch(() => {})
  }, [])
  const theme = document.documentElement.dataset.theme === 'light' ? 'light' : 'dark'
  return <div className="mascot-slot">{createElement('sentinel-mascot', { state, message, size: 64, theme })}</div>
}

export function TopBar({ view, lost, mascot }) {
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
      <ThemeToggle />
      {mascot ? <MascotSlot state={mascot.state} message={mascot.message} /> : null}
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
