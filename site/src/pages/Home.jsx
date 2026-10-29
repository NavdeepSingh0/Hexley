import { Link } from 'react-router-dom'
import { Accordion, Feature, Frame, Icon, IconBlock } from '../components/Blocks.jsx'
import CtaBand from '../components/CtaBand.jsx'
import { Shot, StatusBadge } from '../components/Ui.jsx'
import { RULES } from '../data/rules.js'
import { FAQ } from '../data/faq.jsx'
import { STATUS_MEANING, groupByStatus, useConnect } from '../lib/connect.js'
import { formatInterval } from '../lib/evidence.js'
import { useEvidence } from '../lib/useEvidence.js'

// The "what's real" rail: three short facts, each read from the same data the rest of the site uses (the evidence file, the
// gateway's own client list). An item whose data has not loaded is left out, never replaced by a typed number.
function Rail() {
  const ev = useEvidence()
  const { data } = useConnect()
  const first = ev.groups[0]
  const tested = (data?.clients ?? []).filter((c) => c.status === 'tested').map((c) => c.name)
  return (
    <aside className="rail" aria-label="What is real">
      <p className="s-label rail-label">What's real</p>
      {first && (
        <Link to="/#evidence" className="rail-item">
          <span className="rail-title">{first.protectedItem.value} {first.title.toLowerCase()} got past Sentinel</span>
          <span className="rail-text">Sample size {first.protectedItem.n}. Read what this is not.</span>
        </Link>
      )}
      {tested.length > 0 && (
        <Link to="/integrations" className="rail-item">
          <span className="rail-title">Connected for real: {tested.join(' and ')}</span>
          <span className="rail-text">One session each, with the evidence kept.</span>
        </Link>
      )}
      <Link to="/docs" className="rail-item">
        <span className="rail-title">Run it yourself with one command</span>
        <span className="rail-text">python -m sentinel up --demo</span>
      </Link>
    </aside>
  )
}

function Hero() {
  return (
    <div className="hero-wrap">
      <section className="hero2" aria-labelledby="hero-title">
        <div className="hero2-text">
          <h1 id="hero-title" className="hero2-title">The AI can only do the job you gave it.</h1>
          <p className="hero2-lede">Sentinel checks every action an AI agent takes against a permission slip, and stops the ones the job never needed.</p>
          <div className="hero-actions">
            <a className="s-btn s-btn--primary s-btn--big" href="/console/">See it work</a>
            <Link className="s-btn s-btn--ghost s-btn--big" to="/docs">Read the docs</Link>
          </div>
        </div>
        <Rail />
      </section>
    </div>
  )
}

function Screens() {
  return (
    <section className="section section--tight" aria-label="The console">
      <Frame>
        <div className="frame-shots">
          <div className="frame-main"><Shot name="stage" alt="Three lanes side by side: Unprotected and Standard access both say LEAKED, Sentinel says DENIED." /></div>
          <div className="frame-side"><Shot name="why" alt="The side drawer explaining a denied step, with the restricted values underlined in the message the agent tried to send." /></div>
        </div>
      </Frame>
      <p className="frame-caption">The console, replaying a real model's actions on a poisoned quotation (recorded 26 Oct 2026); Sentinel's decisions are computed live.</p>
    </section>
  )
}

function RulesCard() {
  const kind = { DENIED: 'denied', 'NEEDS APPROVAL': 'approval', QUARANTINED: 'quarantined' }
  return (
    <ol className="rules-card" aria-label="The seven rules">
      {RULES.map((r) => (
        <li key={r.id}>
          <span className="rules-card-id">{r.id}</span>
          <span className="rules-card-title">{r.title}</span>
          <span className={`rules-card-out rules-card-out--${kind[r.outcome] ?? 'denied'}`}>{r.outcome}</span>
        </li>
      ))}
    </ol>
  )
}

function EvidenceCard({ g, primary }) {
  const p = g.protectedItem
  const u = g.unprotectedItem
  return (
    <article className={`s-panel evidence-card ${primary ? 'evidence-card--primary' : 'evidence-card--secondary'}`}>
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
    <section className="section" id="evidence" aria-labelledby="evidence-title">
      <p className="s-label">The evidence</p>
      <h2 id="evidence-title" className="section-title">Measured, with its limits</h2>
      {ev.status === 'loading' && <p className="muted" role="status">Loading the evidence file...</p>}
      {ev.status === 'error' && <p className="muted" role="status">The evidence file could not be loaded, so no numbers are shown.</p>}
      {ev.status === 'ready' && ev.groups.length === 0 && <p className="muted" role="status">The evidence file has no complete entries, so no numbers are shown.</p>}
      {ev.groups.length > 0 && <div className="evidence-grid">{ev.groups.map((g, i) => <EvidenceCard key={g.id} g={g} primary={i === 0} />)}</div>}
      <p className="evidence-more"><Link to="/docs/limits">Read what this does not prove</Link></p>
    </section>
  )
}

