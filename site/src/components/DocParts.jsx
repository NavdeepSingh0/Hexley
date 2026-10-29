import { ClientProof, TranscriptProof } from './Ui.jsx'
import { useConnect } from '../lib/connect.js'

// The evidence for one client, read from the gateway's own client list, so the docs never claim a status the gateway does not.
export function ClientEvidence({ id }) {
  const { status, data } = useConnect()
  const c = data?.clients?.find((x) => x.id === id)
  if (status === 'loading') return <p className="muted" role="status">Loading...</p>
  if (!c) return <p className="muted" role="status">The gateway is not reachable, so the evidence is not shown here. See the Integrations page.</p>
  if (c.status !== 'tested') return <p className="muted">This client is marked "{c.status.replace('_', ' ')}": we have not run it, so there is no evidence to show.</p>
  return (
    <>
      {c.screenshot && <ClientProof src={c.screenshot} />}
      {c.transcript && <TranscriptProof url={c.transcript.url} caption={c.transcript.caption} />}
    </>
  )
}
