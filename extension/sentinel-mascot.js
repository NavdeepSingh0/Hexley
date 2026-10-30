// <sentinel-mascot>: Hexley's mascot, a rounded screen-cube robot drawn as an animated SVG (docs/contracts/MASCOT.md).
// One file, no dependencies, no network, works in a plain HTML page, in the console and site bundles, and in an extension.
// It only ever shows the state it is told (`state` attribute), and what it says is the `message` attribute: it decides nothing.
//
// Motion: every eye is a set of numbers that ease toward the next state's numbers each frame (so a change of state is a
// morph, not a cut); the body bobs, blinks, and pops or shakes when a decision lands. `prefers-reduced-motion` shows the
// finished pose with no animation at all.
//
// Boosters: `liftoff()` (or a `liftoff` attribute present when it connects) plays a one-off launch: two small thrusters slide
// out under the body, flames light, the body rises, hovers and settles back. It is decoration for the home page and the mascot lab;
// it is not a state and says nothing about any decision. With reduced motion (or `still`) it does nothing.
//
// The pure parts (states, poses, easing, motion, speech timing, the liftoff curve) are exported and tested in Node; the element is
// checked in a real browser.

export const STATES = ['sleeping', 'idle', 'checking', 'allowed', 'denied', 'needs-approval', 'quarantined', 'verified', 'tamper']
export const MAX_MESSAGE = 90
export const BUBBLE_MS = 6000
export const PERSISTENT = new Set(['quarantined', 'needs-approval']) // the bubble stays up while the state lasts

export const normalizeState = (s) => (STATES.includes(s) ? s : 'idle')
export const truncateMessage = (m, n = MAX_MESSAGE) => {
  const t = String(m ?? '').replace(/\s+/g, ' ').trim()
  return t.length > n ? `${t.slice(0, n - 1).trimEnd()}…` : t
}
// The `speed` review attribute: a time scale for the whole animation (0 freezes it, 0.25 is slow motion, 4 at most).
// Missing or unusable means 1. Only the mascot lab sets it.
export const parseSpeed = (v) => { const n = parseFloat(v); return Number.isFinite(n) ? Math.min(4, Math.max(0, n)) : 1 }
// Is the speech bubble showing, `ageMs` after it was set?
export const bubbleVisible = (state, message, ageMs) => Boolean(message) && (PERSISTENT.has(state) || ageMs < BUBBLE_MS)

// ---- colours -------------------------------------------------------------------------------------------------------------
const hex = (h) => { const n = parseInt(h.slice(1), 16); return [(n >> 16) & 255, (n >> 8) & 255, n & 255] }
const C = { white: hex('#FFFFFF'), violet: hex('#A98BFF'), green: hex('#34E8A3'), blue: hex('#5B9BFF'), amber: hex('#FFB62E'),
  red: hex('#FF5468'), muted: hex('#A9A9BC'), ink: hex('#07070A') }
const lerp = (a, b, t) => a + (b - a) * t
const mix = (a, b, t) => [lerp(a[0], b[0], t), lerp(a[1], b[1], t), lerp(a[2], b[2], t)]
const css = (c) => `rgb(${Math.round(c[0])},${Math.round(c[1])},${Math.round(c[2])})`

// ---- poses ---------------------------------------------------------------------------------------------------------------
// The face lives on a dark screen (x 48..152, y 62..134), eyes centred on y = 98. Each eye is two 3-point polylines (A, B)
// drawn with a thick round stroke: a bar is a vertical line, a flat eye a horizontal one, a "^" or a tick has a corner, and a
// cross uses both polylines. B normally lies exactly on A, so a morph to a cross is a slide, not a pop.
const LX = 78
const RX = 122
const CY = 98
const bar = (cx, h) => { const p = [cx, CY - h, cx, CY, cx, CY + h]; return { A: p, B: p } }
const flat = (cx, hw) => { const p = [cx - hw, CY, cx, CY, cx + hw, CY]; return { A: p, B: p } }
const happy = (cx) => { const p = [cx - 11, CY + 8, cx, CY - 9, cx + 11, CY + 8]; return { A: p, B: p } }
const tick = (cx) => { const p = [cx - 11, CY + 1, cx - 3, CY + 11, cx + 12, CY - 10]; return { A: p, B: p } }
const cross = (cx) => ({ A: [cx - 10, CY - 12, cx, CY, cx + 10, CY + 12], B: [cx + 10, CY - 12, cx, CY, cx - 10, CY + 12] })

