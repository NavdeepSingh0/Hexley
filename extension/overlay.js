/**
 * overlay.js — Sentinel Chrome Extension
 *
 * Runs inside overlay.html (the iframe injected by content.js).
 * Responsibilities:
 * - Load the officer's Sentinel address + token from chrome.storage
 * - Poll GET /api/v1/mascot/state every ~700 ms while visible
 * - Drive the <sentinel-mascot> element (state + message attributes)
 * - Show a "not connected" pill when Sentinel is unreachable
 * - When state is "needs-approval": offer a "Review" button
 * - Handle drag-to-reposition and minimise-to-dot
 * - Forward theme from the parent page
 */

'use strict'

// ── Constants ────────────────────────────────────────────────────────────────
const POLL_MS   = 700          // how often to poll when visible
const CONNECTED_STATES = new Set([
  'sleeping','idle','checking','allowed','denied',
  'needs-approval','quarantined','verified','tamper',
])

// ── State ────────────────────────────────────────────────────────────────────
let sentinelBase = 'http://127.0.0.1:8000'
let token        = ''
let pollTimer    = null
let lastState    = null
let approvalCard = null      // cached approval card when needs-approval

// ── DOM refs (set after DOMContentLoaded) ────────────────────────────────────
let mascot, pill, pillText, reviewBtn, approvalPanel,
    approvalTool, approvalSummary, approvalArgs, approvalTimer,
    approveBtn, denyBtn, wrap

// ── Helpers ─────────────────────────────────────────────────────────────────
function authHeader() {
  return token ? { 'Authorization': `Bearer ${token}` } : {}
}

async function apiFetch(path, options = {}) {
  const url = `${sentinelBase}${path}`
  const res = await fetch(url, {
    ...options,
    headers: { ...authHeader(), ...(options.headers || {}) },
  })
  return res
}

// ── Connection pill ──────────────────────────────────────────────────────────
function showPill(text, ok = false) {
  pill.hidden = false
  pillText.textContent = text
  pill.dataset.ok = ok ? '1' : '0'
}

function hidePill() {
  pill.hidden = true
}

// ── Mascot driver ─────────────────────────────────────────────────────────────
function applyState(state, message) {
  mascot.setAttribute('state', state)
  mascot.setAttribute('message', message || '')
  lastState = state

  // Show review button when holding for officer
  reviewBtn.hidden = state !== 'needs-approval'

  // If we left needs-approval, clear the approval panel
  if (state !== 'needs-approval') {
    approvalPanel.hidden = true
    approvalCard = null
    stopApprovalTimer()
  }
}

// ── Polling ──────────────────────────────────────────────────────────────────
async function poll() {
  if (!token) {
    showPill('Not configured — open options')
    return
  }

  try {
    const res = await apiFetch('/api/v1/mascot/state')
    if (res.status === 401 || res.status === 403) {
      showPill('Token rejected')
      applyState('sleeping', '')
      return
    }
    if (!res.ok) throw new Error(`HTTP ${res.status}`)

    const data = await res.json()
    hidePill()
    applyState(data.state || 'sleeping', data.message || '')
  } catch (_) {
    showPill('Sentinel not connected')
    applyState('sleeping', '')
  }
}

function startPolling() {
  if (pollTimer) return
  poll()
  pollTimer = setInterval(poll, POLL_MS)
}

function stopPolling() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
}

// Pause polling when tab is hidden (saves CPU/battery)
document.addEventListener('visibilitychange', () => {
  document.hidden ? stopPolling() : startPolling()
})

// ── Approval panel ────────────────────────────────────────────────────────────
let timerInterval = null

function stopApprovalTimer() {
  if (timerInterval) { clearInterval(timerInterval); timerInterval = null }
}

function startApprovalTimer(expiresIn) {
  stopApprovalTimer()
  let remaining = expiresIn
  const update = () => {
    remaining--
    approvalTimer.textContent = remaining > 0 ? `${remaining}s left` : 'Expired'
    if (remaining <= 0) stopApprovalTimer()
  }
  update()
  timerInterval = setInterval(update, 1000)
}

