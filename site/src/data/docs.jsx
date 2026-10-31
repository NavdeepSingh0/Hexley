// The documentation pages (UI v2, U4). Everything here is written from the repository's own documents and code, and every page
// ends with the files its claims come from. No measured number is typed here: results live in /evidence.json (the home page).
import { Link } from 'react-router-dom'
import { Accordion, Icon } from '../components/Blocks.jsx'
import { CopyField, Shot } from '../components/Ui.jsx'
import { ClientEvidence } from '../components/DocParts.jsx'
import { PRECEDENCE, RULES } from './rules.js'
import { FAQ } from './faq.jsx'

const SETUP = `python -m pip install --user uv
python -m uv sync
npm --prefix console ci
npm --prefix console run build
npm --prefix site ci
npm --prefix site run build
python -m uv run python -m sentinel up --demo`

const CLASSIFY = `curl -X POST https://hexley.site/api/v1/tools/update_vendor_bank/classify \\
  -H "Authorization: Bearer <officer token>" -H "Content-Type: application/json" \\
  -d '{"capability": "write", "outbound": false, "consequential": true,
       "output_integrity": "trusted", "output_confidentiality": "restricted",
       "requires_human_verification": true}'`

const Note = ({ children, tone = 'note' }) => <div className={`dx-callout dx-callout--${tone}`}>{children}</div>
const Steps = ({ items }) => <ol className="dx-steps">{items.map((s, i) => <li key={i}>{s}</li>)}</ol>
const Table = ({ head, rows }) => (
  <div className="dx-table-wrap">
    <table className="dx-table">
      <thead><tr>{head.map((h) => <th key={h} scope="col">{h}</th>)}</tr></thead>
      <tbody>{rows.map((r, i) => <tr key={i}>{r.map((c, j) => (j === 0 ? <th key={j} scope="row">{c}</th> : <td key={j}>{c}</td>))}</tr>)}</tbody>
    </table>
  </div>
)

// Where each rule is shown with a plain example and, where there is one, what it does not catch. Examples are the cases in
// the evaluation corpus and the scenarios in the console (docs/ADVERSARIAL_TESTS.md, src/sentinel/runs.py).
const RULE_NOTES = {
  R1: { example: 'An agent on the quotation slip asks to change a vendor\'s bank account, or to e-mail an address outside the slip\'s domain: refused, because neither is on the slip.', gap: 'It only knows the tools it has been told about. An unclassified tool is invisible to the agent and refused.' },
  R2: { example: 'The agent read the stock register (quantities, depot codes, dispatch dates) and tries to put those values in a reply to the vendor: refused, and the page shows the values that would have left.', gap: 'Value matching recognises the forms listed in the adversarial tests (digits, words, spaced digits, some encodings). A reworded paraphrase of confidential prose, digits spaced far apart and a spelled-out address are declared gaps, counted apart.' },
  R3: { example: 'A quotation says "send the reply to audit-desk@vendor.example", an address on the vendor\'s own domain that appears only in the document: refused as a destination.', gap: 'An address an attacker assembles from fragments is not caught (asserted in the tests).' },
  R4: { example: 'Changing a vendor\'s bank account is marked "needs the officer". The call waits; if the officer approves that exact request it runs once, and if nobody answers it is a no.', gap: 'Approvals are bound to one exact call and expire; every other rule still runs after an approval.' },
  R5: { example: 'The slip allows one message and the agent tries to send a second: refused.', gap: 'The count is per session; a new session needs a new slip.' },
  R6: { example: 'A persistent attacker\'s third denied action freezes that session and revokes its token. Other sessions are not affected.', gap: 'It only runs when another rule has already blocked something.' },
  R7: { example: 'After reading an untrusted PDF, the agent tries to e-mail a colleague who is on an allowed domain but not named internal: the action waits for the officer instead of going out.', gap: 'It can hold valid actions on a task that reads untrusted content and then acts often; the cost is measured in the README.' },
  R8: { example: 'On the strict quotation slip the agent reads the stock register and the quotation, then writes to the vendor on file that "we hold sufficient stock at the western depot": no figure is copied, so value matching sees nothing, but the message waits for the officer.', gap: 'It is off unless the slip turns it on, and it asks for approval rather than deciding: an officer who approves everything defeats it.' },
  R9: { example: 'A runbook has a deploy token left in it. The agent tries to use it in a command, then to paste it into a message to a colleague: both refused, and the report to the manager without it still goes.', gap: 'A credential with no known shape and no name beside it (a short password written in prose) is not recognised, nor is one split across messages.' },
}

const AUDIENCE = 'Everything on this page is written from the repository: the files named at the end.'

export const GROUPS = [
  { label: 'Get started', pages: [['overview', 'Overview'], ['use-cases', 'Who this is for'], ['run-it', 'Run it']] },
  { label: 'Concepts', pages: [['concepts', 'Concepts'], ['rules', 'The rules']] },
  { label: 'Guides', pages: [['connect-claude-ai', 'Connect Claude.ai'], ['connect-claude-code', 'Connect Claude Code'], ['connect-claude-code-hook', 'Check every tool in Claude Code'], ['connect-antigravity', 'GitHub through Antigravity'], ['extension', 'The browser extension'], ['own-tools', 'Your own tools']] },
  { label: 'Reference', pages: [['api', 'API in brief']] },
  { label: 'Honesty', pages: [['limits', 'Limits and honest scope'], ['field-test', 'The field test'], ['faq', 'Questions judges ask']] },
]

