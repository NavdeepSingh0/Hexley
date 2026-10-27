import { Link, Route, Routes } from 'react-router-dom'
import { getTheme, setTheme } from './theme.js'

// B0 scaffold: every route is a placeholder. The teammates build the real pages in phases A1 to A8
// (docs/plans/FRONTEND_PLAN.md). Keep the route list in sync with section 6 of that plan.
const ROUTES = [
  ['/', 'Home', 'A2'],
  ['/how-it-works', 'How it works', 'A3'],
  ['/integrations', 'Integrations', 'A3'],
  ['/docs', 'Docs', 'A4'],
  ['/pricing', 'Pricing', 'A5'],
  ['/connect', 'Connect', 'A5'],
  ['/chat', 'Sentinel Chat', 'A7'],
  ['/oauth/consent', 'OAuth consent', 'A8'],
  ['/styleguide', 'Styleguide (dev)', 'A1'],
  ['/mascot', 'Mascot (dev)', 'A6b'],
]

function Placeholder({ title, phase }) {
  return (
    <main className="placeholder">
      <p className="label">Placeholder · phase {phase}</p>
      <h1>{title}</h1>
      <p className="muted">This page is built in phase {phase} of the frontend plan.</p>
    </main>
  )
}

function Nav() {
  const toggle = () => setTheme(getTheme() === 'dark' ? 'light' : 'dark')
  return (
    <header className="nav">
      <Link to="/" className="brand">SENTINEL</Link>
      <nav>
        {ROUTES.slice(1, 7).map(([to, label]) => <Link key={to} to={to}>{label}</Link>)}
        <a href="/console/">See it work</a>
      </nav>
      <button className="ghost" onClick={toggle} aria-label="Toggle theme">Theme</button>
    </header>
  )
}

export default function App() {
  return (
    <>
      <Nav />
      <Routes>
        {ROUTES.map(([to, title, phase]) => (
          <Route key={to} path={to === '/docs' ? '/docs/*' : to} element={<Placeholder title={title} phase={phase} />} />
        ))}
        <Route path="*" element={<Placeholder title="Not found" phase="-" />} />
      </Routes>
    </>
  )
}
