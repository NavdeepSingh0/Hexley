import { Link } from 'react-router-dom'

// The closing band: a full-width violet frame, a short headline, two buttons, and the mascot (at its usual size) peeking up
// from the bottom edge. The mascot is at rest; it does not claim a decision.
export default function CtaBand() {
  return (
    <section className="band" aria-labelledby="band-h">
      <div className="band-inner">
        <h2 id="band-h" className="band-title">Watch an attack get stopped.</h2>
        <p className="band-lede">Run the guided demo, or try an agent in the chat. Nothing to install to look.</p>
        <div className="band-actions">
          <a className="s-btn band-btn band-btn--solid" href="/console/">See it work</a>
          <Link className="s-btn band-btn band-btn--line" to="/chat">Open the chat</Link>
        </div>
      </div>
      <div className="band-mascot" aria-hidden="true"><sentinel-mascot state="idle" size="200" /></div>
    </section>
  )
}