export const POSES = {
  sleeping: { L: flat(LX, 11), R: flat(RX, 11), sw: [5, 5], eye: C.muted, dot: C.muted, z: 1 },
  idle: { L: bar(LX, 14), R: bar(RX, 14), sw: [15, 15], eye: C.white, dot: C.violet },
  checking: { L: bar(LX, 13), R: bar(RX, 13), sw: [15, 15], eye: C.violet, dot: C.violet },
  allowed: { L: happy(LX), R: happy(RX), sw: [8, 8], eye: C.green, dot: C.green },
  denied: { L: flat(LX, 13), R: flat(RX, 13), sw: [9, 9], eye: C.blue, dot: C.blue },
  'needs-approval': { L: bar(LX, 10), R: bar(RX, 17), sw: [15, 15], eye: C.amber, dot: C.amber, q: 1 },
  quarantined: { L: bar(LX, 10), R: bar(RX, 10), sw: [14, 14], eye: C.ink, dot: C.ink, inv: 1 },
  verified: { L: tick(LX), R: tick(RX), sw: [8, 8], eye: C.green, dot: C.green },
  tamper: { L: cross(LX), R: cross(RX), sw: [8, 8], eye: C.red, dot: C.red },
}

// The pose as one flat vector of numbers, so easing is a single loop. Layout:
// 0-5 left A, 6-11 left B, 12-17 right A, 18-23 right B, 24-25 stroke widths, 26 inversion, 27 "z" alpha, 28 "?" alpha,
// 29-31 eye colour, 32-34 badge-dot colour.
export const VECTOR_LENGTH = 35
export function poseVector(state) {
  const p = POSES[normalizeState(state)]
  return [...p.L.A, ...p.L.B, ...p.R.A, ...p.R.B, p.sw[0], p.sw[1], p.inv ?? 0, p.z ?? 0, p.q ?? 0, ...p.eye, ...p.dot]
}

// Move `cur` toward `target` by an exponential ease: frame-rate independent, no overshoot. `tau` is the time constant (s).
export function easeToward(cur, target, dt, tau = 0.12) {
  const k = 1 - Math.exp(-dt / tau)
  return cur.map((c, i) => c + (target[i] - c) * k)
}

// ---- motion --------------------------------------------------------------------------------------------------------------
const hash = (n) => { const x = Math.sin(n * 127.1) * 43758.5453; return x - Math.floor(x) } // deterministic jitter
const pop = (age) => { const s = Math.exp(-age * 7) * Math.cos(age * 18); return { sx: 1 - 0.07 * s, sy: 1 + 0.09 * s, dy: age < 0.3 ? -9 * Math.sin((age / 0.3) * Math.PI) : 0 } }
const shake = (age) => 7 * Math.exp(-age * 6) * Math.sin(age * 45)

