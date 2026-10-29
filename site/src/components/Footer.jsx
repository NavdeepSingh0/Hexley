import { Link } from 'react-router-dom'

// Four columns and one honest line. Every link goes to a page that exists.
const COLUMNS = [
  ['Product', [['/how-it-works', 'How it works'], ['/integrations', 'Integrations'], ['/connect', 'Connect'], ['/chat', 'Chat']]],
  ['Learn', [['/docs', 'Docs'], ['/docs/faq', 'Questions judges ask'], ['/pricing', 'Pricing (illustrative)']]],
  ['Evidence and honesty', [['/#evidence', 'Measured results'], ['/docs/limits', 'What this does not prove']]],
]

export default function Footer() {
  return (
    <footer className="footer">
      <div className="footer-inner">
        <div className="footer-brand">
          <p className="footer-word">SENTINEL</p>
          <p className="footer-line">Built for Zinnovatio 4.0 by team 404 Disruptors. Every record, mailbox and document shown is synthetic.</p>
        </div>
        {COLUMNS.map(([title, links]) => (
          <nav key={title} className="footer-col" aria-label={title}>
            <p className="s-label">{title}</p>
            {links.map(([to, label]) => <Link key={to} to={to}>{label}</Link>)}
          </nav>
        ))}
        <nav className="footer-col" aria-label="Project">
          <p className="s-label">Project</p>
          <a href="/console/">The console</a>
          <span className="muted">Team 404 Disruptors</span>
        </nav>
      </div>
    </footer>
  )
}