function renderApprovalCard(card) {
  approvalCard = card
  approvalTool.textContent = card.tool || '(unknown tool)'
  approvalSummary.textContent = card.summary || ''
  try {
    approvalArgs.textContent = JSON.stringify(card.args || {}, null, 2)
  } catch (_) {
    approvalArgs.textContent = String(card.args)
  }
  startApprovalTimer(card.expires_in || 90)
  approvalPanel.hidden = false
}

async function fetchApprovalCard() {
  try {
    const res = await apiFetch('/approvals')
    if (!res.ok) return
    const data = await res.json()
    // Sentinel's approval cards carry the status in lower case ("pending"); GET /approvals lists only pending ones anyway.
    const pending = (data.pending || []).find(c => c.status === 'pending')
    if (pending) renderApprovalCard(pending)
  } catch (_) { /* no-op */ }
}

async function resolveApproval(decision) {
  if (!approvalCard) return
  const id = approvalCard.approval_id
  approveBtn.disabled = true
  denyBtn.disabled = true

  try {
    const res = await apiFetch(`/approvals/${id}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ decision }),
    })

    if (res.status === 409) {
      approvalPanel.hidden = true
      showPill('Already resolved or expired', false)
      setTimeout(hidePill, 3000)
    } else if (res.ok) {
      approvalPanel.hidden = true
      // Poll will pick up the new state within 700 ms
    } else {
      showPill(`Error ${res.status}`, false)
      setTimeout(hidePill, 3000)
    }
  } catch (_) {
    showPill('Request failed', false)
    setTimeout(hidePill, 3000)
  } finally {
    approveBtn.disabled = false
    denyBtn.disabled = false
    approvalCard = null
    stopApprovalTimer()
  }
}

// ── Minimise / expand ─────────────────────────────────────────────────────────
// (Minimise UI removed — mascot is always visible)

// ── Theme from parent page ─────────────────────────────────────────────────────
window.addEventListener('message', (e) => {
  if (!e.data || e.data.source !== 'sentinel-content') return
  if (e.data.type === 'theme') {
    mascot.setAttribute('theme', e.data.value || 'dark')
    document.documentElement.dataset.theme = e.data.value || 'dark'
  }
})

// ── Init ──────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  // Grab DOM refs
  mascot        = document.getElementById('mascot')
  pill          = document.getElementById('pill')
  pillText      = document.getElementById('pill-text')
  reviewBtn     = document.getElementById('review-btn')
  approvalPanel = document.getElementById('approval-panel')
  approvalTool  = document.getElementById('approval-tool')
  approvalSummary = document.getElementById('approval-summary')
  approvalArgs  = document.getElementById('approval-args')
  approvalTimer = document.getElementById('approval-timer')
  approveBtn    = document.getElementById('approve-btn')
  denyBtn       = document.getElementById('deny-btn')
  wrap          = document.getElementById('wrap')

  // Load settings
  const stored = await chrome.storage.session.get(['sentinelBase', 'token'])
  // Fall back to local storage for "remember" option
  const local  = await chrome.storage.local.get(['sentinelBase', 'token'])
  sentinelBase = stored.sentinelBase || local.sentinelBase || 'http://127.0.0.1:8000'
  token        = stored.token || local.token || ''

  if (!token) {
    showPill('Not configured — open options')
  }

  // Review button
  reviewBtn.addEventListener('click', () => {
    fetchApprovalCard()
    approvalPanel.hidden = false
  })

  // Approve (two-step: confirm first)
  let approveConfirming = false
  approveBtn.addEventListener('click', () => {
    if (!approveConfirming) {
      approveBtn.textContent = 'Confirm?'
      approveConfirming = true
      setTimeout(() => {
        approveBtn.textContent = 'Approve'
        approveConfirming = false
      }, 3000)
    } else {
      approveConfirming = false
      approveBtn.textContent = 'Approve'
      resolveApproval('approve')
    }
  })

  // Deny (one-click)
  denyBtn.addEventListener('click', () => resolveApproval('deny'))

  // Start polling
  if (!document.hidden) startPolling()
})

