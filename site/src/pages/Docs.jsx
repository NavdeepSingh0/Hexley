import { Link, useLocation } from 'react-router-dom'
import { CopyField } from '../components/Ui.jsx'

// Every section ends with the files its claims come from, so a reader (or a judge) can check them. Numbers are not typed
// here: measured results live in /evidence.json and are shown on the home page.
const INDEX = [
  ['getting-started', 'Getting started'],
  ['concepts', 'Concepts'],
  ['connect', 'Connecting a client'],
  ['own-tools', 'Your own tools'],
  ['limits', 'Limits and honest scope'],
  ['faq', 'Questions judges ask'],
]

function Section({ id, title, source, children }) {
  return (
    <section id={id} className="doc-section" aria-labelledby={`${id}-h`}>
      <h2 id={`${id}-h`} className="doc-h2">{title}</h2>
      {children}
      <p className="doc-source">Source: {source}</p>
    </section>
  )
}

function Faq({ q, children }) {
  return (
    <details className="faq">
      <summary>{q}</summary>
      <div className="faq-a">{children}</div>
    </details>
  )
}

const SETUP = `python -m pip install --user uv
python -m uv sync
npm --prefix console ci
npm --prefix console run build
npm --prefix site ci
npm --prefix site run build
python -m uv run python -m sentinel up --demo`

const CLASSIFY = `curl -X POST http://127.0.0.1:8000/api/v1/tools/update_vendor_bank/classify \\
  -H "Authorization: Bearer <officer token>" -H "Content-Type: application/json" \\
  -d '{"capability": "write", "outbound": false, "consequential": true,
       "output_integrity": "trusted", "output_confidentiality": "restricted",
       "requires_human_verification": true}'`

