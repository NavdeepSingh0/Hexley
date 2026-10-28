import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { INTEGRATIONS, STATUS_LABEL } from '../data/integrations.js'
import { formatInterval, groupEvidence } from '../lib/evidence.js'

const STEPS = [
  {
    n: '1',
    title: 'The officer gives the agent one job',
    text: 'A permission slip names the task, the tools it may use and where data may go. Nothing starts until the officer confirms it.',
    shot: 'slip',
    alt: 'The permission slip screen of the Sentinel console: the task, the allowed tools, the allowed destination and the confirm button.',
    caption: 'The slip, as the console shows it.',
  },
  {
    n: '2',
    title: 'Every action is checked, live',
    text: 'The same poisoned document is given to three setups. Unprotected and standard access both leak; Sentinel denies the unsafe message and lets a clean one through.',
    shot: 'stage',
    alt: 'Three lanes side by side: Unprotected and Standard access both say LEAKED, Sentinel says DENIED.',
    caption: 'Replay mode: the model’s actions were recorded on 26 Oct 2026, Sentinel’s decisions are computed live.',
  },
  {
    n: '3',
    title: 'You can see exactly why',
    text: 'The denied step shows the rule in one sentence and highlights the values that would have left the building.',
    shot: 'why',
    alt: 'The side drawer explaining a denied step, with the restricted figures highlighted in the message the agent tried to send.',
    caption: 'Why the message was stopped.',
  },
]

function Shot({ name, alt }) {
  // One picture per theme; the other is hidden by CSS and, being lazy, never downloaded.
  const common = { width: 1280, height: 720, loading: 'lazy', alt }
  return (
    <>
      <img className="shot shot-dark" src={`/img/console-${name}-dark.png`} {...common} />
      <img className="shot shot-light" src={`/img/console-${name}-light.png`} {...common} />
    </>
  )
}

function Hero() {
  return (
    <section className="hero" aria-labelledby="hero-title">
      <div className="hero-text">
        <h1 id="hero-title" className="hero-title">The AI can only do the job you gave it.</h1>
        <p className="hero-lede">Sentinel checks every action an AI agent takes against a permission slip, and stops the ones the job never needed.</p>
        <div className="hero-actions">
          <a className="s-btn s-btn--primary s-btn--big" href="/console/">See it work</a>
          <Link className="s-btn s-btn--ghost s-btn--big" to="/connect">Connect Claude</Link>
        </div>
      </div>
      <div className="hero-mascot"><sentinel-mascot state="idle" size="200" /></div>
    </section>
  )
}

function Story() {
  return (
    <section className="block" aria-labelledby="story-title">
      <p className="s-label">How it works</p>
      <h2 id="story-title" className="block-title">One job, checked at every step</h2>
      <ol className="story">
        {STEPS.map((s, i) => (
          <li key={s.n} className={`story-step${i % 2 ? ' is-flipped' : ''}`}>
            <div className="story-copy">
              <span className="story-n" aria-hidden="true">{s.n}</span>
              <h3 className="story-title">{s.title}</h3>
              <p className="story-text">{s.text}</p>
            </div>
            <figure className="story-fig">
              <Shot name={s.shot} alt={s.alt} />
              <figcaption>{s.caption}</figcaption>
            </figure>
          </li>
        ))}
      </ol>
    </section>
  )
}

// Reads /evidence.json. If the file cannot be read the section says so; it never falls back to a number typed here.
function useEvidence() {
  const [state, setState] = useState({ status: 'loading', groups: [] })
  useEffect(() => {
    let live = true
    fetch('/evidence.json')
      .then((r) => { if (!r.ok) throw new Error(String(r.status)); return r.json() })
      .then((items) => { if (live) setState({ status: 'ready', ...groupEvidence(items) }) })
      .catch(() => { if (live) setState({ status: 'error', groups: [] }) })
    return () => { live = false }
  }, [])
  return state
}

function EvidenceCard({ g }) {
  const p = g.protectedItem
  const u = g.unprotectedItem
  return (
    <article className="s-panel evidence-card">
      <p className="s-label">{g.title}</p>
      <p className="evidence-big">{p.value}</p>
      <p className="evidence-what">got past Sentinel</p>
      {u && <p className="evidence-vs"><strong>{u.value}</strong> with no protection</p>}
      <p className="evidence-n">Sample size {p.n}. 95% interval {formatInterval(p.ci95)}.</p>
      <p className="evidence-caveat"><strong>What this is not:</strong> {p.caveat}</p>
    </article>
  )
}

function Evidence() {
  const ev = useEvidence()
  return (
    <section className="block" aria-labelledby="evidence-title">
      <p className="s-label">The evidence</p>
      <h2 id="evidence-title" className="block-title">Measured, with its limits</h2>
      {ev.status === 'loading' && <p className="muted" role="status">Loading the evidence file...</p>}
      {ev.status === 'error' && <p className="muted" role="status">The evidence file could not be loaded, so no numbers are shown.</p>}
      {ev.status === 'ready' && ev.groups.length === 0 && <p className="muted" role="status">The evidence file has no complete entries, so no numbers are shown.</p>}
      {ev.groups.length > 0 && <div className="evidence-grid">{ev.groups.map((g) => <EvidenceCard key={g.id} g={g} />)}</div>}
      <p className="evidence-more"><Link to="/docs#limits">Read what this does not prove</Link></p>
    </section>
  )
}

function Integrations() {
  return (
    <section className="block" aria-labelledby="int-title">
      <p className="s-label">Works with</p>
      <h2 id="int-title" className="block-title">Built on the MCP standard</h2>
      <ul className="int-list">
        {INTEGRATIONS.map((i) => (
          <li key={i.id} className="int-item">
            <span className={`s-badge${i.status === 'tested' ? ' s-badge--tested' : i.status === 'planned' ? ' s-badge--planned' : ''}`}>{STATUS_LABEL[i.status]}</span>
            <span className="int-name">{i.name}</span>
            <span className="int-note">{i.note}</span>
          </li>
        ))}
      </ul>
      <p className="evidence-more"><Link to="/integrations">All integrations</Link></p>
    </section>
  )
}

export default function Home() {
  return (
    <main>
      <Hero />
      <Story />
      <Evidence />
      <Integrations />
    </main>
  )
}
