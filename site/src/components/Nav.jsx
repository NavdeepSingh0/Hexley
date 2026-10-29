import { useEffect, useRef, useState } from 'react'
import { Link, NavLink, useLocation } from 'react-router-dom'
import { getTheme, setTheme } from '../theme.js'
import { Icon } from './Blocks.jsx'

// The floating navbar: always visible, rounded, blurred. Two menus (Product, Resources) open by click; Escape, a click outside,
// a route change or moving focus away closes them; the arrow keys move between items. Below 860 px it is a menu button.
const MENUS = {
  product: {
    label: 'Product',
    items: [
      ['/how-it-works', 'How it works', 'The slip, the rules, approvals and the signed log'],
      ['/integrations', 'Integrations', 'What it connects to, and what we have tested'],
      ['/connect', 'Connect', 'Add Sentinel to your AI app'],
      ['/chat', 'Chat', 'Try an agent whose every call is checked'],
    ],
  },
  resources: {
    label: 'Resources',
    items: [
      ['/docs', 'Docs', 'Run it, the concepts, the rules, the API'],
      ['/docs#limits', 'Limits and honest scope', 'What Sentinel does and does not cover'],
      ['/docs#faq', 'Questions judges ask', 'Short answers, each with its source'],
      ['/#evidence', 'Evidence', 'Measured, with the sample size and the limits'],
    ],
  },
}

function ThemeButton() {
  const [theme, set] = useState(() => document.documentElement.dataset.theme || getTheme())
  const toggle = () => {
    const next = theme === 'dark' ? 'light' : 'dark'
    setTheme(next)
    set(next)
  }
  const to = theme === 'dark' ? 'light' : 'dark'
  return (
    <button type="button" className="nav-icon-btn" onClick={toggle} aria-label={`Switch to ${to} theme`} title={`Switch to ${to} theme`}>
      <Icon name={theme === 'dark' ? 'sun' : 'moon'} size={19} />
    </button>
  )
}

function Menu({ id, menu, open, setOpen }) {
  const ref = useRef(null)
  const isOpen = open === id
  const onKey = (e) => {
    const items = [...(ref.current?.querySelectorAll('[role="menuitem"]') ?? [])]
    const i = items.indexOf(document.activeElement)
    if (e.key === 'ArrowDown') { e.preventDefault(); (items[i + 1] ?? items[0])?.focus() }
    else if (e.key === 'ArrowUp') { e.preventDefault(); (items[i - 1] ?? items.at(-1))?.focus() }
    else if (e.key === 'Escape') { setOpen(null); ref.current?.querySelector('button')?.focus() }
  }
  return (
    <div className="nav-menu" ref={ref} onKeyDown={onKey}
      onBlur={(e) => { if (isOpen && !ref.current?.contains(e.relatedTarget)) setOpen(null) }}>
      <button type="button" className={`nav-link${isOpen ? ' is-open' : ''}`} aria-expanded={isOpen} aria-haspopup="menu"
        onClick={() => setOpen(isOpen ? null : id)}
        onKeyDown={(e) => { if (e.key === 'ArrowDown') { e.preventDefault(); setOpen(id); setTimeout(() => ref.current?.querySelector('[role="menuitem"]')?.focus(), 0) } }}>
        {menu.label} <Icon name="chevron" size={14} className="nav-chevron" />
      </button>
      {isOpen && (
        <div className="nav-panel" role="menu" aria-label={menu.label}>
          {menu.items.map(([to, title, text]) => (
            <Link key={to} to={to} role="menuitem" className="nav-panel-item">
              <span className="nav-panel-title">{title}</span>
              <span className="nav-panel-text">{text}</span>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}

export default function Nav() {
  const [open, setOpen] = useState(null) // 'product' | 'resources' | 'sheet' | null
  const { pathname, hash } = useLocation()
  const bar = useRef(null)
  useEffect(() => { setOpen(null) }, [pathname, hash])
  useEffect(() => {
    const away = (e) => { if (bar.current && !bar.current.contains(e.target)) setOpen(null) }
    const esc = (e) => { if (e.key === 'Escape') setOpen(null) }
    document.addEventListener('mousedown', away)
    document.addEventListener('keydown', esc)
    return () => { document.removeEventListener('mousedown', away); document.removeEventListener('keydown', esc) }
  }, [])
  return (
    <header className="nav-wrap">
      <div className="nav" ref={bar}>
        <Link to="/" className="nav-brand" aria-label="Sentinel home">
          <span aria-hidden="true" className="nav-mark"><sentinel-mascot state="idle" size="30" still="" /></span>
          <span className="nav-word">SENTINEL</span>
        </Link>
        <nav className="nav-links" aria-label="Main">
          <Menu id="product" menu={MENUS.product} open={open} setOpen={setOpen} />
          <NavLink to="/docs" className="nav-link">Docs</NavLink>
          <NavLink to="/pricing" className="nav-link">Pricing</NavLink>
          <Menu id="resources" menu={MENUS.resources} open={open} setOpen={setOpen} />
        </nav>
        <div className="nav-right">
          <ThemeButton />
          <a href="/console/" className="nav-cta">See it work</a>
          <button type="button" className="nav-icon-btn nav-burger" aria-label={open === 'sheet' ? 'Close the menu' : 'Open the menu'} aria-expanded={open === 'sheet'}
            onClick={() => setOpen(open === 'sheet' ? null : 'sheet')}>
            <Icon name={open === 'sheet' ? 'close' : 'menu'} size={20} />
          </button>
        </div>
        {open === 'sheet' && (
          <div className="nav-sheet">
            {Object.values(MENUS).map((m) => (
              <div key={m.label} className="nav-sheet-group">
                <p className="s-label">{m.label}</p>
                {m.items.map(([to, title]) => <Link key={to} to={to} className="nav-sheet-link">{title}</Link>)}
              </div>
            ))}
            <div className="nav-sheet-group">
              <Link to="/docs" className="nav-sheet-link">Docs</Link>
              <Link to="/pricing" className="nav-sheet-link">Pricing</Link>
              <a href="/console/" className="nav-sheet-link">See it work</a>
            </div>
          </div>
        )}
      </div>
    </header>
  )
}
