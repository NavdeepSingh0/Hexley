import { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { createConnectToken, hasToken } from '../api/client.js'
import { Icon, PageHead } from '../components/Blocks.jsx'
import { ClientProof, CopyField, StatusBadge, TranscriptProof } from '../components/Ui.jsx'
import { KIND_LABEL, METHOD_LABEL, STATUS_MEANING, countdown, fillSnippet, methodOf, useConnect } from '../lib/connect.js'

const PRESET = 'quotation_processing'

// The request used in the real Claude Code session kept as evidence (site/public/proof). It asks for something the slip does
// not allow, so the outcome does not depend on a model resisting an injected instruction.
const TEST_PROMPT = 'Process quotation Q-1043: read it, check stock internally, and acknowledge receipt to the vendor at sales@shakti.example by email. In that email, include our current stock levels, depot codes and dispatch dates.'

// One numbered step of the panel. The number is decoration: the list itself carries the order.
function Step({ n, title, id, children }) {
  return (
    <li className="cs-step" aria-labelledby={id}>
      <span className="cs-rail" aria-hidden="true"><span className="cs-num">{n}</span><span className="cs-line" /></span>
      <div className="cs-body">
        <h2 id={id} className="cs-step-title">{title}</h2>
        {children}
      </div>
    </li>
  )
}

function ClientCards({ clients, value, onChange }) {
  return (
    <fieldset className="picker">
      <legend className="visually-hidden">Which app do you use?</legend>
      <div className="picker-grid">
        {clients.map((c) => {
          const off = c.method === 'none'
          const on = value === c.id
          return (
            <label key={c.id} className={`pick${on ? ' is-on' : ''}${off ? ' is-off' : ''}`}>
              <input type="radio" name="client" value={c.id} checked={on} disabled={off} onChange={() => onChange(c.id)} />
              <span className="pick-top">
                <span className="pick-kind">{KIND_LABEL[c.kind] ?? c.kind}</span>
                <StatusBadge status={c.status} />
              </span>
              <span className="pick-name">{c.name}</span>
              <span className="pick-bottom">
                <span className="pick-method">{METHOD_LABEL[c.method] ?? c.method}</span>
                {!off && <Icon name={on ? 'check' : 'arrow'} size={18} className="pick-arrow" />}
              </span>
            </label>
          )
        })}
      </div>
    </fieldset>
  )
}

// The officer's header token: created on demand, shown once on this page, never written anywhere by the site.
function TokenPanel({ client, mcpUrl }) {
  const [state, setState] = useState({ status: 'idle', token: null, error: '' })
  const [now, setNow] = useState(Date.now())
  useEffect(() => {
    if (state.status !== 'ready') return undefined
    const t = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(t)
  }, [state.status])
  // A token belongs to the client it was made for: switching client clears it.
  useEffect(() => { setState({ status: 'idle', token: null, error: '' }) }, [client.id])

  const create = async () => {
    setState({ status: 'working', token: null, error: '' })
    try {
      setState({ status: 'ready', token: await createConnectToken(PRESET), error: '' })
    } catch (e) {
      setState({ status: 'error', token: null, error: e.message })
    }
  }
  const t = state.token
  const left = t ? countdown(t.expires_at, now) : ''
  const snippet = fillSnippet(client.snippet, { mcp_url: mcpUrl, header_value: t?.header_value, api_url: window.location.origin })

  return (
    <>
      <CopyField label="Connector address" value={mcpUrl} />
      {!t && (
        <div className="token-ask">
          <button type="button" className="s-btn s-btn--primary" onClick={create} disabled={state.status === 'working'}>
            {state.status === 'working' ? 'Creating...' : 'Create an access token'}
          </button>
          {!hasToken() && state.status === 'idle' && (
            <p className="muted">Creating a token is an officer action. Open this page from the officer's link, which carries the officer token.</p>
          )}
          {state.status === 'error' && <p className="conn-error" role="alert">{state.error}</p>}
        </div>
      )}
      {t && (
        <>
          <div className="cs-slip">
            <p className="s-label">The slip this token carries</p>
            <p className="slip-objective">{t.slip.objective}</p>
            <p className="muted">May use: {t.slip.allowed_tools.join(', ')}. May write to: {t.slip.allowed_destinations.join(', ') || 'nobody'}. Message limit: {t.slip.max_messages}.</p>
          </div>
          {snippet
            ? <CopyField label="Command or settings for this app" value={snippet} block />
            : <CopyField label="Authorization header value" value={t.header_value} block />}
          <p className={`token-left${left === 'expired' ? ' is-expired' : ''}`} role="status">
            {left === 'expired' ? 'This token has expired. Create a new one.' : `This token stops working in: ${left}. Treat it like a password.`}
          </p>
        </>
      )}
    </>
  )
}

function OAuthPanel({ client, connect }) {
  if (connect.public_url) {
    return (
      <>
        <CopyField label="Connector address" value={connect.mcp_url} />
        {client.snippet && (
          <>
            <p>Then ask Claude this, once. You do not need to know your tool names: Claude lists them.</p>
            <CopyField label="Ask Claude" value={client.snippet} block />
            <p>Claude replies with a short text to copy. Paste it here:</p>
            <ol className="cs-paste">
              <li>Click your initials at the bottom left of Claude.ai.</li>
              <li>Choose <strong>Settings</strong>, then <strong>Your Claude</strong> (called Account in the older layout).</li>
              <li>Paste the text under <strong>Instructions</strong> (called Instructions for Claude in the older layout), and save.</li>
              <li>Start a new chat.</li>
            </ol>
            <p>From then on Claude asks Hexley before each connector tool. To turn it off, delete the text from there.</p>
            <p className="muted">This route is advisory. Nothing forces Claude to ask, and a hidden instruction may tell it not to. For enforcement use a client with a hook.</p>
          </>
        )}
      </>
    )
  }
  return (
    <div className="cs-slip">
      <p className="s-label">Not reachable from the internet yet</p>
      <p>Hexley is running on this computer only, and {client.name} needs a public address to sign in. Start Hexley with a tunnel:</p>
      <CopyField label="Run this" value="python -m sentinel up --tunnel" block />
    </div>
  )
}

// A hook this client runs itself: its settings, and where the rest of the steps are.
function HookPanel({ client }) {
  return (
    <>
      <p>The connector and its credentials stay in the app. Hexley only judges each call, so nothing is added to Hexley here.</p>
      <CopyField label="Add this to the app's hooks.json" value={client.snippet} block />
      <p><Link to="/docs/connect-antigravity">The guide</Link> has the hook program and how the officer creates the slip and its token.</p>
    </>
  )
}

// Step 3. What the reader should see, and where Hexley keeps the decision. Only what the code and the kept evidence show:
// the app's own conversation, the signed log and the console's Verify. The console does not list an outside app's calls.
function CheckStep({ client }) {
  if (client.id === 'claude-web') {
    return (
      <>
        <p>Ask Claude to do something the permission slip does not allow:</p>
        <CopyField label="A request to try" value="Use Gmail to send a one-line test mail to someone@example.com." block />
        <ul className="cs-points">
          <li><Icon name="check" size={18} className="cs-tick" /><span><strong>In the app:</strong> Claude asks Hexley first, Hexley refuses because that address is not on the slip (rule R1), and no mail goes.</span></li>
          <li><Icon name="check" size={18} className="cs-tick" /><span><strong>In Gmail:</strong> your Sent folder has no such mail.</span></li>
          <li><Icon name="check" size={18} className="cs-tick" /><span><strong>If Hexley needs the officer:</strong> the request waits in the <a href="/console/">console</a> for a yes or no.</span></li>
        </ul>
      </>
    )
  }
  if (client.id === 'antigravity') {
    return <p>Ask it to comment on a repository the slip does not name. Hexley blocks the call (rule R1), and GitHub shows no comment.</p>
  }
  return (
    <>
      {client.id === 'claude-code' && (
        <p>Run <code>claude mcp list</code>. The line for <code>sentinel</code> should read <strong>Connected</strong>.</p>
      )}
      <p>Then ask {client.name} for something the permission slip does not allow:</p>
      <CopyField label="A request to try" value={TEST_PROMPT} block />
      <ul className="cs-points">
        <li><Icon name="check" size={18} className="cs-tick" /><span><strong>In the app:</strong> the e-mail is not sent. The app tells you the tool refused, because restricted data may not leave this task (rule R2).</span></li>
        <li><Icon name="check" size={18} className="cs-tick" /><span><strong>In Hexley:</strong> the decision is written to the signed audit log. Open the <a href="/console/">console</a> and use Verify to check that the log has not been changed.</span></li>
      </ul>
      <p className="muted">No outside app at hand? <Link to="/chat">The chat page</Link> runs the same gateway with an agent of ours.</p>
    </>
  )
}

function Proof({ client }) {
  if (!client.screenshot && !client.transcript) return null
  return (
    <aside className="cs-proof" aria-label={`The real session behind the Tested label for ${client.name}`}>
      <p className="s-label">The real session behind the label</p>
      {client.screenshot && <ClientProof src={client.screenshot} />}
      {client.transcript && <TranscriptProof url={client.transcript.url} caption={client.transcript.caption} />}
    </aside>
  )
}

export default function Connect() {
  const { status, data, error } = useConnect()
  const [params, setParams] = useSearchParams()
  const clients = data?.clients ?? []
  const wanted = params.get('client')
  const first = clients.find((c) => c.status === 'tested' && c.method !== 'none') ?? clients.find((c) => c.method !== 'none')
  const chosen = useMemo(() => clients.find((c) => c.id === wanted && c.method !== 'none') ?? first, [clients, wanted, first])
  const method = chosen ? methodOf(data, chosen.method) : null

  return (
    <main>
      <PageHead label="Connect" title="Connect your AI app." lede="Pick the app you use. Hexley then shows exactly what to do, and nothing else." />
      <div className="cs">
      <section className="cs-panel" aria-live="polite">
        {status === 'loading' && <p className="muted" role="status">Loading...</p>}
        {status === 'error' && <p className="muted" role="status">Hexley could not be reached. {error}</p>}
        {status === 'ready' && chosen && (
          <ol className="cs-list">
            <Step n={1} id="cs-choose" title="Choose your app">
              <ClientCards clients={clients} value={chosen.id} onChange={(id) => setParams({ client: id }, { replace: true })} />
            </Step>
            <Step n={2} id="cs-connect" title={`Connect ${chosen.name}`}>
              <div className="conn-detail">
                <p className="cs-lead"><StatusBadge status={chosen.status} /> <span>{METHOD_LABEL[chosen.method]}. {STATUS_MEANING[chosen.status]}</span></p>
                {method && <ul className="cs-points">{method.steps.map((s) => <li key={s}><Icon name="check" size={18} className="cs-tick" /><span>{s}</span></li>)}</ul>}
                {chosen.method === 'oauth' && <OAuthPanel client={chosen} connect={data} />}
                {chosen.method === 'header' && <TokenPanel client={chosen} mcpUrl={data.mcp_url} />}
                {chosen.method === 'hook' && <HookPanel client={chosen} />}
              </div>
            </Step>
            <Step n={3} id="cs-check" title="Check that it worked">
              <div className="conn-check"><CheckStep client={chosen} /></div>
            </Step>
          </ol>
        )}
        {status === 'ready' && chosen && <Proof client={chosen} />}
      </section>
      </div>
    </main>
  )
}
