// Shared building blocks for the website (UI v2, docs/plans/UI_V2_PLAN.md): icons, the lavender frame, alternating feature
// sections, an accessible accordion, an icon block. Plain markup and the tokens in design/tokens.css; no library.
import { Link } from 'react-router-dom'
import { RULES } from '../data/rules.js'

const PATHS = {
  plug: 'M9 3v4M15 3v4M6 7h12v4a6 6 0 0 1-12 0V7ZM12 17v4',
  shield: 'M12 3l7 3v5c0 5-3 8-7 10-4-2-7-5-7-10V6l7-3ZM9 12l2 2 4-4',
  laptop: 'M5 6h14v9H5V6ZM3 19h18M9 19l.5-4h5l.5 4',
  arrow: 'M5 12h14M13 6l6 6-6 6',
  chevron: 'M6 9l6 6 6-6',
  menu: 'M4 7h16M4 12h16M4 17h16',
  close: 'M6 6l12 12M18 6L6 18',
  sun: 'M12 4V2M12 22v-2M4 12H2M22 12h-2M5.6 5.6 4.2 4.2M19.8 19.8l-1.4-1.4M18.4 5.6l1.4-1.4M4.2 19.8l1.4-1.4M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8Z',
  moon: 'M20 14.5A8 8 0 0 1 9.5 4 8 8 0 1 0 20 14.5Z',
  check: 'M5 12l5 5 9-10',
  book: 'M5 4h11a3 3 0 0 1 3 3v13H8a3 3 0 0 1-3-3V4ZM5 17a3 3 0 0 1 3-3h11',
  chat: 'M4 5h16v11H9l-5 4V5Z',
  play: 'M8 5v14l11-7Z',
  lock: 'M7 11V8a5 5 0 0 1 10 0v3M5 11h14v9H5v-9Z',
  list: 'M9 6h11M9 12h11M9 18h11M4.5 6h.01M4.5 12h.01M4.5 18h.01',
}

export function Icon({ name, size = 22, className = '' }) {
  return (
    <svg className={`icon ${className}`} width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">
      <path d={PATHS[name] ?? PATHS.check} />
    </svg>
  )
}

// A big rounded lavender frame around product screenshots, the way a product page shows its real screens.
export function Frame({ children, className = '' }) {
  return <div className={`frame ${className}`}>{children}</div>
}

// Text on one side, something to look at on the other; `flip` swaps them. `visual` is any node (a screenshot, a card).
export function Feature({ id, label, title, children, bullets = [], link, visual, flip = false }) {
  return (
    <section id={id} className={`feature${flip ? ' is-flipped' : ''}`} aria-labelledby={id ? `${id}-h` : undefined}>
      <div className="feature-copy">
        {label && <p className="s-label">{label}</p>}
        <h2 id={id ? `${id}-h` : undefined} className="feature-title">{title}</h2>
        <div className="feature-text">{children}</div>
        {bullets.length > 0 && (
          <ul className="feature-bullets">
            {bullets.map((b) => <li key={b}><Icon name="check" size={18} className="feature-tick" /><span>{b}</span></li>)}
          </ul>
        )}
        {link && <Link className="feature-link" to={link.to}>{link.label} <Icon name="arrow" size={16} /></Link>}
      </div>
      <div className="feature-visual">{visual}</div>
    </section>
  )
}

// Questions that open and close. details/summary, so it works with the keyboard and without a script.
export function Accordion({ items }) {
  return (
    <div className="accordion">
      {items.map((it) => (
        <details key={it.q} className="accordion-item">
          <summary>{it.q}<span className="accordion-plus" aria-hidden="true" /></summary>
          <div className="accordion-body">{it.a}</div>
        </details>
      ))}
    </div>
  )
}

export function IconBlock({ icon, title, children, link }) {
  return (
    <article className="icon-block">
      <span className="icon-block-mark"><Icon name={icon} size={26} /></span>
      <h3 className="icon-block-title">{title}</h3>
      <div className="icon-block-text">{children}</div>
      {link && <Link className="icon-block-link" to={link.to}>{link.label} <Icon name="arrow" size={15} /></Link>}
    </article>
  )
}

// The top of an inner page: a small label, a heading in the display face and one sentence.
export function PageHead({ label, title, lede }) {
  return (
    <header className="pg-head">
      {label && <p className="s-label">{label}</p>}
      <h1 className="pg-h1">{title}</h1>
      {lede && <p className="pg-lede">{lede}</p>}
    </header>
  )
}

// The four decision words, each in its own colour. Used as a legend beside the rules, not as a claim about any one action.
export const OUTCOME_CLASS = { ALLOWED: 'allowed', DENIED: 'denied', 'NEEDS APPROVAL': 'approval', QUARANTINED: 'quarantined' }
export function Outcome({ word }) {
  return <span className={`rules-card-out rules-card-out--${OUTCOME_CLASS[word] ?? 'denied'}`}>{word}</span>
}

// The nine rules as a short list: id, title and the decision word each one produces.
export function RulesCard() {
  return (
    <ol className="rules-card" aria-label="The nine rules">
      {RULES.map((r) => (
        <li key={r.id}>
          <span className="rules-card-id">{r.id}</span>
          <span className="rules-card-title">{r.title}</span>
          <Outcome word={r.outcome} />
        </li>
      ))}
    </ol>
  )
}
