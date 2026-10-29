// The mascot lab: a page for judging the mascot's animation. It exists only in the development server (App.jsx adds the
// route behind import.meta.env.DEV and the production build is checked for it), so it is never part of the final run.
import { useEffect, useMemo, useRef, useState } from 'react'
import { STATES } from '../../../design/mascot/sentinel-mascot.js'
import { MASCOT_LAB_DEV_ONLY, SAY, SCENARIOS, STATE_INFO, allTransitions, dwell, trace } from '../lib/mascotLab.js'
import '../styles/lab.css'

export { MASCOT_LAB_DEV_ONLY }

const SPEEDS = [[0, 'Freeze'], [0.25, '0.25×'], [0.5, '0.5×'], [1, '1×'], [2, '2×']]
const SIZES = [64, 96, 128, 160]
const BACKGROUNDS = [['dark', 'Dark page'], ['light', 'Light page'], ['violet', 'Violet']]
const MATRIX_SIZES = [32, 48, 64, 96, 128]
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

// One mascot with the lab's review attributes. `still` is a boolean attribute: present or absent.
function M({ state, message = '', size, speed, still, placement = 'below', theme }) {
  return <sentinel-mascot state={state} message={message} size={String(size)} speed={String(speed)} still={still ? '' : undefined} placement={placement} theme={theme} />
}

// Plays a list of steps one after another on the stage; a new play (or Stop) cancels the one before.
function usePlayer(apply, speed) {
  const token = useRef(0)
  const speedRef = useRef(speed)
  speedRef.current = speed
  const [playing, setPlaying] = useState(null) // { id, index, label }
  const stop = () => { token.current += 1; setPlaying(null) }
  const play = async (id, steps, label = () => '') => {
    const mine = ++token.current
    for (let i = 0; i < steps.length; i += 1) {
      if (token.current !== mine) return
      setPlaying({ id, index: i, label: label(i) })
      apply(steps[i])
      await sleep(dwell(steps[i].ms, speedRef.current))
    }
    if (token.current === mine) setPlaying(null)
  }
  useEffect(() => () => { token.current += 1 }, [])
  return { playing, play, stop }
}

