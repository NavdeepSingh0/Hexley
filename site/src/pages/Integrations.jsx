import { Link } from 'react-router-dom'
import { ClientProof, StatusBadge, TranscriptProof } from '../components/Ui.jsx'
import { KIND_LABEL, METHOD_LABEL, STATUS_MEANING, groupByStatus, useConnect } from '../lib/connect.js'

function ClientCard({ c }) {
  return (
    <li className="s-panel client-card">
      <div className="client-head">
        <h3 className="client-name">{c.name}</h3>
        <span className="muted client-kind">{KIND_LABEL[c.kind] ?? c.kind}</span>
      </div>
      <p className="muted client-method">{METHOD_LABEL[c.method] ?? c.method}</p>
      {c.screenshot && <ClientProof src={c.screenshot} />}
      {c.transcript && <TranscriptProof url={c.transcript.url} caption={c.transcript.caption} />}
      {c.method !== 'none' && c.status !== 'planned' && <Link className="client-link" to={`/connect?client=${encodeURIComponent(c.id)}`}>How to connect</Link>}
    </li>
  )
}

export default function Integrations() {
  const { status, data, error } = useConnect()
  const groups = groupByStatus(data?.clients)
  return (
    <main>
      <header className="page-head">
        <h1 className="page-title">What Sentinel works with.</h1>
        <p className="page-lede">Anything that speaks MCP can be routed through Sentinel. The labels below say what we have actually run.</p>
      </header>
      {status === 'loading' && <p className="block muted" role="status">Loading...</p>}
      {status === 'error' && <p className="block muted" role="status">The list of clients could not be loaded from Sentinel. {error}</p>}
      {groups.map((g) => (
        <section key={g.status} className="block" aria-labelledby={`g-${g.status}`}>
          <div className="group-head">
            <h2 id={`g-${g.status}`} className="visually-hidden">{g.status}</h2>
            <StatusBadge status={g.status} />
            <p className="muted group-meaning">{STATUS_MEANING[g.status]}</p>
          </div>
          <ul className="client-list">{g.clients.map((c) => <ClientCard key={c.id} c={c} />)}</ul>
        </section>
      ))}
    </main>
  )
}
