import { createElement, useEffect, useState } from 'react'
import '../../../design/mascot/sentinel-mascot.js'
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
    <button className="s-btn s-btn--ghost s-btn--small" onClick={flip} aria-label={`Switch to the ${theme === 'dark' ? 'light' : 'dark'} theme`}>
      {theme === 'dark' ? 'Light' : 'Dark'}
    </button>
  )
}

// The mascot is a framework-free Web Component (design/mascot/sentinel-mascot.js, docs/contracts/MASCOT.md), bundled with the
// console, so it needs no network. It sits in the top bar, never over the stage, so it cannot cover the evidence, and its
// words appear below it. Its state comes only from real data (derive.mascotFor): it decides nothing.
export function MascotSlot({ state, message }) {
  return <div className="mascot-slot">{createElement('sentinel-mascot', { state, message, size: 52, placement: 'below' })}</div>
}

// The top bar holds only: the name, where the agent's behaviour comes from, help, theme, the mascot.
export function TopBar({ view, lost, mascot, helpOpen, onHelp }) {
  return (
    <header className="topbar">
      <div className="logo">SENTINEL</div>
      {view ? <span className={`s-badge ${view.source === 'live' ? 's-badge--tested' : ''}`}>{SOURCE_NAME[view.source]}</span> : null}
      {lost ? <span className="s-badge lost" role="status">Connection lost, retrying</span> : null}
      <div className="spacer" />
      <button className="s-btn s-btn--ghost s-btn--small help-btn" onClick={onHelp} aria-expanded={helpOpen} aria-label="Presenter keys and help">?</button>
      <ThemeToggle />
      {mascot ? <MascotSlot state={mascot.state} message={mascot.message} /> : null}
    </header>
  )
}

// The officer's task in the officer's words, then the one honest line about where the agent's actions come from.
export function TaskLine({ view }) {
  const task = view.lanes[0]?.task
  return (
    <div className="task">
      <p className="s-label">{view.scenario.title}</p>
      <h1 className="task-text" title={task}>{task}</h1>
      <p className="task-note">{view.disclosure}</p>
    </div>
  )
}

export function PresenterHelp({ onClose, tamperEnabled }) {
  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])
  const keys = [
    ['Enter', 'The next step of the guided demo: confirm the slip, show why it was denied, continue'],
    ['N', 'Skip to the next situation'],
    ['V', 'Verify the audit log'],
    ...(tamperEnabled ? [['T', 'Change one record in the log, then press V to see it caught']] : []),
    ['?', 'Open or close this panel'],
    ['Esc', 'Close a panel without moving on'],
  ]
  return (
    <aside className="help s-panel s-panel--raised" role="dialog" aria-label="Presenter keys">
      <div className="help-head">
        <p className="s-label">Presenter keys</p>
        <button className="s-btn s-btn--ghost s-btn--small" onClick={onClose}>Close</button>
      </div>
      <dl className="help-keys">
        {keys.map(([k, text]) => (
          <div key={k}><dt><span className="s-kbd">{k}</span></dt><dd>{text}</dd></div>
        ))}
      </dl>
      <p className="s-label help-sub">Where the agent&rsquo;s behaviour comes from</p>
      <dl className="help-sources">
        <div><dt>SCRIPTED</dt><dd>a fixed, fully compromised agent: the same attack every time</dd></div>
        <div><dt>REPLAY</dt><dd>a real AI model&rsquo;s recorded behaviour; Sentinel still decides live</dd></div>
        <div><dt>LIVE</dt><dd>a real AI model right now (needs the model API; behaviour varies)</dd></div>
      </dl>
    </aside>
  )
}

// The finale of the guided demo: the audit log's state as one big word, then what to press.
export function AuditPanel({ verify, onVerify, onTamper, busy }) {
  const v = verifyView(verify)
  const word = v.tone === 'ok' ? ['INTACT', 'allowed'] : v.tone === 'bad' ? ['TAMPERED', 'harm'] : null
  return (
    <div className="s-panel is-active audit-panel">
      {word
        ? <p className={`s-verdict s-verdict--${word[1]} s-glow s-glow--${word[1]}`} role="status">{word[0]}</p>
        : <p className="s-verdict s-verdict--muted" role="status">Not checked yet</p>}
      <p className="lane-sentence">{word ? v.text : 'Press V to check every record against its signature and the chain.'}</p>
      <div className="audit-panel-actions">
        <button className="s-btn s-btn--primary" disabled={busy} onClick={onVerify}>Verify the log <span className="s-kbd">V</span></button>
        {verify?.tamper_enabled ? (
          <button className="s-btn s-btn--ghost" disabled={busy} onClick={onTamper}>Change one record <span className="s-kbd">T</span></button>
        ) : null}
      </div>
    </div>
  )
}

export function AuditBar({ verify, onVerify, onTamper, busy }) {
  const v = verifyView(verify)
  return (
    <footer className="auditbar">
      <span className={`audit-dot audit-${v.tone}`} aria-hidden="true" />
      <div className={`audit-state audit-${v.tone}`} role="status">{v.text}</div>
      <p className="s-label audit-label">Signed, hash-chained audit log</p>
      <button className="s-btn s-btn--ghost s-btn--small" disabled={busy} onClick={onVerify}>Verify <span className="s-kbd">V</span></button>
      {verify?.tamper_enabled ? (
        <button className="s-btn s-btn--ghost s-btn--small" disabled={busy} onClick={onTamper}>Tamper <span className="s-kbd">T</span></button>
      ) : null}
    </footer>
  )
}
