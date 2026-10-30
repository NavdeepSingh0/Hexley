/**
 * options.js — Hexley Chrome Extension
 *
 * Handles: parsing the full Hexley link, saving address + token to
 * chrome.storage.session (and optionally chrome.storage.local),
 * and the "Test connection" flow.
 *
 * The token NEVER appears in a URL, log line, or page variable.
 */

'use strict'

// ── DOM refs ─────────────────────────────────────────────────────────────────
const fullLinkInput = document.getElementById('full-link')
const baseUrlInput  = document.getElementById('base-url')
const tokenInput    = document.getElementById('token-input')
const rememberCheck = document.getElementById('remember')
const saveBtn       = document.getElementById('save-btn')
const clearBtn      = document.getElementById('clear-btn')
const statusEl      = document.getElementById('status')

// ── Helpers ──────────────────────────────────────────────────────────────────
function showStatus(text, kind = 'info') {
  statusEl.textContent = text
  statusEl.className = kind
  statusEl.style.display = 'block'
}

function hideStatus() {
  statusEl.style.display = 'none'
}

/** Hexley's officer API runs on this computer. The token can approve actions, so it is only ever sent to this computer: not to a
 *  tunnel (which reaches the AI gateway, not the officer API) and not to an address pasted by mistake. */
function isLocalAddress(base) {
  try {
    const u = new URL(base)
    return u.protocol === 'http:' && (u.hostname === '127.0.0.1' || u.hostname === 'localhost')
  } catch (_) {
    return false
  }
}

/** Parse address + token out of a full Hexley link.
 *  Accepts: http://127.0.0.1:8000/#token=abc123
 *  Returns: { base, token } or null if unparseable.
 */
function parseFullLink(raw) {
  const str = (raw || '').trim()
  if (!str) return null
  try {
    const url = new URL(str)
    // Token is in the fragment after "#token="
    const frag = url.hash // "#token=abc123"
    const match = frag.match(/^#token=(.+)$/)
    if (!match) return null
    const token = match[1].trim()
    if (!token) return null
    // Base is everything except the fragment
    url.hash = ''
    return { base: url.toString().replace(/\/$/, ''), token }
  } catch (_) {
    return null
  }
}

// ── Load saved settings on open ───────────────────────────────────────────────
async function loadSaved() {
  const session = await chrome.storage.session.get(['sentinelBase', 'token'])
  const local   = await chrome.storage.local.get(['sentinelBase', 'token', 'remember'])

  const base  = session.sentinelBase || local.sentinelBase || ''
  const token = session.token        || local.token        || ''
  const remember = local.remember    || false

  if (base)    baseUrlInput.value  = base
  if (token)   tokenInput.value    = '•'.repeat(20) // mask; show placeholder
  if (remember) rememberCheck.checked = true

  if (base && token) {
    showStatus('Settings loaded. Click "Save & test" to verify.', 'info')
  }
}

// ── Auto-fill from full link ─────────────────────────────────────────────────
fullLinkInput.addEventListener('input', () => {
  const parsed = parseFullLink(fullLinkInput.value)
  if (parsed) {
    baseUrlInput.value = parsed.base
    tokenInput.value   = parsed.token
    hideStatus()
  }
})

// ── Save & Test ──────────────────────────────────────────────────────────────
saveBtn.addEventListener('click', async () => {
  hideStatus()

  // Parse full link if provided and not yet parsed
  const parsed = parseFullLink(fullLinkInput.value)
  if (parsed) {
    baseUrlInput.value = parsed.base
    tokenInput.value   = parsed.token
  }

  const base  = (baseUrlInput.value || '').trim().replace(/\/$/, '')
  const token = (tokenInput.value   || '').trim()

  if (!isLocalAddress(base)) {
    showStatus('Use the address of Hexley on this computer, like http://127.0.0.1:8000. A tunnel address reaches the AI gateway, not the officer API, and the token is never sent to another machine.', 'error')
    return
  }

  // Reject masked placeholder (user hasn't re-entered real token)
  const isPlaceholder = /^•+$/.test(token)

  if (!base) {
    showStatus('Please enter the server address.', 'error')
    return
  }
  if (!token || isPlaceholder) {
    showStatus('Please enter the officer token.', 'error')
    return
  }

  saveBtn.disabled = true
  showStatus('Testing connection…', 'info')

  try {
    // Step 1: /health (no auth needed)
    const healthRes = await fetch(`${base}/health`)
    if (!healthRes.ok) throw new Error(`/health returned ${healthRes.status}`)

    // Step 2: /api/v1/mascot/state (requires auth)
    const stateRes = await fetch(`${base}/api/v1/mascot/state`, {
      headers: { 'Authorization': `Bearer ${token}` },
    })

    if (stateRes.status === 401 || stateRes.status === 403) {
      showStatus('Token rejected — check the token and try again.', 'error')
      return
    }
    if (!stateRes.ok) throw new Error(`/api/v1/mascot/state returned ${stateRes.status}`)

    const data = await stateRes.json()
    const stateWord = data.state || 'unknown'

    // Save to session storage
    await chrome.storage.session.set({ sentinelBase: base, token })

    if (rememberCheck.checked) {
      // Save to local storage (persists across browser restarts)
      await chrome.storage.local.set({ sentinelBase: base, token, remember: true })
    } else {
      // Clear any previously stored local creds
      await chrome.storage.local.remove(['sentinelBase', 'token', 'remember'])
      await chrome.storage.local.set({ remember: false })
    }

    showStatus(`Connected — mascot state: ${stateWord}`, 'ok')
  } catch (err) {
    if (err instanceof TypeError && err.message.includes('Failed to fetch')) {
      showStatus('Hexley not running — start it with: python -m sentinel up --demo', 'error')
    } else {
      showStatus(`Connection failed: ${err.message}`, 'error')
    }
  } finally {
    saveBtn.disabled = false
  }
})

// ── Clear ─────────────────────────────────────────────────────────────────────
clearBtn.addEventListener('click', async () => {
  fullLinkInput.value = ''
  baseUrlInput.value  = ''
  tokenInput.value    = ''
  rememberCheck.checked = false
  await chrome.storage.session.remove(['sentinelBase', 'token'])
  await chrome.storage.local.remove(['sentinelBase', 'token', 'remember'])
  showStatus('Cleared.', 'info')
})

// ── Init ──────────────────────────────────────────────────────────────────────
loadSaved()

