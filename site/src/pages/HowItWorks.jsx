import { Link } from 'react-router-dom'
import { Feature, Icon, IconBlock, Outcome, PageHead, RulesCard } from '../components/Blocks.jsx'
import CtaBand from '../components/CtaBand.jsx'
import { Shot } from '../components/Ui.jsx'
import { PRECEDENCE, RULES } from '../data/rules.js'

// The four decision words, each with what it means for the agent. The same words are used in the console, the chat and the log.
const OUTCOMES = [
  ['ALLOWED', 'Inside the slip, and nothing restricted leaves. The call goes through to the tool.'],
  ['DENIED', 'A rule refused it. The agent is told why in one plain sentence, and nothing is forwarded.'],
  ['NEEDS APPROVAL', 'Held until the officer approves that exact request. If nobody answers, the answer is no.'],
  ['QUARANTINED', 'The session was frozen and its token revoked. It can do nothing more.'],
]

// One action, left to right: the agent asks, Sentinel decides, the tool runs only on a yes. Below, the four ways it can end.
function Flow() {
  return (
    <section className="section" aria-labelledby="flow-title">
      <p className="s-label">The path of one action</p>
      <h2 id="flow-title" className="section-title">Every action goes through the same gate</h2>
      <div className="flow">
        <ol className="flow-row" aria-label="Where an action goes">
          <li className="flow-node">
            <span className="flow-icon"><Icon name="chat" size={22} /></span>
            <strong>The AI agent</strong>
            <span>asks to use a tool, for example to send an e-mail.</span>
          </li>
          <li className="flow-arrow" aria-hidden="true"><Icon name="arrow" size={22} /></li>
          <li className="flow-node flow-node--gate">
            <span className="flow-icon"><Icon name="shield" size={22} /></span>
            <strong>Sentinel</strong>
            <span>checks it against the slip, then writes the decision to the signed log.</span>
          </li>
          <li className="flow-arrow" aria-hidden="true"><Icon name="arrow" size={22} /></li>
          <li className="flow-node">
            <span className="flow-icon"><Icon name="plug" size={22} /></span>
            <strong>Your tools</strong>
            <span>run only if the answer is yes. In the demo, only the gateway can reach them.</span>
          </li>
        </ol>
        <ul className="flow-outcomes" aria-label="The four decisions">
          {OUTCOMES.map(([word, text]) => (
            <li key={word} className="flow-outcome">
              <Outcome word={word} />
              <p>{text}</p>
            </li>
          ))}
        </ul>
      </div>
      <p className="flow-note muted">No AI model makes any of these decisions. The checks are ordinary code that runs outside the model, so a document the model reads cannot talk them out of it.</p>
    </section>
  )
}

// The seven rules, each in a sentence or two, in the order the engine names them.
function RulesList() {
  return (
    <section className="section" id="rules" aria-labelledby="rules-title">
      <p className="s-label">The rules</p>
      <h2 id="rules-title" className="section-title">Seven rules, in plain English</h2>
      <ol className="hr-rules">
        {RULES.map((r) => (
          <li key={r.id} className="hr-rule">
            <span className="hr-rule-id">{r.id}</span>
            <div className="hr-rule-body">
              <h3 className="hr-rule-title">{r.title}</h3>
              <p>{r.text}</p>
            </div>
            <Outcome word={r.outcome} />
          </li>
        ))}
      </ol>
      <p className="hr-note muted">{PRECEDENCE}</p>
      <p className="evidence-more"><Link to="/docs/rules">Each rule with an example and what it does not catch <Icon name="arrow" size={14} /></Link></p>
    </section>
  )
}

function NotCovered() {
  return (
    <section className="section" aria-labelledby="limits-title">
      <p className="s-label">Honest scope</p>
      <h2 id="limits-title" className="section-title">What it does not do</h2>
      <div className="icon-blocks">
        <IconBlock icon="shield" title="It can still be wrong" link={{ to: '/docs/limits', label: 'Limits and honest scope' }}>
          <p>A reworded paraphrase of confidential prose can get through value matching. It is listed as a declared gap and counted apart.</p>
        </IconBlock>
        <IconBlock icon="list" title="The log shows change, not truth" link={{ to: '/docs/concepts#audit', label: 'The audit log' }}>
          <p>The check shows if a record was altered, deleted or reordered. It cannot show that a recorded event was true.</p>
        </IconBlock>
        <IconBlock icon="lock" title="Some channels stay open" link={{ to: '/docs/concepts#hardened', label: 'Hardened mode' }}>
          <p>The narrower set-up shrinks the e-mail channel a lot. It does not remove every covert channel: which calls are made, their timing, retries.</p>
        </IconBlock>
      </div>
    </section>
  )
}

