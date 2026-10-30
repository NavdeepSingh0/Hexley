import { Link } from 'react-router-dom'
import { Feature, Icon, PageHead } from '../components/Blocks.jsx'
import CtaBand from '../components/CtaBand.jsx'
import { ClientProof, StatusBadge, TranscriptProof } from '../components/Ui.jsx'
import { KIND_LABEL, METHOD_LABEL, STATUS_MEANING, groupByStatus, useConnect } from '../lib/connect.js'

// What a Tested label stands on: the real screenshot or captured session the gateway lists for that client. Whatever the
// gateway lists is shown; nothing is added here.
function Proof({ c }) {
  if (!c.screenshot && !c.transcript) return <p className="ig-visual-note">No recording is attached to this client yet.</p>
  return (
    <>
      {c.screenshot && <ClientProof src={c.screenshot} />}
      {c.transcript && <TranscriptProof url={c.transcript.url} caption={c.transcript.caption} />}
    </>
  )
}

function Card({ c }) {
  const connectable = c.method !== 'none' && c.status !== 'planned'
  return (
    <li className="ig-card">
      <div className="ig-card-top"><span>{KIND_LABEL[c.kind] ?? c.kind}</span><StatusBadge status={c.status} /></div>
      <h3 className="ig-name">{c.name}</h3>
      <p className="ig-method">{METHOD_LABEL[c.method] ?? c.method}</p>
      {connectable && <Link className="ig-link" to={`/connect?client=${encodeURIComponent(c.id)}`}>How to connect <Icon name="arrow" size={15} /></Link>}
    </li>
  )
}

export default function Integrations() {
  const { status, data, error } = useConnect()
  const groups = groupByStatus(data?.clients)
  const tested = groups.find((g) => g.status === 'tested')?.clients ?? []
  const others = groups.filter((g) => g.status !== 'tested')
  return (
    <main>
      <PageHead label="Integrations" title="What Hexley works with." lede="Anything that speaks MCP can be routed through Hexley. The labels say what we have actually run, and only a Tested label comes with its evidence." />
      {status === 'loading' && <p className="section muted" role="status">Loading...</p>}
      {status === 'error' && <p className="section muted" role="status">The list of clients could not be loaded from Hexley. {error}</p>}
      {tested.map((c, i) => (
        <Feature
          key={c.id} id={c.id} flip={i % 2 === 1}
          label={`Tested · ${KIND_LABEL[c.kind] ?? c.kind}`} title={c.name}
          bullets={[`How it connects: ${METHOD_LABEL[c.method] ?? c.method}`, STATUS_MEANING.tested]}
          link={c.method !== 'none' ? { to: `/connect?client=${encodeURIComponent(c.id)}`, label: 'How to connect' } : null}
          visual={<Proof c={c} />}
        />
      ))}
      {others.map((g) => (
        <section key={g.status} className="section" aria-labelledby={`g-${g.status}`}>
          <div className="ig-group-head">
            <h2 id={`g-${g.status}`} className="ig-h2">{g.status === 'should_work' ? 'Should work' : 'Planned'}</h2>
            <p>{STATUS_MEANING[g.status]}</p>
          </div>
          <ul className="ig-grid">{g.clients.map((c) => <Card key={c.id} c={c} />)}</ul>
        </section>
      ))}
      <p className="section ig-note">MCP is how AI apps connect to tools. <Link to="/docs/concepts">How the gateway fits in</Link>.</p>
      <CtaBand />
    </main>
  )
}