// Where the body and the gaze are at time `t` (s), `age` seconds after entering `state`. Pure and deterministic.
export function motionAt(state, t, age) {
  const w = (period) => Math.sin((2 * Math.PI * t) / period)
  const m = { dx: 0, dy: 0, sx: 1, sy: 1, rot: 0, gx: 0, gy: 0 }
  switch (normalizeState(state)) {
    case 'sleeping':
      m.sy = 1 + 0.015 * w(4.5); m.sx = 1 - 0.008 * w(4.5)
      break
    case 'idle':
      m.dy = -3 * w(3.4); m.gx = 3 * Math.sin(t * 0.6); m.gy = 1.5 * Math.sin(t * 0.9)
      break
    case 'checking':
      m.dy = -2 * w(1.2); m.gx = 9 * Math.sin(t * 3.2)
      break
    case 'allowed': { const p = pop(age); m.dy = -2 * w(3) + p.dy; m.sx = p.sx; m.sy = p.sy; break }
    case 'denied':
      m.dy = -1.5 * w(3); m.dx = shake(age)
      break
    case 'needs-approval':
      m.dy = -2 * w(2); m.rot = 2.5 * Math.sin(t * 2.4)
      break
    case 'quarantined': {
      const s = Math.exp(-age * 8)
      m.dy = -0.8 * w(5) + 4 * s; m.sy = 1 - 0.12 * s; m.sx = 1 + 0.06 * s
      break
    }
    case 'verified': { const p = pop(age); m.dy = -2 * w(3) + p.dy; m.sx = p.sx; m.sy = p.sy; break }
    case 'tamper': {
      const j = Math.floor(t * 12)
      m.dx = (hash(j) - 0.5) * 5 + shake(age); m.dy = (hash(j + 91) - 0.5) * 3; m.rot = (hash(j + 17) - 0.5) * 3
      break
    }
    default:
  }
  return m
}

// Blink: 1 = open, down to 0.1 mid-blink; a blink lasts 0.14 s.
export const blinkScale = (sinceBlinkStart) => (sinceBlinkStart < 0 || sinceBlinkStart > 0.14 ? 1 : 1 - 0.9 * Math.sin((sinceBlinkStart / 0.14) * Math.PI))
const BLINKS = new Set(['idle', 'checking', 'needs-approval'])

// ---- liftoff (the boosters) ----------------------------------------------------------------------------------------------
// One launch, `age` seconds after it starts: nozzles slide out (0 to 0.5 s) with a small crouch, flames light and the body rises
// (0.5 to 1.3), hovers (to 2.6), descends as the flames taper off (out by 3.4), lands with a squash (3.5) and the nozzles slide
// back in (to 4.2).
// Pure and deterministic. `flame` and `nozzle` run from 0 to 1; offsets are in drawing units (the drawing is 200 wide).
export const LIFTOFF_S = 4.2
export const LIFT_MAX = 26
const smooth = (x) => { const u = Math.min(1, Math.max(0, x)); return u * u * (3 - 2 * u) }
export function liftoffAt(age) {
  const rest = { dy: 0, sx: 1, sy: 1, rot: 0, flame: 0, nozzle: 0, lift: 0 }
  if (!(age >= 0) || age >= LIFTOFF_S) return rest
  const nozzle = age < 0.5 ? smooth(age / 0.5) : age < 3.6 ? 1 : 1 - smooth((age - 3.6) / 0.6)
  let lift = 0
  if (age >= 0.5 && age < 1.3) lift = smooth((age - 0.5) / 0.8)
  else if (age >= 1.3 && age < 2.6) lift = 1
  else if (age >= 2.6 && age < 3.5) lift = 1 - smooth((age - 2.6) / 0.9)
  let flame = 0 // lit only once the nozzles are fully out (0.5 s), out before touch-down
  if (age >= 0.5 && age < 0.75) flame = 0.35 * smooth((age - 0.5) / 0.25)
  else if (age >= 0.75 && age < 1.2) flame = 0.35 + 0.65 * smooth((age - 0.75) / 0.45)
  else if (age >= 1.2 && age < 1.6) flame = 1 - 0.2 * smooth((age - 1.2) / 0.4)
  else if (age >= 1.6 && age < 2.6) flame = 0.8
  else if (age >= 2.6 && age < 3.4) flame = 0.8 * (1 - smooth((age - 2.6) / 0.8))
  const crouch = Math.sin(Math.PI * Math.min(1, Math.max(0, (age - 0.15) / 0.35))) // 0 outside 0.15 to 0.5 s
  const rise = age >= 0.5 && age < 1.3 ? Math.sin((Math.PI * (age - 0.5)) / 0.8) : 0
  const land = age >= 3.5 ? Math.exp(-(age - 3.5) * 9) * Math.cos((age - 3.5) * 16) : 0
  return {
    dy: -LIFT_MAX * lift + 3 * crouch + lift * lift * 1.8 * Math.sin(age * 4.6),
    sx: 1 + 0.03 * crouch + 0.035 * land - 0.02 * rise,
    sy: 1 - 0.06 * crouch + 0.04 * rise - 0.07 * land,
    rot: 1.6 * Math.sin(age * 2.1) * lift,
    flame, nozzle, lift,
  }
}

