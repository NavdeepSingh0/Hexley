import { Link } from 'react-router-dom'
import { Icon, PageHead } from '../components/Blocks.jsx'

// Illustrative only (docs/DESIGN_BRIEF.md section 7, BUILD_PLAN F8). Nothing here is offered, and nothing is sold: there is no
// button that buys, no sign-up and no payment. What the first column lists as existing is what the README marks as built;
// everything a paid plan would add is labelled Planned, not built, and is drawn with an empty marker instead of a tick.
const PLANS = [
  {
    id: 'self-host', name: 'Self-host', price: '$0', unit: 'you run it yourself', built: true,
    title: 'What exists today',
    items: ['The gateway and its rules', 'Permission slips and officer approvals', 'The signed, hash-chained audit log', 'This website, the console and Hexley Chat', 'Sign-in for Claude.ai and an access token for others'],
  },
  {
    id: 'team', name: 'Team', price: '$10', unit: 'per seat per month (illustrative)', built: false,
    title: 'Would add',
    items: ['A hosted gateway, so nothing runs on your machine', 'Several officers, each with their own sign-in', 'A phone page for approvals'],
  },
  {
    id: 'organisation', name: 'Organisation', price: 'By arrangement', text: true, unit: 'one-time licence (illustrative)', built: false,
    title: 'Would add',
    items: ['Several tool servers behind one gateway', 'Adapters for agents that do not use MCP', 'Support and a review of your own tools'],
  },
]

export default function Pricing() {
  return (
    <main>
      <PageHead label="Pricing" title="Pricing, illustrative." lede="Nothing on this page can be bought. It shows the shape of a business we could build around Hexley." />
      <section className="section" aria-labelledby="pricing-title">
        <div className="pr-banner" role="note">
          <span className="s-badge">Illustrative, not offered</span>
          <p id="pricing-title">Hexley is a hackathon project. These prices are placeholders to show how it could be packaged; we have not tested whether anyone would pay them, and there is no way to sign up.</p>
        </div>
        <ul className="pr-plans">
          {PLANS.map((p) => (
            <li key={p.id} className={`pr-plan${p.built ? ' pr-plan--now' : ''}`}>
              <p className="s-label">{p.name}</p>
              <p className={p.text ? 'pr-price pr-price--text' : 'pr-price'}>{p.price}</p>
              <p className="pr-unit">{p.unit}</p>
              <p className="pr-sub">{p.title}{!p.built && <span className="s-badge s-badge--planned">Planned, not built</span>}</p>
              <ul className="pr-items">
                {p.items.map((i) => (
                  <li key={i}>
                    {p.built ? <Icon name="check" size={18} className="pr-tick" /> : <span className="pr-dot" aria-hidden="true" />}
                    <span>{i}</span>
                  </li>
                ))}
              </ul>
            </li>
          ))}
        </ul>
        <p className="evidence-more">What exists, and what does not, is listed under <Link to="/docs/limits">limits and honest scope</Link>.</p>
      </section>
    </main>
  )
}