function Pillars() {
  const { data } = useConnect()
  const tested = (data?.clients ?? []).filter((c) => c.status === 'tested').map((c) => c.name)
  return (
    <section className="section" aria-labelledby="pillars-title">
      <h2 id="pillars-title" className="section-title section-title--center">Built for the way a careful team works</h2>
      <div className="icon-blocks">
        <IconBlock icon="plug" title="Built on a standard" link={{ to: '/integrations', label: 'See what is tested' }}>
          <p>Sentinel is an MCP gateway, so anything that speaks MCP can be routed through it.{tested.length > 0 ? ` ${tested.join(' and ')} have been connected for real; the rest are labelled as we have run them.` : ''}</p>
        </IconBlock>
        <IconBlock icon="shield" title="Every number has its limits" link={{ to: '/docs/limits', label: 'What this does not prove' }}>
          <p>Each result shows its sample size and a line saying what it is not. The cases were written by us, so a zero means "does what we say", not "no other route exists".</p>
        </IconBlock>
        <IconBlock icon="laptop" title="Runs on your machine" link={{ to: '/docs', label: 'Run it' }}>
          <p>One command starts the gateway, the console and this website. Everything shown is synthetic and the tools are mocks.</p>
        </IconBlock>
      </div>
    </section>
  )
}

function Integrations() {
  const { status, data } = useConnect()
  const rows = groupByStatus(data?.clients).flatMap((g) => g.clients.map((c) => ({ ...c, group: g.status })))
  return (
    <section className="section" aria-labelledby="int-title">
      <p className="s-label">Works with</p>
      <h2 id="int-title" className="section-title">Built on the MCP standard</h2>
      {status === 'loading' && <p className="muted" role="status">Loading...</p>}
      {status === 'error' && <p className="muted" role="status">The list of clients could not be loaded from Sentinel.</p>}
      {rows.length > 0 && (
        <ul className="int-list s-panel">
          {rows.map((c) => (
            <li key={c.id} className="int-item">
              <StatusBadge status={c.group} />
              <span className="int-name">{c.name}</span>
              <span className="int-note">{STATUS_MEANING[c.group]}</span>
            </li>
          ))}
        </ul>
      )}
      <p className="int-gloss muted">MCP is how AI apps connect to tools.</p>
      <p className="evidence-more"><Link to="/integrations">All integrations</Link></p>
    </section>
  )
}

export default function Home() {
  return (
    <main>
      <Hero />
      <Screens />
      <Feature
        id="slip" label="1 · The slip" title="One job, written down before it starts"
        bullets={['A tool that is not on the slip is refused, including a tool nobody has classified', 'Restricted data may only go to places the officer names as internal', 'A message limit and a lifetime: when they run out, the slip is spent']}
        link={{ to: '/how-it-works', label: 'How it works' }}
        visual={<Shot name="slip" alt="The permission slip screen: the task, the allowed tools, the allowed destination and the confirm button." />}
      >
        <p>Before an agent starts, the officer confirms a permission slip: the task, the tools it may use, where data may go and how many messages it may send. The agent cannot write or widen its own slip.</p>
      </Feature>
      <Feature
        id="rules" flip label="2 · The rules" title="Seven rules, checked on every action"
        bullets={['The strictest outcome wins: freeze, then deny, then ask, then allow', 'Known gaps are listed, not hidden: a reworded paraphrase can still get through value matching', 'Each rule has tests, and a check that they fail when the rule is removed']}
        link={{ to: '/how-it-works#rules', label: 'Every rule in plain English' }}
        visual={<RulesCard />}
      >
        <p>No model decides. Ordinary code checks each action against the slip, where the data came from and where it is going, and every decision is written to a signed log before anything is forwarded.</p>
      </Feature>
      <Feature
        id="proof" label="3 · The proof" title="See exactly why, and check the log"
        bullets={['A denied step shows the rule in one sentence and underlines the values that would have left', 'Held actions wait for the officer, and silence counts as a no', 'The third denial freezes the session and revokes its token']}
        link={{ to: '/chat', label: 'Try an agent in the chat' }}
        visual={<Shot name="audit" alt="The audit screen reading INTACT, with buttons to verify the log or change one record." />}
      >
        <p>The signed, hash-chained log shows if a record was altered, deleted or reordered. It cannot show that a record was true, and the site says so.</p>
      </Feature>
      <Evidence />
      <Pillars />
      <Integrations />
      <section className="section" aria-labelledby="faq-title">
        <h2 id="faq-title" className="section-title section-title--center">Questions judges ask</h2>
        <Accordion items={FAQ.slice(0, 6)} />
        <p className="evidence-more faq-more"><Link to="/docs/faq">All questions <Icon name="arrow" size={14} /></Link></p>
      </section>
      <CtaBand />
    </main>
  )
}
