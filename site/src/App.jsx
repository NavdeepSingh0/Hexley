import { Route, Routes } from 'react-router-dom'
import Layout from './components/Layout.jsx'
import Home from './pages/Home.jsx'
import Styleguide from './pages/Styleguide.jsx'
import Mascot from './pages/Mascot.jsx'

// Pages that a later phase builds (docs/plans/BUILD_PLAN.md). Until then each says so plainly instead of pretending.
const LATER = [
  ['/how-it-works', 'How it works', 'F4'],
  ['/integrations', 'Integrations', 'F4'],
  ['/connect', 'Connect', 'F4'],
  ['/docs/*', 'Docs', 'F5'],
  ['/chat', 'Sentinel Chat', 'F7b'],
  ['/oauth/consent', 'Officer approval', 'F4'],
  ['/pricing', 'Pricing', 'F8'],
]

function Soon({ title, phase }) {
  return (
    <main className="page-soon">
      <p className="s-label">Not built yet</p>
      <h1>{title}</h1>
      <p className="muted">This page is built in phase {phase} of the plan.</p>
    </main>
  )
}

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Home />} />
        <Route path="/styleguide" element={<Styleguide />} />
        <Route path="/mascot" element={<Mascot />} />
        {LATER.map(([to, title, phase]) => <Route key={to} path={to} element={<Soon title={title} phase={phase} />} />)}
        <Route path="*" element={<Soon title="Page not found" phase="-" />} />
      </Route>
    </Routes>
  )
}
