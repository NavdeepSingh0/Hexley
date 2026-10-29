// Dev page: the mascot in the site's own React app, every state on demand, with a message, a size and a bubble placement.
// The same component also works in a plain HTML page (design/mascot/preview.html). Phase F1 of docs/plans/BUILD_PLAN.md.
import { useState } from 'react'
import { STATES } from '../../../design/mascot/sentinel-mascot.js'

const SAY = {
  sleeping: '', idle: '', checking: '', allowed: 'Checked: allowed.', denied: 'That would send restricted data out.',
  'needs-approval': "This needs the officer's approval.", quarantined: 'Too many denied attempts: quarantined.',
  verified: 'Audit log intact.', tamper: 'The audit log was altered!',
}
const TOUR = ['sleeping', 'idle', 'checking', 'allowed', 'checking', 'denied', 'needs-approval', 'idle', 'checking', 'denied', 'quarantined', 'verified', 'tamper', 'idle']

export default function Mascot() {
  const [state, setState] = useState('idle')
  const [message, setMessage] = useState('')
  const [size, setSize] = useState('96')
  const [placement, setPlacement] = useState('left')
  const [touring, setTouring] = useState(false)

  const pick = (s) => { setState(s); setMessage(SAY[s]) }
  const tour = async () => {
    setTouring(true)
    for (const s of TOUR) { pick(s); await new Promise((r) => setTimeout(r, 1800)) }
    setTouring(false)
  }

  return (
    <main className="sg" data-dev-page="MASCOT_PAGE_DEV_ONLY">
      <p className="s-label">Dev page · phase F1</p>
      <h1 className="sg-title">Mascot</h1>
      <p className="sg-lede">An original rounded screen-cube robot, drawn as an animated SVG. It shows the state it is given and says what it is told.</p>

      <div className="sg-row" role="group" aria-label="State">
        {STATES.map((s) => (
          <button key={s} className={`s-btn s-btn--small ${state === s ? 's-btn--primary' : 's-btn--ghost'}`} onClick={() => pick(s)}>{s}</button>
        ))}
      </div>

      <div className="sg-row" style={{ margin: 'var(--space-3) 0' }}>
        <input className="mascot-input" value={message} onChange={(e) => setMessage(e.target.value)} maxLength={200}
          placeholder="What it says (90 characters at most)" aria-label="Message" />
        <select className="mascot-input" value={size} onChange={(e) => setSize(e.target.value)} aria-label="Size">
          {['48', '64', '96', '128', '192'].map((n) => <option key={n}>{n}</option>)}
        </select>
        <select className="mascot-input" value={placement} onChange={(e) => setPlacement(e.target.value)} aria-label="Bubble placement">
          <option value="left">bubble left</option><option value="below">bubble below</option><option value="above">bubble above</option>
        </select>
        <button className="s-btn s-btn--ghost s-btn--small" disabled={touring} onClick={tour}>{touring ? 'Touring…' : 'Play a tour'}</button>
      </div>

      <div className="s-panel mascot-stage">
        <sentinel-mascot state={state} message={message} size={size} placement={placement} />
      </div>
    </main>
  )
}
