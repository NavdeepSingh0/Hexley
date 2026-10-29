import { useEffect, useState } from 'react'
import { Link, Navigate, NavLink, useLocation, useParams } from 'react-router-dom'
import { Icon } from '../components/Blocks.jsx'
import { GROUPS, LEGACY, ORDER, PAGES } from '../data/docs.jsx'

// The documentation (UI v2, U4): a grouped sidebar, one big rounded panel, and an "On this page" rail that follows the reader.
// One route (`/docs/*`); the page is the first path segment after /docs, and `/docs#limits`-style links from before still work.
function Nav({ current }) {
  return (
    <nav aria-label="Documentation" className="dx-nav">
      {GROUPS.map((g) => (
        <div key={g.label} className="dx-group">
          <p className="s-label dx-group-label">{g.label}</p>
          {g.pages.map(([slug, label]) => (
            <NavLink key={slug} to={slug === 'overview' ? '/docs' : `/docs/${slug}`} end className={`dx-link${current === slug ? ' is-current' : ''}`} aria-current={current === slug ? 'page' : undefined}>{label}</NavLink>
          ))}
        </div>
      ))}
    </nav>
  )
}

// The h2 headings of the page that is showing, and which one the reader is at.
function useHeadings(slug) {
  const [items, setItems] = useState([])
  const [active, setActive] = useState('')
  useEffect(() => {
    const hs = [...document.querySelectorAll('.dx-body h2[id]')]
    setItems(hs.map((h) => ({ id: h.id, text: h.textContent })))
    setActive(hs[0]?.id ?? '')
    if (typeof IntersectionObserver === 'undefined' || hs.length === 0) return undefined
    const seen = new Map()
    const io = new IntersectionObserver((entries) => {
      for (const e of entries) seen.set(e.target.id, e.isIntersecting ? e.boundingClientRect.top : null)
      const open = [...seen.entries()].filter(([, top]) => top !== null).sort((a, b) => a[1] - b[1])
      if (open.length) setActive(open[0][0])
    }, { rootMargin: '-96px 0px -60% 0px' })
    hs.forEach((h) => io.observe(h))
    // Short last sections never reach the observed band, so at the very bottom of the page the last heading is the one marked.
    const bottom = () => { if (window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 8) setActive(hs.at(-1).id) }
    window.addEventListener('scroll', bottom, { passive: true })
    return () => { io.disconnect(); window.removeEventListener('scroll', bottom) }
  }, [slug])
  return { items, active }
}

export default function Docs() {
  const { '*': rest } = useParams()
  const { hash, pathname } = useLocation()
  const slug = rest ? rest.replace(/\/$/, '') : 'overview'
  const page = PAGES[slug]
  const { items, active } = useHeadings(slug)

  // An old link such as /docs#limits goes to the page that now holds that section.
  if (!rest && hash && LEGACY[hash.slice(1)] && LEGACY[hash.slice(1)] !== 'overview') {
    return <Navigate to={`/docs/${LEGACY[hash.slice(1)]}`} replace />
  }
  if (!page) {
    return (
      <main className="dx dx--single">
        <article className="dx-panel"><h1 className="dx-title">That page is not in the docs</h1><p className="dx-lede"><Link to="/docs">Back to the overview</Link></p></article>
      </main>
    )
  }
  const i = ORDER.indexOf(slug)
  const prev = i > 0 ? ORDER[i - 1] : null
  const next = i < ORDER.length - 1 ? ORDER[i + 1] : null
  const label = (s) => GROUPS.flatMap((g) => g.pages).find(([k]) => k === s)?.[1]
  const to = (s) => (s === 'overview' ? '/docs' : `/docs/${s}`)

  return (
    <main className="dx">
      <aside className="dx-side"><Nav current={slug} /></aside>
      <details className="dx-menu">
        <summary><Icon name="menu" size={16} /> Docs menu: <strong>{label(slug)}</strong></summary>
        <Nav current={slug} />
      </details>
      <article className="dx-panel">
        <p className="s-label">Documentation</p>
        <h1 className="dx-title">{page.title}</h1>
        <p className="dx-lede">{page.lede}</p>
        <div className="dx-body">{page.body()}</div>
        <p className="dx-source">Source: {page.source}</p>
        <nav className="dx-pager" aria-label="Previous and next page">
          {prev ? <Link to={to(prev)} className="dx-pager-link"><span className="muted">Previous</span><span>{label(prev)}</span></Link> : <span />}
          {next ? <Link to={to(next)} className="dx-pager-link dx-pager-next"><span className="muted">Next</span><span>{label(next)}</span></Link> : <span />}
        </nav>
      </article>
      <aside className="dx-rail" aria-label="On this page">
        {items.length > 0 && (
          <>
            <p className="dx-rail-head"><Icon name="list" size={16} /> On this page</p>
            <ul>
              {items.map((h) => (
                <li key={h.id}><Link to={{ pathname, hash: `#${h.id}` }} className={active === h.id ? 'is-active' : ''} aria-current={active === h.id ? 'location' : undefined}>{h.text}</Link></li>
              ))}
            </ul>
          </>
        )}
      </aside>
    </main>
  )
}
