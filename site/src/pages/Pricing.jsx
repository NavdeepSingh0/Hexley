import { Link } from 'react-router-dom'

// Illustrative only (docs/DESIGN_BRIEF.md section 7, BUILD_PLAN F8). Nothing here is offered, and nothing is sold: there is no
// button that buys, no sign-up and no payment. What each column lists as existing is what the README marks as built;
// everything a paid plan would add is labelled Planned, not built.
const PLANS = [
  {
    id: 'self-host', name: 'Self-host', price: '$0', unit: 'you run it yourself', status: null,
    title: 'What exists today',
    items: ['The gateway and its rules', 'Permission slips and officer approvals', 'The signed, hash-chained audit log', 'This website, the console and Sentinel Chat', 'Sign-in for Claude.ai and an access token for others'],
  },
  {
    id: 'team', name: 'Team', price: '$10', unit: 'per seat per month (illustrative)', status: 'planned',
    title: 'Would add (planned, not built)',
    items: ['A hosted gateway, so nothing runs on your machine', 'Several officers, each with their own sign-in', 'A phone page for approvals'],
  },
  {
    id: 'organisation', name: 'Organisation', price: 'By arrangement', text: true, unit: 'one-time licence (illustrative)', status: 'planned',
    title: 'Would add (planned, not built)',
    items: ['Several tool servers behind one gateway', 'Adapters for agents that do not use MCP', 'Support and a review of your own tools'],
  },
]

export default function Pricing() {
  return (
    <main>
      <header className="page-head">
        <h1 className="page-title">Pricing, illustrative.</h1>
        <p className="page-lede">Nothing on this page can be bought. It shows the shape of a business we could build around Sentinel.</p>
      </header>
      <section className="block" aria-labelledby="pricing-title">
        <div className="s-panel pricing-banner" role="note">
          <span className="s-badge">Illustrative, not offered</span>
          <p id="pricing-title">Sentinel is a hackathon project. These prices are placeholders to show how it could be packaged; we have not tested whether anyone would pay them, and there is no way to sign up.</p>
        </div>
        <ul className="plan-list">
          {PLANS.map((p) => (
            <li key={p.id} className="s-panel plan">
              <p className="s-label">{p.name}</p>
              <p className={p.text ? 'plan-price plan-price--text' : 'plan-price'}>{p.price}</p>
              <p className="muted plan-unit">{p.unit}</p>
              <p className="plan-title">{p.title}{p.status === 'planned' && <span className="s-badge s-badge--planned plan-badge">Planned</span>}</p>
              <ul className="plan-items">{p.items.map((i) => <li key={i}>{i}</li>)}</ul>
            </li>
          ))}
        </ul>
        <p className="evidence-more">What exists, and what does not, is listed under <Link to="/docs#limits">limits and honest scope</Link>.</p>
      </section>
    </main>
  )
}