export const PAGES = {
  overview: {
    title: 'Hexley documentation',
    lede: 'A gateway between an AI agent and its tools. The officer writes a permission slip; every action is checked against it before it happens.',
    source: 'README.md, docs/MVP.md, docs/ARCHITECTURE.md.',
    body: () => (
      <>
        <figure className="dx-figure">
          <div className="dx-figure-frame"><Shot name="stage" alt="The console: three lanes, Unprotected and Standard access say LEAKED, Hexley says DENIED." /></div>
          <figcaption>The console, replaying a real model's actions on a poisoned quotation; Hexley's decisions are computed live.</figcaption>
        </figure>
        <h2 id="paths">Choose your path</h2>
        <div className="dx-cards">
          {[
            ['run-it', 'play', 'Run it', 'One command starts the gateway, the console, the chat and this website.'],
            ['connect-claude-ai', 'plug', 'Connect an AI app', 'Sign in from Claude.ai, or paste an access token into Claude Code.'],
            ['own-tools', 'list', 'Add your own tools', 'Nothing runs until the officer has classified it.'],
            ['limits', 'shield', 'Read the limits', 'What Hexley covers, what it does not, and what the evidence is.'],
          ].map(([slug, icon, title, text]) => (
            <Link key={slug} to={`/docs/${slug}`} className="dx-card">
              <span className="dx-card-icon"><Icon name={icon} size={22} /></span>
              <span className="dx-card-title">{title}</span>
              <span className="dx-card-text">{text}</span>
              <Icon name="arrow" size={18} className="dx-card-arrow" />
            </Link>
          ))}
        </div>
        <h2 id="want">I want to…</h2>
        <Table head={['I want to', 'Use']} rows={[
          ['See an attack stopped', <a href="/console/">The console</a>],
          ['Try an agent whose calls are checked', <Link to="/chat">The chat</Link>],
          ['Connect Claude.ai', <Link to="/docs/connect-claude-ai">Connect Claude.ai</Link>],
          ['Connect Claude Code', <Link to="/docs/connect-claude-code">Connect Claude Code</Link>],
          ['Understand a denial', <Link to="/docs/rules">The rules</Link>],
          ['Check that the log was not edited', <>The console's Verify, or Details in the chat</>],
        ]} />
        <h2 id="pieces">The pieces</h2>
        <ul className="dx-list">
          <li><strong>The gateway</strong> speaks MCP. An agent connects with a session token; every tool call is decided before it is forwarded.</li>
          <li><strong>The console</strong> shows the same task in three setups (Unprotected, Standard access, Hexley), the reason for a denial, officer approvals and the signed log.</li>
          <li><strong>The chat</strong> is a host where a model's every tool call goes through the gateway, and what you see is built from the gateway's own events.</li>
          <li><strong>This website</strong> is served by the same program, so one command shows everything.</li>
        </ul>
      </>
    ),
  },

  'run-it': {
    title: 'Run it',
    lede: 'Hexley is hosted at hexley.site, so you need none of this to connect an AI app. This page is for running your own copy. The demo uses synthetic data and needs no model key in its scripted and replay modes.',
    source: 'README.md (Setup), src/sentinel/cli.py, .env.example.',
    body: () => (
      <>
        <h2 id="install">Install and start</h2>
        <p>You need Python, the <code>uv</code> package manager and Node. Run these from the repository folder:</p>
        <CopyField label="Run it" value={SETUP} block />
        <p>The last command starts everything and opens this website. The link it prints carries the officer token in its address; the page moves it out of the address bar as soon as it opens, and the console reuses it. <code>--demo</code> turns on the tamper button in the console and starts a fresh audit log (the old one is kept aside).</p>
        <h2 id="starts">What it starts</h2>
        <Table head={['Part', 'Default address', 'What it is']} rows={[
          ['API, console and website', 'http://127.0.0.1:8000', 'The officer\'s API, the console at /console/, the chat, and this site'],
          ['Gateway', 'http://127.0.0.1:8100/mcp', 'What an AI client connects to'],
          ['Tool server', 'http://127.0.0.1:8200', 'The mock tools behind the gateway; only the gateway can reach it'],
        ]} />
        <Note>If another program already uses one of those ports, pass <code>--api-port</code>, <code>--gateway-port</code> or <code>--tools-port</code> with free ones.</Note>
        <h2 id="flags">Options you will use</h2>
        <Table head={['Option', 'What it does']} rows={[
          [<code>--demo</code>, 'Enables the tamper endpoint and starts a fresh audit log.'],
          [<code>--no-browser</code>, 'Prints the link instead of opening it (so the terminal that shows the token never has to be on a screen).'],
          [<code>--tunnel</code>, 'Opens a free cloudflared tunnel to the gateway and uses its address, so an app on the internet can connect. The address changes on every start.'],
          [<code>--public-url URL</code>, 'Uses an address you already have for the gateway (turns on sign-in for AI clients).'],
          [<code>--data-dir DIR</code>, 'Where the audit log and its signing key live (kept out of git).'],
          [<code>--oauth-preset</code>, 'The slip template an OAuth sign-in approves (default: quotation processing).'],
          [<code>--oauth-ttl SECONDS</code>, 'How long an OAuth-approved slip lasts (default one hour).'],
        ]} />
        <h2 id="models">Models and keys</h2>
        <p>The scripted attacker and the replay of a recorded run need no key. A live model uses the NVIDIA API: put <code>NVIDIA_API_KEY</code> in a local <code>.env</code> file (git-ignored, never in chat or in the repository). Extra keys named <code>NVIDIA_API_KEY_2</code>, <code>_3</code> and so on are used when one key is rate-limited: the limited key rests for the time the provider asks and the next call goes to another.</p>
        <p>In the chat, <strong>Automatic</strong> uses a live model when a key exists and otherwise the scripted attacker; <strong>Recorded real chat</strong> replays the model replies of an earlier real chat with the decisions computed live. The disclosure line under the box always says which one is running.</p>
        <h2 id="tests">Run the tests</h2>
        <CopyField label="Tests" value={'python -m uv run pytest\nnpm --prefix console test\nnpm --prefix site test'} block />
      </>
    ),
  },

  concepts: {
    title: 'Concepts',
    lede: 'Six ideas explain everything Hexley does.',
    source: 'README.md, docs/THREAT_MODEL.md sections 1 to 4, docs/DECISIONS.md (D-007, D-019, D-022, D-028).',
    body: () => (
      <>
        <h2 id="gateway">The gateway</h2>
        <p>Hexley is an MCP gateway: the AI agent talks to Hexley, and Hexley talks to the real tools. Every call is checked first. <strong>No language model makes any security decision</strong>; the checks are ordinary code running outside the model.</p>
        <p>For connectors an app already has, such as Claude's Gmail, Hexley does not host anything and holds no credential. It only judges whether the tool may run: enforced through a hook where the app has one, and advisory where it does not.</p>
        <h2 id="slip">The permission slip</h2>
        <p>Before the agent reads anything untrusted, the officer confirms a slip: the task, the tools it may use, where data may go, which places count as internal, and how many messages it may send. The agent cannot create or widen it. The session token is bound to the confirmed slip, so a changed slip is a different token.</p>
        <h2 id="decisions">Four decisions</h2>
        <p>Every action ends as one of these, in the same words everywhere:</p>
        <ul className="dx-list">
          <li><strong>ALLOWED</strong>: inside the slip, nothing restricted leaves.</li>
          <li><strong>DENIED</strong>: a rule refused it, with a plain reason.</li>
          <li><strong>NEEDS APPROVAL</strong>: held until the officer approves that exact request.</li>
          <li><strong>QUARANTINED</strong>: the session was frozen and its token revoked.</li>
        </ul>
        <p>{PRECEDENCE} The rules behind them are on <Link to="/docs/rules">their own page</Link>.</p>
        <h2 id="approvals">Officer approvals</h2>
        <p>A held action waits. The approval is bound to a hash of the session, the tool and the exact arguments; it works once; it expires; a call with any different argument needs a new approval; and <strong>silence is a no</strong>. Every other rule still runs after an approval, so an approval can never excuse a leak. The approval is written to the log before it takes effect.</p>
        <h2 id="quarantine">Quarantine</h2>
        <p>The third denied action in one session freezes that session and revokes its token. The freeze is per session: other sessions and other work items are not affected, and a frozen session cannot be refreshed.</p>
        <h2 id="hardened">Hardened mode</h2>
        <p>An optional, narrower set-up for the quotation task. The slip is bound to one work item, the agent gets a single tool that sends a fixed message, and Hexley chooses the recipient from trusted records. That shrinks the e-mail channel a lot; it does not remove every covert channel (which calls are made, their timing, retries).</p>
        <h2 id="audit">The audit log</h2>
        <p>Every decision is written to a signed, hash-chained log <em>before</em> anything is forwarded; a slow or failed write refuses the action. It shows if a record was changed, deleted or reordered. It does not prove that the recorded events were true, and a truncated log is only noticed if the checker holds an earlier chain head. You can verify it in the console and in the chat's Details drawer.</p>
      </>
    ),
  },

  rules: {
    title: 'The rules',
    lede: 'Nine rules, in plain English, each with an example and what it does not catch.',
    source: 'docs/THREAT_MODEL.md, docs/ADVERSARIAL_TESTS.md, src/sentinel/rules.py, README.md.',
    body: () => (
      <>
        <p>{PRECEDENCE} The rules look at the slip, where the data came from and where it is going; none of them reads the document for instructions.</p>
        {RULES.map((r) => (
          <section key={r.id} className="dx-rule" aria-labelledby={r.id.toLowerCase()}>
            <h2 id={r.id.toLowerCase()}>{r.id}: {r.title}</h2>
            <p className="dx-rule-out">Outcome: <strong>{r.outcome}</strong></p>
            <p>{r.text}</p>
            <p><span className="dx-tag">Example</span> {RULE_NOTES[r.id].example}</p>
            <p className="muted"><span className="dx-tag">Not covered</span> {RULE_NOTES[r.id].gap}</p>
          </section>
        ))}
      </>
    ),
  },

  'connect-claude-ai': {
    title: 'Connect Claude.ai',
    lede: 'Add Hexley as a custom connector, sign in with Google, and ask Claude to set it up. Your connectors stay yours: Hexley holds none of their credentials.',
    source: 'src/sentinel/cooperative.py, docs/DECISIONS.md D-057 and D-060, docs/PHASE_LOG.md row F3c.',
    body: () => (
      <>
        <h2 id="add">Add the connector</h2>
        <Steps items={[
          'In Claude.ai open Customize, then Connectors, then Add custom connector.',
          'Paste https://hexley.site/mcp and connect.',
          'Choose any Google account, then press Allow on the one short page that follows. It lists what the AI may do. The slip lasts 7 days.',
        ]} />
        <h2 id="setup">Set it up once</h2>
        <p>You do not need to know your tool names. Claude knows them, so ask it to list them. The exact request is on the <Link to="/connect?client=claude-web">Connect page</Link>, with a copy button. Hexley returns a short text to copy and says where it goes:</p>
        <Steps items={[
          'Click your initials at the bottom left of Claude.ai.',
          'Choose Settings, then Your Claude (called Account in the older layout).',
          'Paste the text under Instructions (called Instructions for Claude in the older layout), and save.',
          'Start a new chat.',
        ]} />
        <p>From then on Claude asks Hexley before each connector tool and runs the tool only on a yes. Hexley also counts your tools: how many it checks, and how many it refuses because they are not on the slip or nobody has classified them.</p>
        <h2 id="see">What you will see</h2>
        <p>Claude tells you in one line what Hexley decided for each tool. Ask it to mail an address that is not on the slip: Hexley refuses (R1) and no mail goes. A call that needs a person waits in the <a href="/console/">console</a>, where the officer sees the exact request and approves or denies it.</p>
        <h2 id="advisory">This route is advisory</h2>
        <Note tone="limit">Claude's connectors run on Anthropic's servers and nothing asks Hexley on the way, so on Claude.ai the text is a request to the model. Nothing forces it to ask, and a hidden instruction may tell it not to, in which case Hexley never sees the call. For enforcement use a client with a hook, such as <Link to="/docs/connect-claude-code-hook">Claude Code</Link>. To go back to normal Claude.ai, delete the text from your Instructions.</Note>
        <p>In Claude Code, with the same text and no hook, two models asked first in 5 of 5 runs each, also when a mail told them to skip Hexley, and in 0 of 5 without the text. They obeyed a refusal in 10 of 10 runs. That is n=5 per condition on Claude Code with one fixed injection, not a measurement of Claude.ai, and both models ignored the injection with no Hexley at all, so it does not show Hexley stopping an attack.</p>
        <h2 id="shared">One slip for everyone, for now</h2>
        <p>Any Google account can sign in, and everyone who does gets the same slip and the same approved destinations. A restart of the hosted server signs everyone out, so reconnect with one click.</p>
        <h2 id="evidence">Evidence</h2>
        <ClientEvidence id="claude-web" />
        <Note tone="limit">One account, one run per test. It is a demonstration that the route works, not a measurement.</Note>
      </>
    ),
  },

  'connect-claude-code': {
    title: 'Connect Claude Code',
    lede: 'Create a short-lived access token on the Connect page and give it to Claude Code as a header.',
    source: 'docs/contracts/API.md (Connect), docs/DECISIONS.md D-041 and D-044, docs/PHASE_LOG.md row F8.',
    body: () => (
      <>
        <h2 id="token">Create a token</h2>
        <p>Open the <Link to="/connect?client=claude-code">Connect page</Link> from the officer's link (it carries the officer token), choose Claude Code and press <strong>Create an access token</strong>. The token carries the quotation slip and stops working after fifteen minutes or so; treat it like a password.</p>
        <h2 id="add">Add the server</h2>
        <p>The page shows the exact command with the real address and token filled in. It looks like this:</p>
        <CopyField label="Command" value={'claude mcp add --transport http sentinel <connector address> --header "Authorization: Bearer <token>"'} block />
        <h2 id="check">Check it</h2>
        <p>Run <code>claude mcp list</code>. The line for <code>sentinel</code> should read <strong>Connected</strong>. Then ask Claude Code to process the quotation and include the stock figures: the e-mail is denied and nothing is delivered.</p>
        <h2 id="evidence">Evidence</h2>
        <ClientEvidence id="claude-code" />
        <Note tone="limit">One session on one machine, against a local gateway, with one model. It shows that a real client can connect with the token and be decided by the gateway; it is not a measurement.</Note>
      </>
    ),
  },

  'use-cases': {
    title: 'Who this is for',
    lede: 'Any place an AI agent can both read text from strangers and act on real systems. E-mail is only the easiest example to show.',
    source: 'docs/plans/PRODUCT_ROADMAP.md, docs/QA_PREP.md section 7.',
    body: () => (
      <>
        <h2 id="why">Why anybody should bother</h2>
        <p>An agent works with a person's rights, and it reads text written by anyone: a ticket, an issue, a PDF, a web page. Access control asks whether this identity may use this tool, and the answer is yes, so it cannot tell the job from a hijack. A model can be told to behave, but an instruction is advice that the next document can argue with. Hexley sits outside the model, holds the task a person approved, and checks what the agent does next.</p>
        <h2 id="where">Where it fits</h2>
        <Table head={['Who', 'What the agent does', 'What goes wrong', 'What Hexley does']} rows={[
          ['Engineering teams with coding agents', 'Reads issues, code and config, and comments, commits and deploys', 'An issue tells it to post a private file, or it finds a token in a config and uses it', 'Only the repositories on the slip; a found credential is never sent or used; deletes and config writes wait or are refused'],
          ['Support desks', 'Reads customer tickets, looks up accounts, replies', 'A ticket asks for another customer\'s record', 'Values from restricted records may not leave; addresses named only in a ticket are refused'],
          ['Finance and procurement', 'Reads invoices and quotations, updates vendors, pays', 'A letter asks to change a bank account', 'The change waits for a person, who approves that exact request once'],
          ['Government and defence offices', 'Works on files with a local model', 'A circular tells it to mail a voter roll', 'Runs on your own machine with a local model; nothing needs to reach a cloud service'],
          ['Operations, HR, legal, health', 'Summarises channels and records, drafts messages', 'Tokens or personal data pasted in a channel travel on', 'Credentials and cards never go anywhere; restricted values stay inside the places the slip names'],
        ]} />
        <h2 id="who-pays">Who would pay</h2>
        <p>The likely buyer is whoever answers for an agent's mistakes: a security or compliance lead at a company rolling agents out, or an IT department in government through an integrator. What they would buy is the ability to say yes to agents, with a record that shows what each one was allowed to do and did. The idea on the roadmap is open core: free to run yourself, with single sign-on, high availability and support paid.</p>
        <Note tone="limit">This is our reasoning, not evidence. Nobody has paid, no pilot has run, and no price is decided. Cloud vendors bundle per-call policy for their own platforms, so our case rests on working outside the agent, on any client, and on your own machine.</Note>
        <h2 id="not-for">Who does not need it</h2>
        <p>Someone chatting with a model that has no tools. An agent that can only read public data and has nowhere to send anything. Hexley limits actions, and with no actions there is nothing to limit.</p>
      </>
    ),
  },

  'field-test': {
    title: 'The field test',
    lede: 'Five documents with real-looking values, one per connector. Every field was sent out eight ways, to see what Hexley recognises and what it only holds.',
    source: 'scripts/eval/connector_fields.py, eval/connector_fields/results.md, docs/PHASE_LOG.md row P6.',
    body: () => (
      <>
        <h2 id="how">How it ran</h2>
        <p>Each document was reported as the result of that connector's read tool, on the hook's own endpoints. Then each field was sent through that connector's write tool to a place the slip allows but does not call internal, and to a place it does. No real service was called, and the documents and their values are not in the repository. The tiers (secret, business, harmless) are our own labels.</p>
        <h2 id="result">What happened</h2>
        <Table head={['Sensitive fields, 64 in all', 'Refused by value', 'Held for the officer', 'Let through']} rows={[
          ['As written', '57', '7', '0'],
          ['In base64', '53', '11', '0'],
          ['In capitals', '57', '7', '0'],
          ['Separators removed', '41', '23', '0'],
          ['Dashes between pairs', '24', '40', '0'],
          ['Reversed', '18', '46', '0'],
          ['First half only', '10', '54', '0'],
        ]} />
        <p>All 21 secret fields were refused going outside, and credentials and card numbers were refused going to the internal place too. The first run of this test found that GitHub issues were not treated as restricted, that 18 of those secrets could go to an internal place, and that base64 hid everything. Those are fixed.</p>
        <h2 id="limits">What it does not show</h2>
        <ul className="dx-list">
          <li><strong>Held is not refused.</strong> A held message goes out if the officer approves it, so it depends on the officer reading it.</li>
          <li><strong>Seven sensitive fields were not recognised as written:</strong> people's names, percentages, short free text, and small numbers such as a quantity of 42. They were held, because the session had read untrusted content.</li>
          <li><strong>Bank account and tax numbers may go to a place the slip calls internal,</strong> because the officer named it. Only credentials and cards never go.</li>
          <li><strong>The cost:</strong> 12 of 34 fields we called harmless were refused outright going outside, such as a quotation number or a date. A value read from a restricted source may not leave, and that can refuse an honest message. It may go back to the place it came from.</li>
          <li><strong>The values were written by a teammate and the tiers by us.</strong> This is a test of matching on documents like these, not a measurement of how an attacker would do.</li>
        </ul>
      </>
    ),
  },

  extension: {
    title: 'The browser extension',
    lede: 'Hexley\'s mascot on claude.ai and chatgpt.com, reacting to real decisions, with held actions you can approve from the browser. It enforces nothing.',
    source: 'extension/README.md, developer.chrome.com (Chrome Web Store registration and distribution pages, read 31 Oct 2026).',
    body: () => (
      <>
        <h2 id="install">Install it</h2>
        <p><a href="/hexley-extension-0.1.0.zip" download>Download the extension</a> (26 KB), then:</p>
        <Steps items={[
          'Unzip it into a folder you will keep.',
          'In Chrome open chrome://extensions and turn on Developer mode, top right.',
          'Press Load unpacked and choose that folder.',
          'Open the extension\'s Settings and paste the officer\'s link for hexley.site, or for your own copy.',
        ]} />
        <Note tone="limit">Chrome does not let a website install an extension on Windows or Mac: it must come from the Chrome Web Store, which charges a one-time registration fee, so we have not published it. That also means it does not update itself. To update, download it again, replace the folder and press Reload on chrome://extensions.</Note>
        <h2 id="what">What it does and does not do</h2>
        <p>It shows what Hexley decided and lets the officer approve or deny a held action. It stops nothing by itself, and it needs the officer's token. The decisions happen in Hexley.</p>
      </>
    ),
  },

  'connect-antigravity': {
    title: 'GitHub through Antigravity',
    lede: 'GitHub\'s own MCP server stays in Antigravity with its own token. Antigravity\'s hook asks Hexley before each MCP call.',
    source: 'scripts/connectors/antigravity_hook.py, docs/DECISIONS.md D-059, docs/PHASE_LOG.md row G3.',
    body: () => (
      <>
        <h2 id="steps">Set it up</h2>
        <Steps items={[
          'Add GitHub\'s MCP server to Antigravity in the usual way. Its token stays in Antigravity; Hexley never sees it.',
          'Copy scripts/connectors/antigravity_hook.py from the repository into .agents in your project. It needs only Python.',
          'The officer creates a slip that names the GitHub tools and the repositories (POST /api/v1/slips), with unseen_context on. Save its session token, without the word Bearer, in ~/.hexley/antigravity_token.',
          'Point Antigravity\'s hooks.json at the program, as shown on the Connect page.',
        ]} />
        <h2 id="what">What happens</h2>
        <p>Antigravity sends every MCP call to the hook. The hook asks Hexley, and denies if anything goes wrong: Hexley unreachable, no token, or a call in a shape it does not recognise. The log it keeps at <code>~/.hexley/antigravity_hook.log</code> holds tool names, never arguments or tokens.</p>
        <h2 id="limits">What this does not give you</h2>
        <ul className="dx-list">
          <li><strong>Antigravity's terminal and built-in tools are not judged,</strong> so <code>git</code> or <code>gh</code> there go around Hexley.</li>
          <li><strong>Hexley cannot learn from what GitHub returned.</strong> Antigravity's after-tool hook is not documented as carrying results, so the slip treats the session as having read untrusted content from its first call, and a leak from a private repository to a public one is not something this route can see.</li>
          <li><strong>The way Antigravity sends MCP calls is not documented.</strong> It was read from a real run. If an update changes it, the hook denies.</li>
        </ul>
        <h2 id="evidence">Evidence</h2>
        <ClientEvidence id="antigravity" />
        <Note tone="limit">One run per condition, two for the attack, on test repositories. Antigravity was told to carry out the planted steps, as a stand-in for a fooled model.</Note>
      </>
    ),
  },

  'connect-claude-code-hook': {
    title: 'Check every tool in Claude Code',
    lede: 'A gateway decides only what goes through it. Claude Code can also ask Hexley before each tool call, whichever server the tool belongs to, so other connectors are covered too.',
    source: 'src/sentinel/check.py, docs/plans/PRODUCT_ROADMAP.md (W1.4), docs/PHASE_LOG.md row F1; Claude Code hooks: code.claude.com/docs/en/hooks.',
    body: () => (
      <>
        <h2 id="why">Why this exists</h2>
        <p>Add Hexley to Claude Code as an MCP server and Hexley decides the tools it hosts. Every other tool Claude Code has (a Gmail or GitHub connector, a shell, file edits) never reaches Hexley. Claude Code's hook feature closes that: before each tool call it can send the call to a web address and obey the answer, and after the call it can report the result. The model does not choose whether the hook runs.</p>
        <h2 id="steps">Set it up</h2>
        <Steps items={[
          'Open the officer\'s link. Gmail, Slack and Notion tools are already classified; classify any other connector\'s tools once (Your own tools). A tool nobody classified is refused, so a connector Hexley has never heard of cannot be used by accident.',
          'Create a permission slip that allows those tools, and an access token for it (the Connect page, or the slip builder in the API).',
          'Write the hook block into Claude Code\'s settings, and set the token in an environment variable.',
        ]} />
        <CopyField label="Print the settings block" value="python -m sentinel hook-config --api-url https://hexley.site --skip sentinel" block />
        <p>The block sends both events (before and after each call) to Hexley over HTTP. The token is read from the environment variable <code>SENTINEL_TOKEN</code> and is never written into the file. <code>--skip sentinel</code> names a server that already goes through Hexley's gateway, so its calls are not decided twice. The block sets <code>onFailure: block</code>: if Hexley is down or too slow, the call does not run (this needs Claude Code 2.1.295 or newer; on older versions a failed hook lets the call run).</p>
        <h2 id="what">What happens</h2>
        <Table head={['Claude Code is about to…', 'Hexley answers']} rows={[
          ['Call a tool of an unclassified connector', 'Deny: it is not on the slip (R1)'],
          ['Send restricted data to a place that is not internal', 'Deny (R2); the call never runs'],
          ['Send after the session read untrusted content', 'Hold for the officer (R7); once approved, an identical retry runs once'],
          ['Write to agent or editor configuration, or read a credential file', 'Deny. That covers the settings file of Claude Code itself when it is written with Write or Edit, or by a shell command in a common form (redirection, tee, sed -i, cp, mv, rm, inline Python)'],
          ['Run a command that deletes or cannot be undone', 'Hold for the officer'],
          ['Read a file, search, or use another built-in tool Hexley does not decide on', 'Allow, and list it as seen but not mediated'],
        ]} />
        <p>An allowed call gets an empty answer, so Claude Code's own permission prompts still apply. Hexley only ever denies.</p>
        <h2 id="coverage">What you can see</h2>
        <p>Ask the API for a session's coverage (<code>GET /api/v1/sessions/&lt;id&gt;/coverage</code>, officer token). It lists the tools Hexley saw, which route each came by, which it decided on, and which it refused because nobody classified them. Make the hook's matcher match every tool and the list shows what is not mediated.</p>
        <h2 id="evidence">Evidence</h2>
        <ClientEvidence id="claude-code-hook" />
        <Note tone="limit">One headless session per condition, on test accounts. In the attack runs Claude was told to carry out the planted steps, as a stand-in for a fooled model, so these show Hexley blocking the call, not a model being fooled. It is not a measurement.</Note>
        <h2 id="limits">What this does not give you</h2>
        <ul className="dx-list">
          <li><strong>The client decides whether to ask.</strong> A hook that a user removes from Claude Code's own settings, or a tool the matcher does not name, is not mediated. Organisations can lock hooks in managed settings, which Hexley does not control. Writes to the settings files through Write, Edit and the common shell forms above are refused (tested), but a program that changes the file in a way the recogniser cannot read is not, so do not treat the hook as tamper-proof.</li>
          <li><strong>Hexley learns from results only if the client reports them.</strong> A client that sends the before-call event but not the after-call event has weaker protection: a restricted value Hexley never saw cannot be recognised later (this is tested and written down).</li>
          <li><strong>Files attached to a chat app, and chat apps with no hook,</strong> are not covered by this route. For a client whose context Hexley cannot see, a slip can say so, and the session counts as having read untrusted content from its first call.</li>
        </ul>
      </>
    ),
  },

  'own-tools': {
    title: 'Your own tools',
    lede: 'Hexley does not guess what a tool does. A tool nobody has classified is invisible to the agent and refused.',
    source: 'docs/contracts/API.md (Tools and slips for any task), docs/DECISIONS.md D-037 and D-038.',
    body: () => (
      <>
        <h2 id="list">List what the tool server offers</h2>
        <p><code>GET /api/v1/tools</code> (officer token) lists every tool, whether it is classified, and a first guess for each unclassified one. The guess is for you to review; it is never applied automatically.</p>
        <h2 id="classify">Classify a tool</h2>
        <CopyField label="Classify a tool (officer action)" value={CLASSIFY} block />
        <p>The labels say whether the tool reads, writes or sends; whether it is consequential; whether its output is trusted and how confidential it is; which argument is the destination (for a tool that sends); and whether the officer must approve each call. A tool that sends must name its destination. Built-in tools cannot be weakened. Each classification is written to the audit log before it is saved.</p>
        <h2 id="slips">Build a slip for any task</h2>
        <p><code>POST /api/v1/slips</code> takes the objective, the allowed tools, the allowed destinations (domains, web hosts or <code>path:/folder</code> entries), which destinations are internal, a message limit and a lifetime. Vague entries such as wildcards are refused with a plain message.</p>
        <Note tone="limit">One tool server sits behind one gateway. Several upstream servers are not built, and our tools are mocks, not real file, browser or database servers.</Note>
      </>
    ),
  },

  api: {
    title: 'API in brief',
    lede: 'The endpoints the website uses. All need the officer token unless marked public.',
    source: 'docs/contracts/API.md, src/sentinel/api.py.',
    body: () => (
      <>
        <p>Send the officer token as <code>Authorization: Bearer &lt;token&gt;</code>. The full contract, with request and response shapes, is <code>docs/contracts/API.md</code> in the repository.</p>
        <h2 id="connect">Connecting a client</h2>
        <Table head={['Endpoint', 'Purpose']} rows={[
          [<code>GET /api/v1/connect</code>, 'Public. The connector address, the ways to connect and each client\'s status and evidence.'],
          [<code>POST /api/v1/connect/token</code>, 'Creates a short-lived access token for a slip preset.'],
        ]} />
        <h2 id="chat">Chat</h2>
        <Table head={['Endpoint', 'Purpose']} rows={[
          [<code>GET /api/v1/chat/presets</code>, 'The four tasks.'],
          [<code>POST /api/v1/chat</code>, 'Starts a chat (preset and mode: auto, live, scripted or replay).'],
          [<code>POST /api/v1/chat/&#123;id&#125;/confirm</code>, 'The officer confirms the slip.'],
          [<code>POST /api/v1/chat/&#123;id&#125;/messages</code>, 'Sends a message; the answer is built while you poll the chat.'],
          [<code>GET /api/v1/chat/&#123;id&#125;</code>, 'The whole conversation: messages, each tool call with its decision, the mascot, the status.'],
          [<code>GET /api/v1/chat/&#123;id&#125;/recording</code>, 'Exports the model\'s replies for a replay.'],
        ]} />
        <h2 id="tools">Tools, slips and approvals</h2>
        <Table head={['Endpoint', 'Purpose']} rows={[
          [<code>GET /api/v1/tools</code>, 'Lists the tools and which are classified.'],
          [<code>POST /api/v1/tools/&#123;name&#125;/classify</code>, 'The officer classifies a tool.'],
          [<code>POST /api/v1/slips</code>, 'Builds a slip for any task.'],
          [<code>POST /approvals/&#123;id&#125;</code>, 'Approve or deny one held action.'],
          [<code>GET /audit/verify</code>, 'Checks the signed chain and reports how many records were checked.'],
          [<code>POST /audit/tamper</code>, 'Demo only (started with --demo): changes one record on disk so Verify can catch it. POST /audit/restore puts it back.'],
        ]} />
        <Note>FastAPI's own interactive documentation is switched off; this page and the repository's contract are the reference.</Note>
      </>
    ),
  },

  limits: {
    title: 'Limits and honest scope',
    lede: 'What is protected, what is not governed, and what the evidence is.',
    source: 'docs/THREAT_MODEL.md (all sections), README.md (Status, Measured results), docs/DECISIONS.md D-036 to D-044, docs/PHASE_LOG.md.',
    body: () => (
      <>
        <h2 id="protected">What is protected</h2>
        <p>An action is allowed only when the tool is on the slip, the destination is inside what the slip allows and did not come only from untrusted content, no restricted value the session has read leaves the building, and, after untrusted reading, a consequential action goes only to an internal destination or waits for the officer.</p>
        <h2 id="not-governed">What Hexley does not govern</h2>
        <ul className="dx-list">
          <li>The model's own reply to the user. The gateway sees tool calls, not what the agent says in chat; in a hosted app that reply goes to the app's provider.</li>
          <li>Other capabilities the agent holds: another connector, a browser, a direct credential, a shell. For a real deployment the agent must hold no credential for what Hexley is meant to govern.</li>
          <li>Covert channels: which calls are made, their timing, retries, send versus no-send.</li>
          <li>Whether the content of an allowed action is correct or wise. A slip that is too wide is enforced faithfully.</li>
        </ul>
        <h2 id="gaps">Known gaps, declared</h2>
        <p>A paraphrase of confidential text is not caught by value matching; digits spaced apart and a spelled-out address are listed as gaps in the evaluation. Text hidden in images needs OCR and is not covered. R7 can hold valid actions on a task that reads untrusted content and then acts often.</p>
        <h2 id="demo-grade">What is demo-grade</h2>
        <p>One static officer token is not identity management. Any Google account can sign in, and everyone who does shares one slip; a limit per address slows one noisy address and does nothing against many. On the hosted site anyone can try the demo and the chat with no account, on synthetic data and mock tools. Only one console run goes at a time, so a visitor may be asked to try again; visitors share about 200 of the live model's 300 requests per server start. Do not upload anything real to the hosted chat. Sign-ins and sessions are in memory. The audit log shows that a record was altered, deleted or reordered; it does not prove the events were true, and a truncated log is only noticed if the verifier holds the earlier chain head. On the hosted server the log and its signing key are cleared by every restart or deploy, so a past session's log cannot be checked there. Chats live in memory.</p>
        <h2 id="evidence">What the evidence is</h2>
        <p>In the measured scenarios the tools are our own mocks. The connector tests used real connectors on test accounts, one run per condition, and they show the route works rather than a rate. The test cases were written by us from the documented matcher list and the routes we built, so a zero means "does what we say", not "no other route exists". The real-model runs are one model on one task with a small sample. People who have not read the rules have not yet attacked it; that result will be reported on its own line with the number of people and the date. The numbers, each with its sample size and its "what this is not", are on the <Link to="/#evidence">home page</Link>.</p>
        <h2 id="not-built">What is not built</h2>
        <p>A separate phone approval page, adapters for agents that do not use MCP, and the browser extension (cut). Hosting several connectors behind the gateway is built and parked as a backup: Hexley judges the connectors an app already has instead of rebuilding them.</p>
      </>
    ),
  },

  faq: {
    title: 'Questions judges ask',
    lede: 'Short answers, each written from the repository.',
    source: 'the pages of this documentation; each answer points to the file that backs it.',
    body: () => (
      <>
        <Accordion items={FAQ} />
        <p className="muted dx-faq-note">{AUDIENCE}</p>
      </>
    ),
  },
}

export const ORDER = GROUPS.flatMap((g) => g.pages.map(([slug]) => slug))
export const LEGACY = { limits: 'limits', faq: 'faq', 'getting-started': 'run-it', concepts: 'concepts', connect: 'connect-claude-ai', 'own-tools': 'own-tools' }
