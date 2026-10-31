// Hexley's pixel mascot for the extension. The same element name and attributes as the website's mascot, so overlay.html and overlay.js
// need no other change: state, message, size, placement, theme, still. The art is whole cells on a 40-cell grid (design/brand/make_brand.py),
// so a size that is a multiple of 40 stays crisp. Colour is meaning, as everywhere: the tile takes the decision's colour.
import { FILL_D, GRID, LINE_D } from './mascot-art.js'

const STATES = ['sleeping', 'idle', 'checking', 'allowed', 'denied', 'needs-approval', 'quarantined', 'verified', 'tamper']
const PERSISTENT = new Set(['quarantined', 'needs-approval']) // the bubble stays up while the state lasts
const BUBBLE_MS = 6000
const MAX_MESSAGE = 90

const TILE = {
  sleeping: '#7d6fb3', idle: '#a98bff', checking: '#a98bff', allowed: '#34e8a3', denied: '#5b9bff', 'needs-approval': '#ffb62e',
  quarantined: '#ffffff', verified: '#34e8a3', tamper: '#ff5468',
}

const EYES = [[13, 11, 3, 9], [24, 11, 3, 9]]
const MOUTH = [[15, 23, 10, 2]]
const SMILE = [[14, 22, 2, 2], [16, 24, 8, 2], [24, 22, 2, 2]]
const FROWN = [[14, 25, 2, 2], [16, 23, 8, 2], [24, 25, 2, 2]]
const cross = (x, y) => [0, 1, 2, 3, 4, 5, 6].flatMap((i) => [[x + i, y + i, 2, 1], [x + 6 - i, y + i, 2, 1]])

const FACES = {
  idle: [...EYES, ...MOUTH],
  sleeping: [[12, 16, 5, 2], [23, 16, 5, 2], [17, 24, 6, 2]],
  checking: [...EYES, [17, 23, 6, 2]],
  allowed: [...EYES, ...SMILE],
  denied: [[11, 10, 5, 2], [24, 10, 5, 2], [13, 13, 3, 6], [24, 13, 3, 6], ...FROWN],
  'needs-approval': [[13, 11, 3, 9], [24, 14, 3, 6], [16, 24, 3, 2], [19, 23, 3, 2], [22, 24, 3, 2]],
  quarantined: [...cross(11, 12), ...cross(22, 12), ...MOUTH],
  verified: [[12, 16, 2, 2], [14, 14, 2, 2], [16, 16, 2, 2], [23, 16, 2, 2], [25, 14, 2, 2], [27, 16, 2, 2], ...SMILE],
  tamper: [[12, 10, 5, 10], [23, 10, 5, 10], [16, 22, 8, 5]],
}
const BLINK = [[13, 15, 3, 1], [24, 15, 3, 1]]

const BUBBLE_THEME = { dark: { bg: '#212130', fg: '#FFFFFF', line: '#2A2A36' }, light: { bg: '#FFFFFF', fg: '#0A0A10', line: '#D9D6EA' } }
const cells = (list, dx = 0) => list.map(([x, y, w, h]) => `M${x + dx} ${y}h${w}v${h}h${-w}z`).join('')
const stateOf = (s) => (STATES.includes(s) ? s : 'idle')
const shorten = (m) => { const t = String(m || '').trim(); return t.length > MAX_MESSAGE ? `${t.slice(0, MAX_MESSAGE - 1)}…` : t }

const TEMPLATE = `
<style>
  :host { display: inline-block; position: relative; z-index: 12; flex: none; box-sizing: border-box; width: var(--size, 80px); height: var(--size, 80px); line-height: 0; }
  svg { width: 100%; height: 100%; display: block; overflow: visible; }
  .bubble { position: absolute; width: max-content; max-width: 280px; padding: 10px 14px; border-radius: 14px; font: 14px/1.35 "Helvetica Neue", Helvetica, Arial, sans-serif;
    border: 1px solid var(--line); background: var(--bg); color: var(--fg); box-shadow: 0 8px 28px rgba(0,0,0,.35); opacity: 0; transform: scale(.94);
    transform-origin: var(--origin, right center); transition: opacity .2s ease, transform .2s ease; pointer-events: none; text-align: left; }
  .bubble.show { opacity: 1; transform: none; }
  .bubble::after { content: ""; position: absolute; width: 10px; height: 10px; background: var(--bg); border: 1px solid var(--line); transform: rotate(45deg); }
  :host([placement="left"]) .bubble, :host(:not([placement])) .bubble { right: calc(100% + 10px); top: 50%; translate: 0 -50%; }
  :host([placement="left"]) .bubble::after, :host(:not([placement])) .bubble::after { right: -6px; top: calc(50% - 5px); border-left: none; border-bottom: none; }
  :host([placement="below"]) .bubble { top: calc(100% + 8px); right: 0; --origin: top right; }
  :host([placement="below"]) .bubble::after { top: -6px; right: 22px; border-right: none; border-bottom: none; }
  :host([placement="above"]) .bubble { bottom: calc(100% + 8px); left: 0; --origin: bottom left; }
  :host([placement="above"]) .bubble::after { bottom: -6px; left: 22px; border-left: none; border-top: none; }
</style>
<svg viewBox="0 0 ${GRID} ${GRID}" shape-rendering="crispEdges" role="img" aria-label="Hexley mascot">
  <path class="tile" d="${FILL_D}"/>
  <path fill="#07070a" d="${LINE_D}"/>
  <path class="face" fill="#07070a"/>
</svg>
<div class="bubble" role="status" aria-live="polite"></div>`

