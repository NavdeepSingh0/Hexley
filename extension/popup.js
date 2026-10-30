/**
 * popup.js — Hexley Chrome Extension
 *
 * Shows: connection status, current mascot state, per-site show/hide toggles,
 * links to the console and options page.
 */

'use strict'

// ── DOM refs ─────────────────────────────────────────────────────────────────
const connBadge    = document.getElementById('conn-badge')
const connText     = document.getElementById('conn-text')
const stateLabel   = document.getElementById('state-label')
const stateMsg     = document.getElementById('state-msg')
const toggleClaude = document.getElementById('toggle-claude')
const toggleChatGPT= document.getElementById('toggle-chatgpt')
const openConsole  = document.getElementById('open-console')
const openOptions  = document.getElementById('open-options')

// ── State colours matching the mascot colour contract ─────────────────────────
const STATE_CLASS = {
  sleeping:       'state-sleeping',
  idle:           'state-idle',
  checking:       'state-checking',
  allowed:        'state-allowed',
  denied:         'state-denied',
  'needs-approval': 'state-needs-approval',
  quarantined:    'state-quarantined',
  verified:       'state-verified',
  tamper:         'state-tamper',
}

// ── Connection ────────────────────────────────────────────────────────────────
function setConnection(status, text) {
  connBadge.className = status   // 'connected' | 'disconnected' | 'rejected'
  connText.textContent = text
}

function setMascotState(state, message) {
  const cls = STATE_CLASS[state] || 'state-idle'
  // Remove all state classes
  stateLabel.className = cls
  stateLabel.textContent = state.toUpperCase().replace(/-/g, ' ')
  stateMsg.textContent = message || ''
}

// ── Load settings & fetch state ───────────────────────────────────────────────
async function init() {
  // Load stored address + token
  const session = await chrome.storage.session.get(['sentinelBase', 'token'])
  const local   = await chrome.storage.local.get(['sentinelBase', 'token'])
  const base  = session.sentinelBase || local.sentinelBase || 'http://127.0.0.1:8000'
  const token = session.token        || local.token        || ''

  // Load per-site preferences
  const prefs = await chrome.storage.local.get(['showClaude', 'showChatGPT'])
  toggleClaude.checked  = prefs.showClaude  !== false   // default: true
  toggleChatGPT.checked = prefs.showChatGPT !== false   // default: true

  // Set console link
  openConsole.href = `${base}/console/`
  openConsole.addEventListener('click', (e) => {
    e.preventDefault()
    chrome.tabs.create({ url: `${base}/console/` })
    window.close()
  })

  if (!token) {
    setConnection('disconnected', 'Not configured')
    setMascotState('sleeping', 'Open Settings to connect')
    return
  }

  // Check connection
  try {
    const res = await fetch(`${base}/api/v1/mascot/state`, {
      headers: { 'Authorization': `Bearer ${token}` },
    })

    if (res.status === 401 || res.status === 403) {
      setConnection('rejected', 'Token rejected')
      setMascotState('sleeping', '')
      return
    }
    if (!res.ok) throw new Error(`HTTP ${res.status}`)

    const data = await res.json()
    setConnection('connected', 'Connected')
    setMascotState(data.state || 'sleeping', data.message || '')
  } catch (_) {
    setConnection('disconnected', 'Not connected')
    setMascotState('sleeping', '')
  }
}

// ── Per-site toggles ──────────────────────────────────────────────────────────
toggleClaude.addEventListener('change', () => {
  chrome.storage.local.set({ showClaude: toggleClaude.checked })
})

toggleChatGPT.addEventListener('change', () => {
  chrome.storage.local.set({ showChatGPT: toggleChatGPT.checked })
})

// ── Options link ──────────────────────────────────────────────────────────────
openOptions.addEventListener('click', (e) => {
  e.preventDefault()
  chrome.runtime.openOptionsPage()
  window.close()
})

// ── Init ──────────────────────────────────────────────────────────────────────
init()

