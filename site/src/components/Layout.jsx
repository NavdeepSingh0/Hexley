import { Link, NavLink, Outlet, useLocation } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { getTheme, setTheme } from '../theme.js'

const LINKS = [
  ['/how-it-works', 'How it works'],
  ['/integrations', 'Integrations'],
  ['/docs', 'Docs'],
  ['/connect', 'Connect'],
  ['/chat', 'Chat'],
]

function ThemeButton() {
  // The page sets data-theme before React starts, so the label is read from the document, not guessed.
  const [theme, set] = useState(() => document.documentElement.dataset.theme || getTheme())
  const toggle = () => {
    const next = theme === 'dark' ? 'light' : 'dark'
    setTheme(next)
    set(next)
  }
  return (
    <button type="button" className="s-btn s-btn--ghost s-btn--small" onClick={toggle} aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`}>
      {theme === 'dark' ? 'Light' : 'Dark'}
    </button>
  )
}

function Nav() {
  return (
    <header className="site-nav">
      <Link to="/" className="site-logo">SENTINEL</Link>
      <nav className="site-links" aria-label="Main">
        {LINKS.map(([to, label]) => <NavLink key={to} to={to}>{label}</NavLink>)}
        <a href="/console/" className="site-see">See it work</a>
      </nav>
      <ThemeButton />
    </header>
  )
}

function Footer() {
  return (
    <footer className="site-footer">
      <p className="site-footer-line">Sentinel was built for Zinnovatio 4.0 by team 404 Disruptors. Every record, mailbox and document shown is synthetic.</p>
      <nav className="site-footer-links" aria-label="Footer">
        <Link to="/how-it-works">How it works</Link>
        <Link to="/integrations">Integrations</Link>
        <Link to="/docs">Docs</Link>
        <Link to="/pricing">Pricing (illustrative)</Link>
        <Link to="/docs#limits">What this does not prove</Link>
      </nav>
    </footer>
  )
}

// A page change starts at the top, and a #hash scrolls to its target once the page has rendered.
function ScrollToTop() {
  const { pathname, hash } = useLocation()
  useEffect(() => {
    if (hash) document.getElementById(hash.slice(1))?.scrollIntoView()
    else window.scrollTo(0, 0)
  }, [pathname, hash])
  return null
}

export default function Layout() {
  return (
    <div className="site-shell">
      <ScrollToTop />
      <Nav />
      <div className="site-main"><Outlet /></div>
      <Footer />
    </div>
  )
}