const Base = typeof HTMLElement === 'undefined' ? class {} : HTMLElement

export class PixelMascot extends Base {
  static get observedAttributes() { return ['state', 'message', 'size', 'theme', 'placement', 'still'] }

  get state() { return stateOf(this.getAttribute('state')) }
  set state(v) { this.setAttribute('state', v) }

  connectedCallback() {
    if (!this.shadowRoot) {
      const root = this.attachShadow({ mode: 'open' })
      root.innerHTML = TEMPLATE
      this._svg = root.querySelector('svg')
      this._tile = root.querySelector('.tile')
      this._face = root.querySelector('.face')
      this._bubble = root.querySelector('.bubble')
    }
    this._applySize()
    this._draw()
    this._say(this.getAttribute('message'))
    this._animate()
  }

  disconnectedCallback() {
    clearTimeout(this._timer)
    clearTimeout(this._bubbleTimer)
  }

  attributeChangedCallback(name, before, value) {
    if (!this._svg || before === value) return
    if (name === 'state') {
      this._draw()
      this._say(this.getAttribute('message')) // a persistent state keeps its words up; leaving one starts the clock
      this._animate()
    } else if (name === 'message') this._say(value)
    else if (name === 'still') this._animate()
    else if (name === 'size' || name === 'theme') this._applySize()
  }

  _applySize() {
    const n = parseFloat(this.getAttribute('size'))
    this.style.setProperty('--size', `${Number.isFinite(n) && n > 0 ? n : 80}px`)
    const explicit = this.getAttribute('theme')
    const page = document.documentElement.dataset.theme === 'light' ? 'light' : 'dark'
    const t = BUBBLE_THEME[explicit === 'light' || explicit === 'dark' ? explicit : page]
    for (const [k, v] of Object.entries(t)) this._bubble.style.setProperty(`--${k}`, v)
  }

  _draw(face) {
    const state = this.state
    this._tile.setAttribute('fill', TILE[state])
    this._face.setAttribute('d', face ?? cells(FACES[state]))
    this._svg.setAttribute('aria-label', `Hexley mascot: ${state}`)
  }

  _say(raw) {
    const text = shorten(raw)
    clearTimeout(this._bubbleTimer)
    if (!text) { this._bubble.classList.remove('show'); return }
    this._bubble.textContent = text
    this._bubble.classList.add('show')
    if (!PERSISTENT.has(this.state)) this._bubbleTimer = setTimeout(() => this._bubble.classList.remove('show'), BUBBLE_MS)
  }

  // Small and stepped, as pixels move: a blink at rest, a look from side to side while checking. None under reduced motion or `still`.
  _animate() {
    clearTimeout(this._timer)
    const still = this.hasAttribute('still') || (typeof matchMedia === 'function' && matchMedia('(prefers-reduced-motion: reduce)').matches)
    if (still) { this._draw(); return }
    const state = this.state
    if (state === 'checking') {
      let side = 2
      const look = () => {
        this._draw(cells([...EYES.map(([x, y, w, h]) => [x + side, y, w, h])]) + cells([[17, 23, 6, 2]]))
        side = -side
        this._timer = setTimeout(look, 420)
      }
      look()
    } else if (state === 'idle' || state === 'needs-approval') {
      const blink = () => {
        this._timer = setTimeout(() => {
          this._draw(cells([...BLINK, ...FACES[state].slice(2)]))
          this._timer = setTimeout(() => { this._draw(); blink() }, 130)
        }, 2600 + Math.random() * 3000)
      }
      blink()
    }
  }
}

if (typeof customElements !== 'undefined' && !customElements.get('sentinel-mascot')) customElements.define('sentinel-mascot', PixelMascot)