// How far the body travels in each direction over the first 4 seconds after entering a state, from the real motion function.
function Trace({ state }) {
  const t = useMemo(() => trace(state), [state])
  const W = 220
  const H = 64
  const RANGE = 12 // pixels; the same scale on every card, so a quiet state looks quiet
  const x = (s) => (s.t / 4) * W
  const y = (v) => H / 2 - (Math.max(-RANGE, Math.min(RANGE, v)) / RANGE) * (H / 2 - 3)
  const line = (pick) => t.samples.map((s) => `${x(s).toFixed(1)},${y(pick(s)).toFixed(1)}`).join(' ')
  const f = (n) => n.toFixed(1)
  return (
    <figure className="lab-trace">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Movement of the ${state} state over four seconds`}>
        <line x1="0" x2={W} y1={H / 2} y2={H / 2} className="lab-trace-axis" />
        <polyline points={line((s) => s.dx)} className="lab-trace-dx" fill="none" />
        <polyline points={line((s) => s.dy)} className="lab-trace-dy" fill="none" />
      </svg>
      <figcaption>
        <span><i className="lab-key lab-key--dy" />up and down</span> <span><i className="lab-key lab-key--dx" />sideways</span> <span className="muted">±{RANGE} px, 4 s</span>
        <br />
        Entry: {f(t.peak.dy)} px up/down, {f(t.peak.dx)} px sideways, tilt {f(t.peak.rot)}°, squash {f(t.peak.scale * 100)}%
        <br />
        Then it waits: {f(t.steady.dy)} px up/down, {f(t.steady.dx)} px sideways, gaze {f(t.steady.gaze)} px, tilt {f(t.steady.rot)}°
      </figcaption>
    </figure>
  )
}

function StateCard({ state, size, speed, still, speech, onStage }) {
  const [shown, setShown] = useState(state)
  const timer = useRef(0)
  // Replay the entry: step out to another state, then back, so the reaction at the start happens again.
  const replay = () => {
    clearTimeout(timer.current)
    setShown(state === 'idle' ? 'checking' : 'idle')
    timer.current = setTimeout(() => setShown(state), Math.round(700 / Math.max(speed, 0.25)))
  }
  useEffect(() => () => clearTimeout(timer.current), [])
  const info = STATE_INFO[state]
  return (
    <article className="s-panel lab-card">
      <div className="lab-card-top" style={{ minHeight: size + (speech && SAY[state] ? 78 : 24) }}>
        <M state={shown} message={speech ? SAY[state] : ''} size={size} speed={speed} still={still} placement="below" />
      </div>
      <h3 className="lab-name">{state}</h3>
      <dl className="lab-facts">
        <dt>When</dt><dd>{info.trigger}</dd>
        <dt>Holds</dt><dd>{info.holds}</dd>
        <dt>Moves</dt><dd>{info.motion}</dd>
      </dl>
      <Trace state={state} />
      <div className="lab-actions">
        <button type="button" className="s-btn s-btn--ghost s-btn--small" onClick={replay}>Replay entry</button>
        <button type="button" className="s-btn s-btn--ghost s-btn--small" onClick={() => onStage(state)}>Show on stage</button>
      </div>
    </article>
  )
}

export default function MascotLab() {
  const [speed, setSpeed] = useState(1)
  const [size, setSize] = useState(96)
  const [still, setStill] = useState(false)
  const [speech, setSpeech] = useState(true)
  const [stage, setStage] = useState({ state: 'idle', message: '' })
  const [from, setFrom] = useState('idle')
  const [to, setTo] = useState('allowed')

  const apply = (s) => setStage({ state: s.state, message: speech ? (s.message ?? SAY[s.state] ?? '') : '' })
  const { playing, play, stop } = usePlayer(apply, speed)
  const pick = (state) => { stop(); setStage({ state, message: speech ? SAY[state] : '' }) }
  const transitions = useMemo(() => allTransitions(), [])
  const playPair = () => play('pair', [{ state: from, ms: 1100 }, { state: to, ms: 2200, message: SAY[to] }], (i) => (i === 0 ? `${from}` : `${from} → ${to}`))
  const playAll = () => play('all', transitions.flatMap((t) => [{ state: t.from, ms: 900 }, { state: t.to, ms: 1300, message: SAY[t.to] }]),
    (i) => `${transitions[Math.floor(i / 2)].from} → ${transitions[Math.floor(i / 2)].to}  (${Math.floor(i / 2) + 1} of ${transitions.length})`)

  return (
    <main className="lab">
      <header className="lab-head">
        <p className="s-label">Development only · not part of the production build</p>
        <h1 className="lab-title">Mascot lab</h1>
        <p className="lab-lede">Every state alive at once, how far it really moves, every change of state, and the sequences the app plays. Use Freeze and 0.25× to look at a reaction frame by frame.</p>
      </header>

      <div className="lab-controls" role="group" aria-label="Playback">
        <div className="lab-group" role="group" aria-label="Speed">
          <span className="s-label">Speed</span>
          {SPEEDS.map(([v, label]) => (
            <button key={v} type="button" aria-pressed={speed === v} className={`s-btn s-btn--small ${speed === v ? 's-btn--primary' : 's-btn--ghost'}`} onClick={() => setSpeed(v)}>{label}</button>
          ))}
        </div>
        <label className="lab-group"><span className="s-label">Cards</span>
          <select className="mascot-input" value={size} onChange={(e) => setSize(Number(e.target.value))} aria-label="Size in the cards">
            {SIZES.map((n) => <option key={n} value={n}>{n} px</option>)}
          </select>
        </label>
        <label className="lab-check"><input type="checkbox" checked={still} onChange={(e) => setStill(e.target.checked)} /> Reduced motion (still pose)</label>
        <label className="lab-check"><input type="checkbox" checked={speech} onChange={(e) => setSpeech(e.target.checked)} /> Speech bubbles</label>
      </div>

      <section className="lab-section" aria-labelledby="stage-h">
        <h2 id="stage-h" className="lab-h2">Stage</h2>
        <div className="lab-stage s-panel">
          <div className="lab-stage-mascot" style={{ minHeight: 160 + 96 }}>
            <M state={stage.state} message={stage.message} size={160} speed={speed} still={still} placement="below" />
          </div>
          <div className="lab-stage-side">
            <p className="lab-stage-state" aria-live="polite">{stage.state}</p>
            <p className="muted lab-stage-note">{playing ? `Playing: ${playing.label || playing.id}` : 'Pick a state, or play something below.'}</p>
            <div className="lab-pick" role="group" aria-label="State on the stage">
              {STATES.map((s) => (
                <button key={s} type="button" aria-pressed={stage.state === s} className={`s-btn s-btn--small ${stage.state === s ? 's-btn--primary' : 's-btn--ghost'}`} onClick={() => pick(s)}>{s}</button>
              ))}
            </div>
            {playing && <button type="button" className="s-btn s-btn--ghost s-btn--small" onClick={stop}>Stop playing</button>}
          </div>
        </div>
      </section>

      <section className="lab-section" aria-labelledby="gallery-h">
        <h2 id="gallery-h" className="lab-h2">All nine, alive</h2>
        <p className="muted lab-sub">Each card holds its own state. Replay entry shows the reaction at the start again. The graph is the real movement function, on the same scale for every card.</p>
        <div className="lab-grid">
          {STATES.map((s) => (
            <StateCard key={s} state={s} size={size} speed={speed} still={still} speech={speech} onStage={pick} />
          ))}
        </div>
      </section>

      <section className="lab-section" aria-labelledby="change-h">
        <h2 id="change-h" className="lab-h2">Change of state</h2>
        <p className="muted lab-sub">The eyes, colours and body morph from one pose to the next. Choose two states, or run all 72 changes in a row on the stage.</p>
        <div className="lab-row">
          <label className="lab-group"><span className="s-label">From</span>
            <select className="mascot-input" value={from} onChange={(e) => setFrom(e.target.value)}>{STATES.map((s) => <option key={s}>{s}</option>)}</select>
          </label>
          <label className="lab-group"><span className="s-label">To</span>
            <select className="mascot-input" value={to} onChange={(e) => setTo(e.target.value)}>{STATES.map((s) => <option key={s}>{s}</option>)}</select>
          </label>
          <button type="button" className="s-btn s-btn--primary s-btn--small" onClick={playPair} disabled={from === to}>Play this change</button>
          <button type="button" className="s-btn s-btn--ghost s-btn--small" onClick={playAll}>Play all 72</button>
          {playing && <button type="button" className="s-btn s-btn--ghost s-btn--small" onClick={stop}>Stop</button>}
        </div>
        <p className="lab-progress" aria-live="polite">{playing && (playing.id === 'pair' || playing.id === 'all') ? playing.label : ''}</p>
      </section>

      <section className="lab-section" aria-labelledby="seq-h">
        <h2 id="seq-h" className="lab-h2">What the app plays</h2>
        <p className="muted lab-sub">The same state changes the console and the chat make for a real run, on the stage above, with the words the app uses.</p>
        <div className="lab-scenarios">
          {SCENARIOS.map((sc) => (
            <article key={sc.id} className="s-panel lab-scenario">
              <div className="lab-scenario-head">
                <h3 className="lab-name">{sc.title}</h3>
                <button type="button" className="s-btn s-btn--small s-btn--ghost" onClick={() => play(sc.id, sc.steps, (i) => sc.steps[i].note)}>
                  {playing?.id === sc.id ? 'Restart' : 'Play'}
                </button>
              </div>
              <ol className="lab-steps">
                {sc.steps.map((s, i) => (
                  <li key={i} className={playing?.id === sc.id && playing.index === i ? 'is-now' : ''}>
                    <span className="lab-step-state">{s.state}</span> <span className="muted">{s.note}</span>
                  </li>
                ))}
              </ol>
            </article>
          ))}
        </div>
      </section>

      <section className="lab-section" aria-labelledby="sizes-h">
        <h2 id="sizes-h" className="lab-h2">Sizes and backgrounds</h2>
        <p className="muted lab-sub">Whatever is on the stage, at the sizes the app uses, on a dark page, a light page and a violet one.</p>
        <div className="lab-bgs">
          {BACKGROUNDS.map(([bg, label]) => (
            <div key={bg} className={`lab-bg lab-bg--${bg}`}>
              <p className="lab-bg-label">{label}</p>
              <div className="lab-bg-row">
                {MATRIX_SIZES.map((n) => (
                  <figure key={n} className="lab-size">
                    <M state={stage.state} size={n} speed={speed} still={still} theme={bg === 'dark' ? 'dark' : 'light'} />
                    <figcaption>{n}</figcaption>
                  </figure>
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>
    </main>
  )
}
