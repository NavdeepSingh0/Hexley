import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Icon } from '../Blocks.jsx'
import { MODES, ago } from '../../lib/chat.js'
import { getTheme, setTheme } from '../../theme.js'

function ThemeRow() {
  const [theme, set] = useState(() => document.documentElement.dataset.theme || getTheme())
  const to = theme === 'dark' ? 'light' : 'dark'
  return (
    <button type="button" className="cx-side-btn" onClick={() => { setTheme(to); set(to) }}>
      <Icon name={theme === 'dark' ? 'sun' : 'moon'} size={17} /> {theme === 'dark' ? 'Light theme' : 'Dark theme'}
    </button>
  )
}

// Left column: the way home, a New chat button, the chats started in this browser, and the settings that rarely change.
export default function Sidebar({ chats, activeId, onNew, onOpen, onRemove, mode, setMode, open, onClose }) {
  return (
    <>
      {open && <div className="cx-scrim" onClick={onClose} aria-hidden="true" />}
      <aside className={`cx-side${open ? ' is-open' : ''}`} aria-label="Chats">
        <div className="cx-side-top">
          <Link to="/" className="cx-brand" aria-label="Hexley home">
            <span aria-hidden="true" className="cx-brand-mark"><sentinel-mascot state="idle" size="28" still="" /></span>
            <span className="cx-brand-word">HEXLEY</span>
          </Link>
          <button type="button" className="cx-icon-btn cx-side-close" onClick={onClose} aria-label="Close the chat list"><Icon name="close" size={18} /></button>
        </div>
        <button type="button" className="cx-new" onClick={onNew}><Icon name="chat" size={17} /> New chat</button>
        <p className="s-label cx-side-label">Chats</p>
        <nav className="cx-chats" aria-label="Your chats">
          {chats.length === 0 && <p className="muted cx-chats-empty">Chats you start here are listed, so you can come back to them.</p>}
          {chats.map((c) => (
            <div key={c.id} className={`cx-chat-item${c.id === activeId ? ' is-active' : ''}`}>
              <button type="button" className="cx-chat-open" onClick={() => onOpen(c.id)} aria-current={c.id === activeId ? 'page' : undefined}>
                <span className="cx-chat-title">{c.title}</span>
                <span className="cx-chat-meta">
                  {c.status === 'quarantined' && <span className="cx-chat-flag">Quarantined</span>}
                  {c.ts ? ago(c.ts) : ''}
                </span>
              </button>
              <button type="button" className="cx-chat-remove" onClick={() => onRemove(c.id)} aria-label={`Remove ${c.title} from the list`}><Icon name="close" size={14} /></button>
            </div>
          ))}
        </nav>
        <div className="cx-side-foot">
          <label className="cx-model">
            <span className="s-label">Model</span>
            <select value={mode} onChange={(e) => setMode(e.target.value)} aria-label="Where the model's replies come from">
              {MODES.map(([v, label]) => <option key={v} value={v}>{label}</option>)}
            </select>
          </label>
          <Link to="/docs" className="cx-side-btn"><Icon name="book" size={17} /> Docs</Link>
          <ThemeRow />
        </div>
      </aside>
    </>
  )
}
