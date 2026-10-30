/**
 * background.js — Sentinel Chrome Extension Service Worker
 *
 * Kept deliberately minimal. MV3 service workers sleep between events,
 * so ALL polling happens inside overlay.html, not here.
 *
 * Responsibilities:
 * - Open the options page on first install so the officer can paste their token
 * - Handle optional host permission requests (for tunnel addresses)
 */

'use strict'

// On first install: open options so the officer can set up their token
chrome.runtime.onInstalled.addListener((details) => {
  if (details.reason === 'install') {
    chrome.runtime.openOptionsPage()
  }
})

// Listen for messages from popup or overlay that need service-worker capabilities
chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (!msg || typeof msg !== 'object') return

  // Request optional host permission for a custom tunnel address
  if (msg.type === 'request-host-permission') {
    const origin = msg.origin // e.g. "https://abc123.trycloudflare.com"
    if (!origin || typeof origin !== 'string') {
      sendResponse({ ok: false, error: 'Missing origin' })
      return true
    }
    chrome.permissions.request(
      { origins: [`${origin}/*`] },
      (granted) => sendResponse({ ok: granted })
    )
    return true // keep message channel open for async response
  }
})