export default function Docs() {
  const { hash } = useLocation()
  return (
    <main>
      <header className="page-head">
        <h1 className="page-title">Docs.</h1>
        <p className="page-lede">What Sentinel does, how to run it, and exactly where its claims stop.</p>
      </header>
      <div className="docs">
        <nav className="docs-index" aria-label="On this page">
          <p className="s-label">On this page</p>
          <ul>
            {INDEX.map(([id, label]) => (
              <li key={id}><a href={`#${id}`} aria-current={hash === `#${id}` ? 'location' : undefined}>{label}</a></li>
            ))}
          </ul>
        </nav>
        <div className="docs-body">
          <Section id="getting-started" title="Getting started" source="README.md (Setup, Console), docs/MVP.md.">
            <p>Sentinel runs on your computer. You need Python, the <code>uv</code> package manager and Node. The demo uses synthetic data and needs no model API key in its scripted and replay modes; the live mode with a real model needs a key, which you keep in a local <code>.env</code> file that is never committed.</p>
            <CopyField label="Run it" value={SETUP} block />
            <p>The last command starts the tool server, the gateway and the API, and opens this website, served by the same program, and prints the links. The link carries the officer token in its address; the page moves it out of the address bar as soon as it opens, and the console (the "See it work" button) reuses it. <code>--demo</code> turns on the tamper button and starts a fresh audit log (the old one is kept aside).</p>
            <p>To let an AI app on the internet reach your gateway, add <code>--tunnel</code> (needs <code>cloudflared</code>) or <code>--public-url</code>. The address changes on every start.</p>
          </Section>

          <Section id="concepts" title="Concepts" source="README.md, docs/THREAT_MODEL.md sections 1 to 4, docs/DECISIONS.md (D-036, D-037).">
            <p><strong>The gateway.</strong> Sentinel is an MCP gateway: the AI agent talks to Sentinel, and Sentinel talks to the real tools. Every call is checked first. No language model makes any security decision; the checks are ordinary code.</p>
            <p><strong>The permission slip.</strong> The officer confirms a slip before the agent reads anything untrusted: the task, the tools it may use, where data may go and how many messages it may send. The agent cannot create or widen it. The session token is bound to the confirmed slip.</p>
            <p><strong>Four decisions.</strong> Every action ends as one of these, in the same words everywhere:</p>
            <ul className="doc-list">
              <li><strong>ALLOWED</strong>: inside the slip, nothing restricted leaves.</li>
              <li><strong>DENIED</strong>: a rule refused it, with a plain reason.</li>
              <li><strong>NEEDS APPROVAL</strong>: held until the officer approves that exact request. If nobody answers, the answer is no.</li>
              <li><strong>QUARANTINED</strong>: the session was frozen and its token revoked. Other sessions are not affected.</li>
            </ul>
            <p>The rules behind them are on <Link to="/how-it-works#rules">How it works</Link>. When more than one applies, the strictest wins.</p>
            <p><strong>Hardened mode.</strong> An optional narrower setup for the quotation task: the slip is bound to one work item, the agent gets a single tool that sends a fixed message, and Sentinel chooses the recipient. It shrinks the e-mail channel; it does not remove every covert channel.</p>
            <p><strong>The audit log.</strong> Every decision is written to a signed, hash-chained log before anything is forwarded; a slow or failed write refuses the action. The console can verify it and can change one record to show the check failing.</p>
          </Section>

          <Section id="connect" title="Connecting a client" source="docs/contracts/API.md (Connect), docs/DECISIONS.md D-036 and D-041, docs/PHASE_LOG.md rows B1 and F4.">
            <p>Two ways, both on the <Link to="/connect">Connect</Link> page, which reads its list from your running gateway:</p>
            <ul className="doc-list">
              <li><strong>Sign in (OAuth).</strong> The AI app adds Sentinel as a custom connector and chooses "Sign in now". The officer approves the permission slip on a page served by the gateway, with a six-digit code shown in the Sentinel terminal. This is the route we have run for real, once, with a free Claude.ai account.</li>
              <li><strong>Access token (header).</strong> The officer creates a short-lived token on the Connect page and pastes it into an app that lets you set a request header. It is the same session token, so it carries the same slip. No real client has been connected this way yet, so it is labelled "Should work".</li>
            </ul>
            <p>The labels on the <Link to="/integrations">Integrations</Link> page mean what they say: Tested is a real session with a screenshot, Should work speaks the same standard but has not been run, Planned is not built.</p>
          </Section>

          <Section id="own-tools" title="Your own tools" source="docs/contracts/API.md (Tools and slips for any task), docs/DECISIONS.md D-037 and D-038.">
            <p>Sentinel does not guess what a tool does. A tool that nobody has classified is invisible to the agent and refused. The officer lists the tools the tool server offers, with a first guess for each, and classifies the ones to allow:</p>
            <CopyField label="Classify a tool (officer action)" value={CLASSIFY} block />
            <p>The labels say whether the tool reads, writes or sends; whether it is consequential; whether its output is trusted and how confidential it is; which argument is the destination (for a tool that sends); and whether the officer must approve each call. A tool that sends must name its destination. Built-in tools cannot be weakened. Each classification is written to the audit log before it is saved.</p>
            <p>A slip for any task is built the same way (<code>POST /api/v1/slips</code>): the objective, the tools, the destinations (domains, web hosts or folders), which destinations count as internal, a message limit and a lifetime. Vague entries such as wildcards are refused.</p>
            <p>Limit: one tool server sits behind one gateway. Several upstream servers are not built.</p>
          </Section>

          <Section id="limits" title="Limits and honest scope" source="docs/THREAT_MODEL.md (all sections), README.md (Status, Measured results), docs/DECISIONS.md D-036 to D-041, docs/PHASE_LOG.md.">
            <p><strong>What is protected.</strong> An action is allowed only when the tool is on the slip, the destination is inside what the slip allows and did not come only from untrusted content, no restricted value the session has read leaves the building, and, after untrusted reading, a consequential action goes only to an internal destination or waits for the officer.</p>
            <p><strong>What Sentinel does not govern.</strong></p>
            <ul className="doc-list">
              <li>The model's own reply to the user. The gateway sees tool calls, not what the agent says in chat; in a hosted app that reply goes to the app's provider.</li>
              <li>Other capabilities the agent holds: another connector, a browser, a direct credential, a shell. For a real deployment the agent must hold no credential for what Sentinel is meant to govern.</li>
              <li>Covert channels: which calls are made, their timing, retries, send versus no-send.</li>
              <li>Whether the content of an allowed action is correct or wise. A slip that is too wide is enforced faithfully.</li>
            </ul>
            <p><strong>Known gaps, declared.</strong> A paraphrase of confidential text is not caught by value matching; digits spaced apart and a spelled-out address are listed as gaps in the evaluation. Text hidden in images needs OCR and is not covered. R7 can hold valid actions on a task that reads untrusted content and then acts often.</p>
            <p><strong>What is demo-grade.</strong> One static API token and a one-time officer code are not identity management. OAuth state is in memory with one officer. The audit log shows that a record was altered, deleted or reordered; it does not prove the events were true, and a truncated log is only noticed if the verifier holds the earlier chain head.</p>
            <p><strong>What the evidence is.</strong> The tools are our own mocks, not real file, browser or database servers. The test cases were written by us from the documented matcher list and the routes we built, so a zero means "does what we say", not "no other route exists". The real-model runs are one model on one task with a small sample. People who have not read the rules have not yet attacked it; that result will be reported on its own line with the number of people and the date. The numbers are on the <Link to="/#evidence">home page</Link>, each with its sample size and its "what this is not".</p>
            <p><strong>What is not built.</strong> A separate phone approval page, several upstream tool servers, adapters for agents that do not use MCP, and the browser extension (cut).</p>
          </Section>

          <Section id="faq" title="Questions judges ask" source="the sections above; each answer points to the file that backs it.">
            <Faq q="Does an AI model decide what is allowed?">
              No. The rules are ordinary code that runs outside the model. The model can be talked into anything by a document it reads; the checks do not read the document for instructions. (README, THREAT_MODEL.)
            </Faq>
            <Faq q="Why not just tell the model not to leak?">
              An instruction in the prompt is advice the model can be persuaded to drop. In our recorded runs of one real model the unprotected setup delivered the restricted data in every usable run on the poisoned quotation, which is why the checks sit outside the model. See the evidence on the home page for the counts and their limits. (README, Measured results.)
            </Faq>
            <Faq q="Is it a guarantee?">
              No. It is a measurement on a corpus we wrote, plus a stated list of routes it does not cover. Read "Limits and honest scope" above. (THREAT_MODEL sections 5 to 7.)
            </Faq>
            <Faq q="What if the attacker rewords the secret?">
              A reworded paraphrase of confidential prose can get through value matching. It is listed as a declared gap and counted separately. The other defences still apply: the destination must be on the slip, an address that appears only in a document is not used, and after untrusted reading a consequential send waits for the officer. (README, ADVERSARIAL_TESTS.)
            </Faq>
            <Faq q="Which AI apps have you actually tested?">
              One: Claude.ai on a free account, signed in with OAuth, once. Other apps that speak MCP should work and are labelled that way. (PHASE_LOG B1, Integrations page.)
            </Faq>
            <Faq q="What does the officer see when asked?">
              What the action is, where it goes, which data, and the rule's own words, built by the gateway from the exact arguments. The agent cannot edit that text. Approvals are one-time, bound to that exact call, and expire. (THREAT_MODEL section 4.)
            </Faq>
            <Faq q="Is any of the data real?">
              No. Every record, mailbox, document and bank detail is synthetic; domains end in <code>.example</code>. (README.)
            </Faq>
            <Faq q="Can I check that the log was not edited?">
              Yes: open the console, finish the guided run, and use Verify, then Change one record, then Verify again. (Console, THREAT_MODEL section 2.)
            </Faq>
          </Section>
        </div>
      </div>
    </main>
  )
}
