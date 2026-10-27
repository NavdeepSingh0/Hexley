// PLACEHOLDER (B0). Phase A6b replaces this with the real pixel-sentry widget.
// It only fixes the interface (docs/contracts/MASCOT.md) so pages and the extension can already use <sentinel-mascot>.
// Attributes: state, message, size (64|128), theme (dark|light), speak. No network requests.
const STATES = ['sleeping', 'idle', 'checking', 'allowed', 'denied', 'needs-approval', 'quarantined', 'verified', 'tamper']

class SentinelMascot extends HTMLElement {
  static get observedAttributes() { return ['state', 'message', 'size', 'theme', 'speak'] }
  connectedCallback() { this.attachShadow({ mode: 'open' }); this.render() }
  attributeChangedCallback() { if (this.shadowRoot) this.render() }
  render() {
    const state = STATES.includes(this.getAttribute('state')) ? this.getAttribute('state') : 'idle'
    const size = Number(this.getAttribute('size')) === 128 ? 128 : 64
    const message = (this.getAttribute('message') || '').slice(0, 90)
    const dark = this.getAttribute('theme') !== 'light'
    this.shadowRoot.innerHTML = `
      <style>
        :host { display: inline-flex; align-items: flex-end; gap: 8px; font-family: Helvetica, Arial, sans-serif; }
        .box { width: ${size}px; height: ${size}px; border: 2px dashed ${dark ? '#a3a29d' : '#5c5b57'}; display: grid; place-items: center;
               font-size: 10px; text-transform: uppercase; letter-spacing: .1em; color: ${dark ? '#a3a29d' : '#5c5b57'}; text-align: center; }
        .bubble { max-width: 260px; padding: 6px 10px; border: 1px solid ${dark ? '#3b3b39' : '#d6d4cd'}; font-size: 14px;
                  color: ${dark ? '#f2f1ed' : '#161616'}; background: ${dark ? '#262625' : '#fff'}; }
        .bubble:empty { display: none; }
      </style>
      <div class="box" role="img" aria-label="Sentinel mascot: ${state}">${state}</div>
      <div class="bubble">${message.replace(/[<>&]/g, '')}</div>`
  }
}
if (!customElements.get('sentinel-mascot')) customElements.define('sentinel-mascot', SentinelMascot)
