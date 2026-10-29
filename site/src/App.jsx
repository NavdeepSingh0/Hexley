import { Suspense, lazy } from 'react'
import { Route, Routes } from 'react-router-dom'
import Layout from './components/Layout.jsx'
import Home from './pages/Home.jsx'
import HowItWorks from './pages/HowItWorks.jsx'
import Integrations from './pages/Integrations.jsx'
import Connect from './pages/Connect.jsx'
import Docs from './pages/Docs.jsx'
import Chat from './pages/Chat.jsx'
import Pricing from './pages/Pricing.jsx'
import Styleguide from './pages/Styleguide.jsx'
import Mascot from './pages/Mascot.jsx'

// The mascot lab is a development tool. import.meta.env.DEV is false in a production build, so the route and the page are
// removed from it (scripts/check-dev-only.mjs fails the build if any of it is left).
const MascotLab = import.meta.env.DEV ? lazy(() => import('./pages/MascotLab.jsx')) : null

// Pages that a later phase builds (docs/plans/BUILD_PLAN.md). Until then each says so plainly instead of pretending.
const LATER = [
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
        <Route path="/how-it-works" element={<HowItWorks />} />
        <Route path="/integrations" element={<Integrations />} />
        <Route path="/connect" element={<Connect />} />
        <Route path="/docs/*" element={<Docs />} />
        <Route path="/chat" element={<Chat />} />
        <Route path="/pricing" element={<Pricing />} />
        <Route path="/styleguide" element={<Styleguide />} />
        <Route path="/mascot" element={<Mascot />} />
        {MascotLab && <Route path="/mascot-lab" element={<Suspense fallback={null}><MascotLab /></Suspense>} />}
        {LATER.map(([to, title, phase]) => <Route key={to} path={to} element={<Soon title={title} phase={phase} />} />)}
        <Route path="*" element={<Soon title="Page not found" phase="-" />} />
      </Route>
    </Routes>
  )
}