export default function HowItWorks() {
  return (
    <main>
      <PageHead label="How it works" title="One job, and nothing more." lede="Sentinel sits between an AI agent and its tools. Every action is checked against a permission slip before it happens, by ordinary code and not by another AI." />
      <Flow />
      <Feature
        id="slip" label="1 · The slip" title="The officer writes the job down first"
        bullets={['The agent cannot create or widen the slip', 'The token the agent holds is bound to the confirmed slip, so a changed slip is a different token', 'A tool nobody has classified is invisible to the agent and refused', 'The slip has a lifetime: when it runs out, the slip is spent']}
        link={{ to: '/docs/concepts#slip', label: 'Concepts: the permission slip' }}
        visual={<Shot name="slip" alt="The permission slip screen: the task, the allowed tools, the allowed destination, the message limit and the confirm button." />}
      >
        <p>Before an agent reads anything untrusted, the officer confirms a slip: the task, the tools it may use, where data may go, which places count as internal, and how many messages it may send.</p>
      </Feature>
      <Feature
        id="rules-summary" flip label="2 · The rules" title="Seven rules, checked on every action"
        bullets={['The strictest outcome wins: freeze, then deny, then ask, then allow', 'The rules look at the slip, where the data came from and where it is going; none reads a document for instructions', 'Each rule has tests, and a check that they fail when the rule is removed']}
        link={{ to: '#rules', label: 'Every rule in plain English' }}
        visual={<RulesCard />}
      >
        <p>Ordinary code checks each action against the slip. A value the agent read from a restricted source may not leave the building, and an address that only appears in a document is not used.</p>
      </Feature>
      <Feature
        id="approval" label="3 · The officer decides" title="Sensitive actions wait for a person"
        bullets={['An approval works once, expires, and is bound to the exact arguments; a changed argument needs a new approval', 'Silence is a no', 'Every other rule still runs after an approval, so an approval cannot excuse a leak']}
        link={{ to: '/docs/concepts#approvals', label: 'Concepts: officer approvals' }}
        visual={<Shot name="approval" alt="A dialog that reads NEEDS APPROVAL: change a vendor's bank account, with Approve and Deny buttons." />}
      >
        <p>Some actions, such as changing a vendor's bank account, are held until the officer approves that exact request: what it is, where it goes and which data it carries.</p>
      </Feature>
      <Feature
        id="quarantine" flip label="4 · Quarantine" title="A persistent attacker is frozen"
        bullets={['The freeze is per session: other sessions and other work are not affected', 'A frozen session cannot be refreshed', 'In the screenshot, a scripted attacker leaks through the first two setups and is frozen by Sentinel']}
        link={{ to: '/docs/concepts#quarantine', label: 'Concepts: quarantine' }}
        visual={<Shot name="quarantine" alt="Three lanes: Unprotected and Standard access say LEAKED, Sentinel says QUARANTINED after three denied attempts." />}
      >
        <p>The third denied action in one session freezes that session and revokes its token.</p>
      </Feature>
      <Feature
        id="audit" label="5 · The record" title="Every decision is written down, signed"
        bullets={['Change, delete or reorder a record and the check fails', 'If the write is slow or fails, the action is refused', 'Verify it in the console, or in the chat’s Details drawer']}
        link={{ to: '/docs/concepts#audit', label: 'Concepts: the audit log' }}
        visual={<Shot name="audit" alt="The audit screen reading INTACT, with buttons to verify the log or change one record." />}
      >
        <p>Each decision is added to a signed, hash-chained log before anything is forwarded.</p>
      </Feature>
      <RulesList />
      <NotCovered />
      <CtaBand />
    </main>
  )
}
