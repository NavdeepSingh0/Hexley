import { Suspense, lazy } from 'react'
import { Link, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout.jsx'
import Home from './pages/Home.jsx'
import HowItWorks from './pages/HowItWorks.jsx'
import Integrations from './pages/Integrations.jsx'
import Connect from './pages/Connect.jsx'
import Docs from './pages/Docs.jsx'
import Chat from './pages/Chat.jsx'
import Pricing from './pages/Pricing.jsx'

// The mascot lab, the mascot page and the styleguide are development tools. import.meta.env.DEV is false in a production build,
// so their routes and pages are removed from it (scripts/check-dev-only.mjs fails the build if any of it is left).
const MascotLab = import.meta.env.DEV ? lazy(() => import('./pages/MascotLab.jsx')) : null
const Mascot = import.meta.env.DEV ? lazy(() => import('./pages/Mascot.jsx')) : null
const Styleguide = import.meta.env.DEV ? lazy(() => import('./pages/Styleguide.jsx')) : null

function NotFound() {
  return (
    <main className="page-soon">
      <p className="s-label">404</p>
      <h1>Page not found</h1>
      <p className="muted">There is nothing at this address. <Link to="/">Go to the home page</Link>.</p>
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
        <Route path="/pricing" element={<Pricing />} />
        {Styleguide && <Route path="/styleguide" element={<Suspense fallback={null}><Styleguide /></Suspense>} />}
        {Mascot && <Route path="/mascot" element={<Suspense fallback={null}><Mascot /></Suspense>} />}
        {MascotLab && <Route path="/mascot-lab" element={<Suspense fallback={null}><MascotLab /></Suspense>} />}
        <Route path="*" element={<NotFound />} />
      </Route>
      {/* The chat is an app screen: no marketing bar or footer around it. */}
      <Route path="/chat" element={<Chat />} />
    </Routes>
  )
}
