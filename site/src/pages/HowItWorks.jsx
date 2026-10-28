import { Link } from 'react-router-dom'
import Story from '../components/Story.jsx'
import { PRECEDENCE, RULES } from '../data/rules.js'

// Slip, rules, approval, quarantine, audit: each with the real console screen it describes.
const STEPS = [
  {
    n: '1', id: 'slip', title: 'The permission slip',
    text: 'Before an agent starts, the officer confirms a slip: the task, the tools it may use, where data may go, and how many messages it may send. The agent cannot write or widen its own slip.',
    shot: 'slip', alt: 'The permission slip screen: the task, the allowed tools, the allowed destination, the message limit and the confirm button.',
    caption: 'The slip, as the console shows it.',
  },
  {
    n: '2', id: 'approval', title: 'The officer decides the sensitive ones',
    text: 'Some actions are held until the officer approves that exact request: what, to where, which data. If nobody answers, the answer is no.',
    shot: 'approval', alt: 'A dialog that reads NEEDS APPROVAL: change a vendor’s bank account, with Approve and Deny buttons.',
    caption: 'A bank-detail change waiting for the officer.',
  },
  {
    n: '3', id: 'quarantine', title: 'A persistent attacker is frozen',
    text: 'The third denied action in a session freezes it and revokes its token. That session can do nothing more; other sessions carry on.',
    shot: 'quarantine', alt: 'Three lanes: Unprotected and Standard access say LEAKED, Sentinel says QUARANTINED after three denied attempts.',
    caption: 'A scripted attacker, frozen after three denials.',
  },
  {
    n: '4', id: 'audit', title: 'Every decision is written down, signed',
    text: 'Each decision is added to a signed, hash-chained log before anything is forwarded. Change one record and the check fails. It shows that a record was altered; it cannot show the record was true.',
    shot: 'audit', alt: 'The audit screen reading INTACT, with buttons to verify the log or change one record.',
    caption: 'Verify the log, then change one record and verify again.',
  },
]

function Rules() {
  return (
    <section className="block" id="rules" aria-labelledby="rules-title">
      <p className="s-label">The rules</p>
      <h2 id="rules-title" className="block-title">Seven rules, in plain English</h2>
      <ol className="rules">
        {RULES.map((r) => (
          <li key={r.id} className="rule">
            <span className="rule-id">{r.id}</span>
            <div>
              <h3 className="rule-title">{r.title}</h3>
              <p className="rule-text">{r.text}</p>
            </div>
            <span className="rule-out">{r.outcome}</span>
          </li>
        ))}
      </ol>
      <p className="evidence-more muted">{PRECEDENCE}</p>
      <p className="evidence-more"><Link to="/docs#limits">What the rules do not cover</Link></p>
    </section>
  )
}

export default function HowItWorks() {
  return (
    <main>
      <header className="page-head">
        <h1 className="page-title">One job, and nothing more.</h1>
        <p className="page-lede">Sentinel sits between an AI agent and its tools. Every action is checked against the slip before it happens.</p>
      </header>
      <section className="block" aria-labelledby="steps-title">
        <h2 id="steps-title" className="visually-hidden">The steps</h2>
        <Story steps={STEPS} />
      </section>
      <Rules />
    </main>
  )
}
