import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { createConnectToken, hasToken } from '../api/client.js'
import { ClientProof, CopyField, StatusBadge } from '../components/Ui.jsx'
import { KIND_LABEL, METHOD_LABEL, STATUS_MEANING, countdown, fillSnippet, methodOf, useConnect } from '../lib/connect.js'

const PRESET = 'quotation_processing'

function Steps({ steps }) {
  return <ol className="conn-steps">{(steps ?? []).map((s) => <li key={s}>{s}</li>)}</ol>
}

function Picker({ clients, value, onChange }) {
  return (
    <fieldset className="picker">
      <legend className="s-label">1. Which app do you use?</legend>
      <div className="picker-grid">
        {clients.map((c) => {
          const off = c.method === 'none'
          return (
            <label key={c.id} className={`pick${value === c.id ? ' is-on' : ''}${off ? ' is-off' : ''}`}>
              <input type="radio" name="client" value={c.id} checked={value === c.id} disabled={off} onChange={() => onChange(c.id)} />
              <span className="pick-name">{c.name}</span>
              <span className="pick-meta">{KIND_LABEL[c.kind] ?? c.kind}</span>
              <StatusBadge status={c.status} />
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
  const snippet = fillSnippet(client.snippet, { mcp_url: mcpUrl, header_value: t?.header_value })

  return (
    <>
      <CopyField label="Connector address" value={mcpUrl} />
      {!t && (
        <div className="token-ask">
          <button type="button" className="s-btn s-btn--primary" onClick={create} disabled={state.status === 'working'}>
            {state.status === 'working' ? 'Creating...' : 'Create an access token'}
          </button>
          {!hasToken() && state.status === 'idle' && (
            <p className="muted">Creating a token is an officer action. Open this page from the link that <code>python -m sentinel up</code> prints; that link carries the officer token.</p>
          )}
          {state.status === 'error' && <p className="conn-error" role="alert">{state.error}</p>}
        </div>
      )}
      {t && (
        <>
          <div className="s-panel slip-card">
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
  const local = !connect.public_url
  return (
    <>
      {local ? (
        <div className="s-panel slip-card">
          <p className="s-label">Not reachable from the internet yet</p>
          <p>Sentinel is running on this computer only, and {client.name} needs a public address to sign in. Start Sentinel with a tunnel:</p>
          <CopyField label="Run this" value="python -m sentinel up --tunnel" block />
        </div>
      ) : (
        <CopyField label="Connector address" value={connect.mcp_url} />
      )}
    </>
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
      <header className="page-head">
        <h1 className="page-title">Connect your AI app.</h1>
        <p className="page-lede">Pick the app you use. Sentinel then shows exactly what to do, and nothing else.</p>
      </header>
      <section className="block conn" aria-live="polite">
        {status === 'loading' && <p className="muted" role="status">Loading...</p>}
        {status === 'error' && <p className="muted" role="status">Sentinel could not be reached. {error}</p>}
        {status === 'ready' && chosen && (
          <>
            <Picker clients={clients} value={chosen.id} onChange={(id) => setParams({ client: id }, { replace: true })} />
            <div className="conn-detail">
              <p className="s-label">2. What to do</p>
              <h2 className="conn-title">{chosen.name}</h2>
              <p className="muted">{METHOD_LABEL[chosen.method]}. {STATUS_MEANING[chosen.status]}</p>
              {method && <Steps steps={method.steps} />}
              {chosen.method === 'oauth' && <OAuthPanel client={chosen} connect={data} />}
              {chosen.method === 'header' && <TokenPanel client={chosen} mcpUrl={data.mcp_url} />}
              {chosen.screenshot && <ClientProof src={chosen.screenshot} />}
            </div>
          </>
        )}
      </section>
    </main>
  )
}