// ---- the element ---------------------------------------------------------------------------------------------------------
const BUBBLE_THEME = {
  dark: { bg: '#212130', fg: '#FFFFFF', line: '#2A2A36' },
  light: { bg: '#FFFFFF', fg: '#0A0A10', line: '#D9D6EA' },
}
let counter = 0

const TEMPLATE = (id) => `
<style>
  :host { display: inline-block; position: relative; z-index: 12; flex: none; box-sizing: border-box; width: var(--size, 64px); height: var(--size, 64px); line-height: 0; }
  svg { width: 100%; height: 100%; overflow: visible; display: block; }
  .bubble { position: absolute; width: max-content; max-width: 280px; padding: 10px 14px; border-radius: 14px; font: 14px/1.35 "Helvetica Neue", Helvetica, Arial, sans-serif;
    border: 1px solid var(--line); background: var(--bg); color: var(--fg); box-shadow: 0 8px 28px rgba(0,0,0,.35); opacity: 0; transform: scale(.94);
    transform-origin: var(--origin, right center); transition: opacity .2s ease, transform .2s ease; pointer-events: none; text-align: left; line-height: 1.35; }
  .bubble.show { opacity: 1; transform: none; }
  .bubble::after { content: ""; position: absolute; width: 10px; height: 10px; background: var(--bg); border: 1px solid var(--line); transform: rotate(45deg); }
  :host([placement="left"]) .bubble, :host(:not([placement])) .bubble { right: calc(100% + 10px); top: 50%; translate: 0 -50%; }
  :host([placement="left"]) .bubble::after, :host(:not([placement])) .bubble::after { right: -6px; top: calc(50% - 5px); border-left: none; border-bottom: none; }
  :host([placement="below"]) .bubble { top: calc(100% + 8px); right: 0; --origin: top right; }
  :host([placement="below"]) .bubble::after { top: -6px; right: 22px; border-right: none; border-bottom: none; }
  :host([placement="above"]) .bubble { bottom: calc(100% + 8px); left: 0; --origin: bottom left; }
  :host([placement="above"]) .bubble::after { bottom: -6px; left: 22px; border-left: none; border-top: none; }
</style>
<svg viewBox="0 0 200 200" role="img" aria-label="Hexley mascot">
  <defs>
    <linearGradient id="g${id}" x1="0" y1="0" x2="0" y2="1"><stop class="sa" offset="0"/><stop class="sb" offset="1"/></linearGradient>
    <linearGradient id="f${id}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#efe8ff" stop-opacity=".98"/><stop offset=".3" stop-color="#b79cff" stop-opacity=".95"/><stop offset=".7" stop-color="#8f5bff" stop-opacity=".6"/><stop offset="1" stop-color="#8f5bff" stop-opacity="0"/></linearGradient>
  </defs>
  <ellipse class="shadow" cx="100" cy="176" rx="58" ry="8" fill="#000" opacity=".28"/>
  <g class="body">
    <g class="boost" visibility="hidden" aria-hidden="true">
      ${['L', 'R'].map((side) => `<g class="nz nz${side}"><path d="M-10 0L10 0L7 11L-7 11Z" fill="#2a2a38" stroke="#a98bff" stroke-width="1.5" stroke-linejoin="round"/><path class="fo fo${side}" fill="url(#f${id})"/><path class="fi fi${side}" fill="#fff" opacity=".9"/></g>`).join('')}
    </g>
    <rect class="shell" x="30" y="36" width="140" height="128" rx="40" fill="url(#g${id})"/>
    <ellipse class="dome" cx="86" cy="50" rx="34" ry="8" fill="#fff" opacity=".8"/>
    <rect class="screen" x="48" y="62" width="104" height="72" rx="20"/>
    <g class="grid" stroke-opacity=".07" stroke-width="1">
      ${[0, 1, 2, 3, 4, 5, 6].map((i) => `<path d="M${65 + i * 12.3} 64v68"/>`).join('')}${[0, 1, 2, 3].map((i) => `<path d="M50 ${79.5 + i * 15}h100"/>`).join('')}
    </g>
    <g class="eyeL"><path class="la" fill="none" stroke-linecap="round" stroke-linejoin="round"/><path class="lb" fill="none" stroke-linecap="round" stroke-linejoin="round"/></g>
    <g class="eyeR"><path class="ra" fill="none" stroke-linecap="round" stroke-linejoin="round"/><path class="rb" fill="none" stroke-linecap="round" stroke-linejoin="round"/></g>
    <rect class="tile" x="126" y="140" width="28" height="18" rx="6"/>
    <circle class="dot" cx="140" cy="149" r="4"/>
    <rect class="vent" x="52" y="146" width="22" height="4" rx="2" opacity=".6"/>
  </g>
  <g class="zs" aria-hidden="true" font-family="Helvetica Neue, Arial, sans-serif" font-weight="800" fill="#A9A9BC"><text class="z0" font-size="18">z</text><text class="z1" font-size="23">z</text><text class="z2" font-size="28">z</text></g>
  <text class="q" aria-hidden="true" x="148" y="30" font-size="38" font-weight="800" font-family="Helvetica Neue, Arial, sans-serif" fill="#FFB62E">?</text>
</svg>
<div class="bubble" role="status" aria-live="polite"></div>`

const Base = typeof HTMLElement === 'undefined' ? class {} : HTMLElement

export class SentinelMascot extends Base {
  static get observedAttributes() { return ['state', 'message', 'size', 'theme', 'speak', 'placement', 'speed', 'still', 'liftoff'] }

  constructor() {
    super()
    this._v = poseVector('idle')
    this._target = this._v
    this._enter = 0
    this._born = 0
    this._raf = 0
    this._last = 0
    this._blinkAt = 0
    this._bubbleSet = 0
    this._bubbleTimer = 0
    this._reduced = false
    this._vnow = 0 // the animation's own clock (ms): real time scaled by `speed`
    this._speed = 1
    this._lift0 = -1 // when the current liftoff began on that clock (ms); -1 when none is playing
    this._wantLift = false // liftoff() was asked for before the element was ready
  }

  // Play the launch once. Does nothing under reduced motion or `still`: the finished pose is the mascot at rest.
  liftoff() {
    if (!this._el) { this._wantLift = true; return }
    if (this._reduced) return
    this._lift0 = this._vnow
    this._start()
  }

  get state() { return normalizeState(this.getAttribute('state')) }
  set state(v) { this.setAttribute('state', v) }

  connectedCallback() {
    if (!this.shadowRoot) {
      const root = this.attachShadow({ mode: 'open' })
      root.innerHTML = TEMPLATE(++counter)
      const q = (s) => root.querySelector(s)
      this._el = {
        svg: q('svg'), sa: q('.sa'), sb: q('.sb'), shadow: q('.shadow'), body: q('.body'), shell: q('.shell'), dome: q('.dome'), screen: q('.screen'),
        grid: q('.grid'), eyeL: q('.eyeL'), eyeR: q('.eyeR'), la: q('.la'), lb: q('.lb'), ra: q('.ra'), rb: q('.rb'), tile: q('.tile'), dot: q('.dot'),
        vent: q('.vent'), zs: [q('.z0'), q('.z1'), q('.z2')], q: q('.q'), bubble: q('.bubble'),
        boost: q('.boost'), nz: [q('.nzL'), q('.nzR')], fo: [q('.foL'), q('.foR')], fi: [q('.fiL'), q('.fiR')],
      }
    }
    this._mq = typeof matchMedia === 'function' ? matchMedia('(prefers-reduced-motion: reduce)') : null
    this._reduced = Boolean(this._mq?.matches) || this.hasAttribute('still')
    this._onMq = () => { this._reduced = Boolean(this._mq.matches) || this.hasAttribute('still'); this._settle(); this._start() }
    this._mq?.addEventListener?.('change', this._onMq)
    this._onVis = () => (document.hidden ? this._stop() : this._start())
    document.addEventListener('visibilitychange', this._onVis)
    if (typeof MutationObserver !== 'undefined') {
      this._mo = new MutationObserver(() => this._applyStatic())
      this._mo.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] })
    }
    this._applyStatic()
    this._speed = parseSpeed(this.getAttribute('speed'))
    this._born = performance.now()
    this._vnow = this._born
    this._enter = this._born
    this._target = poseVector(this.state)
    this._v = this._target.slice() // the first pose is shown at once; only later changes morph
    this._blinkAt = this._born + 1500
    this._settle()
    this._say(this.getAttribute('message'))
    this._start()
    if (this._wantLift || this.hasAttribute('liftoff')) { this._wantLift = false; this.liftoff() }
  }

  disconnectedCallback() {
    this._stop()
    clearTimeout(this._bubbleTimer)
    this._mq?.removeEventListener?.('change', this._onMq)
    this._mo?.disconnect()
    document.removeEventListener('visibilitychange', this._onVis)
  }

  attributeChangedCallback(name, oldValue, value) {
    if (!this._el || oldValue === value) return
    if (name === 'state') {
      this._target = poseVector(this.state)
      this._enter = this._vnow
      this._el.svg.setAttribute('aria-label', `Hexley mascot: ${this.state}`)
      if (this._reduced) this._settle()
      this._say(this.getAttribute('message')) // a persistent state keeps its words up; leaving one starts the clock
    } else if (name === 'message') this._say(value)
    else if (name === 'speed') this._speed = parseSpeed(value)
    else if (name === 'liftoff') { if (value !== null) this.liftoff() }
    else if (name === 'still') {
      this._reduced = Boolean(this._mq?.matches) || this.hasAttribute('still')
      if (this._reduced) { this._stop(); this._settle() } else this._start()
    }
    else if (name === 'size' || name === 'theme') this._applyStatic()
  }

  // size and theme
  _applyStatic() {
    const n = parseFloat(this.getAttribute('size'))
    this.style.setProperty('--size', `${Number.isFinite(n) && n > 0 ? n : 64}px`)
    // an explicit `theme` wins; otherwise the page's own <html data-theme> decides (and is watched, see connectedCallback)
    const explicit = this.getAttribute('theme')
    const page = typeof document !== 'undefined' && document.documentElement.dataset.theme === 'light' ? 'light' : 'dark'
    const t = BUBBLE_THEME[explicit === 'light' || explicit === 'dark' ? explicit : page]
    this._el.bubble.style.setProperty('--bg', t.bg)
    this._el.bubble.style.setProperty('--fg', t.fg)
    this._el.bubble.style.setProperty('--line', t.line)
    this._el.svg.setAttribute('aria-label', `Hexley mascot: ${this.state}`)
  }

  _say(raw) {
    const text = truncateMessage(raw)
    clearTimeout(this._bubbleTimer)
    const b = this._el.bubble
    if (!text) { b.classList.remove('show'); return }
    const changed = b.textContent !== text
    b.textContent = text
    b.classList.add('show')
    this._bubbleSet = performance.now()
    if (!PERSISTENT.has(this.state)) this._bubbleTimer = setTimeout(() => b.classList.remove('show'), BUBBLE_MS)
    if (changed && this.hasAttribute('speak') && typeof speechSynthesis !== 'undefined') {
      try { speechSynthesis.cancel(); speechSynthesis.speak(new SpeechSynthesisUtterance(text)) } catch { /* speech is optional */ }
    }
  }

  _start() {
    if (this._reduced || this._raf || document.hidden || !this.isConnected) return
    this._last = performance.now()
    const tick = (now) => {
      this._raf = requestAnimationFrame(tick)
      const dt = Math.min(0.05, (now - this._last) / 1000) * this._speed
      this._last = now
      this._vnow += dt * 1000
      this._v = easeToward(this._v, this._target, dt, 0.12)
      this._render(this._vnow)
    }
    this._raf = requestAnimationFrame(tick)
  }

  _stop() { if (this._raf) cancelAnimationFrame(this._raf); this._raf = 0 }

  // Reduced motion (or a snap): show the finished pose, still.
  _settle() {
    this._v = this._target.slice()
    this._render(this._vnow, true)
  }

  // The thrusters: nozzles slide out of the underside, flames flicker below them. Hidden whenever no launch is playing.
  _drawBoost(L, now) {
    const e = this._el
    if (!L || (L.nozzle <= 0 && L.flame <= 0)) { e.boost.setAttribute('visibility', 'hidden'); return }
    e.boost.setAttribute('visibility', 'visible')
    const t = now / 1000
    ;[84, 116].forEach((x, i) => {
      e.nz[i].setAttribute('transform', `translate(${x} ${(164 - 11 * (1 - L.nozzle)).toFixed(2)})`)
      const f = 1 + 0.1 * Math.sin(t * 53 + i * 2.1) + 0.07 * Math.sin(t * 89 + i)
      const len = L.flame * 58 * f
      const fl = (w, k) => (len < 1 ? '' : `M${-w} 11C${-w - 1} ${(11 + len * k * 0.45).toFixed(1)} ${-w * 0.4} ${(11 + len * k * 0.8).toFixed(1)} 0 ${(11 + len * k).toFixed(1)}C${w * 0.4} ${(11 + len * k * 0.8).toFixed(1)} ${w + 1} ${(11 + len * k * 0.45).toFixed(1)} ${w} 11Z`)
      e.fo[i].setAttribute('d', fl(8.5, 1)); e.fi[i].setAttribute('d', fl(4, 0.55))
    })
  }

  _render(now, still = this._reduced) {
    const v = this._v
    const e = this._el
    const t = (now - this._born) / 1000
    const age = (now - this._enter) / 1000
    const m = still ? { dx: 0, dy: 0, sx: 1, sy: 1, rot: 0, gx: 0, gy: 0 } : motionAt(this.state, t, age)
    const L = !still && this._lift0 >= 0 ? liftoffAt((now - this._lift0) / 1000) : null
    if (L) { m.dy += L.dy; m.sx *= L.sx; m.sy *= L.sy; m.rot += L.rot }
    if (this._lift0 >= 0 && (still || (now - this._lift0) / 1000 >= LIFTOFF_S)) this._lift0 = -1
    let blink = 1
    if (!still && BLINKS.has(this.state)) {
      if (now >= this._blinkAt) {
        blink = blinkScale((now - this._blinkAt) / 1000)
        if ((now - this._blinkAt) / 1000 > 0.14) this._blinkAt = now + 2500 + Math.random() * 3000
      }
    }
    const d = (a, o) => `M${a[o].toFixed(2)} ${a[o + 1].toFixed(2)}L${a[o + 2].toFixed(2)} ${a[o + 3].toFixed(2)}L${a[o + 4].toFixed(2)} ${a[o + 5].toFixed(2)}`
    e.la.setAttribute('d', d(v, 0)); e.lb.setAttribute('d', d(v, 6)); e.ra.setAttribute('d', d(v, 12)); e.rb.setAttribute('d', d(v, 18))
    const eye = css([v[29], v[30], v[31]])
    for (const [p, sw] of [[e.la, v[24]], [e.lb, v[24]], [e.ra, v[25]], [e.rb, v[25]]]) { p.setAttribute('stroke', eye); p.setAttribute('stroke-width', sw.toFixed(2)) }
    const eyeT = (cx) => `translate(${(cx + m.gx).toFixed(2)} ${(CY + m.gy).toFixed(2)}) scale(1 ${blink.toFixed(3)}) translate(${-cx} ${-CY})`
    e.eyeL.setAttribute('transform', eyeT(LX)); e.eyeR.setAttribute('transform', eyeT(RX))

    const inv = v[26]
    e.sa.setAttribute('stop-color', css(mix([255, 255, 255], [26, 26, 36], inv)))
    e.sb.setAttribute('stop-color', css(mix([205, 205, 224], [10, 10, 16], inv)))
    e.shell.setAttribute('stroke', css(mix([0, 0, 0], [255, 255, 255], inv)))
    e.shell.setAttribute('stroke-opacity', lerp(0.14, 1, inv).toFixed(3))
    e.shell.setAttribute('stroke-width', lerp(1, 3, inv).toFixed(2))
    e.dome.setAttribute('opacity', lerp(0.8, 0.12, inv).toFixed(3))
    e.screen.setAttribute('fill', css(mix([10, 10, 16], [255, 255, 255], inv)))
    e.grid.setAttribute('stroke', css(mix([255, 255, 255], [0, 0, 0], inv)))
    e.tile.setAttribute('fill', css(mix([10, 10, 16], [255, 255, 255], inv)))
    e.dot.setAttribute('fill', css([v[32], v[33], v[34]]))
    e.vent.setAttribute('fill', css(mix([154, 154, 176], [255, 255, 255], inv)))

    e.body.setAttribute('transform', `translate(${m.dx.toFixed(2)} ${m.dy.toFixed(2)}) translate(100 164) rotate(${m.rot.toFixed(2)}) scale(${m.sx.toFixed(4)} ${m.sy.toFixed(4)}) translate(-100 -164)`)
    // the shadow stays on the ground: it shrinks and thins as the body rises
    const up = L ? L.lift : 0
    e.shadow.setAttribute('rx', (58 - (m.dy - (L ? L.dy : 0)) * 0.5 - 14 * up).toFixed(2))
    e.shadow.setAttribute('opacity', (0.28 + (m.dy - (L ? L.dy : 0)) * 0.01 - 0.12 * up).toFixed(3))
    this._drawBoost(L, now)
    // the dot pulses while the mascot is waiting on something
    e.dot.setAttribute('opacity', (this.state === 'checking' || this.state === 'needs-approval') && !still ? (0.65 + 0.35 * Math.sin(t * 6)).toFixed(3) : '1')

    // "z" while asleep, "?" while it waits for the officer
    e.zs.forEach((z, i) => {
      const u = ((t / 3 + i / 3) % 1)
      z.setAttribute('x', (146 + i * 10 + u * 14).toFixed(2))
      z.setAttribute('y', (44 - i * 10 - u * 22).toFixed(2))
      z.setAttribute('opacity', (v[27] * Math.sin(u * Math.PI) * (still ? 0.8 : 1)).toFixed(3))
    })
    e.q.setAttribute('opacity', v[28].toFixed(3))
    e.q.setAttribute('transform', `translate(0 ${(still ? 0 : -3 * Math.sin(t * 3.4)).toFixed(2)})`)
  }
}

if (typeof customElements !== 'undefined' && !customElements.get('sentinel-mascot')) customElements.define('sentinel-mascot', SentinelMascot)
