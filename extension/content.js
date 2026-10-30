/**
 * content.js — Sentinel Chrome Extension
 *
 * Injected into claude.ai and chatgpt.com by the manifest.
 * Does ONE job: injects a fixed-position Shadow DOM host containing an
 * <iframe src="chrome-extension://.../overlay.html"> at the bottom-left
 * of the page.
 *
 * The iframe handles all mascot rendering and API communication.
 * This script never touches the token, never reads page content.
 */

(function () {
  'use strict'

  const EXT_ID = chrome.runtime.id
  const OVERLAY_URL = `chrome-extension://${EXT_ID}/overlay.html`
  const HOST_ID = 'sentinel-ext-host'

  // Don't inject twice (e.g. on SPA navigation events)
  if (document.getElementById(HOST_ID)) return

  // Create an isolated Shadow DOM host so page styles can't affect us
  const host = document.createElement('div')
  host.id = HOST_ID
  host.style.cssText = [
    'position: fixed',
    'bottom: 20px',
    'left: 20px',
    'z-index: 2147483647', // max z-index
    'width: 0',
    'height: 0',
    'overflow: visible',
    'pointer-events: none',
    'border: none',
    'background: none',
    'padding: 0',
    'margin: 0',
  ].join(';')

  const shadow = host.attachShadow({ mode: 'closed' })

  // The iframe — mascot, bubble and all API calls live here
  const iframe = document.createElement('iframe')
  iframe.src = OVERLAY_URL
  iframe.style.cssText = [
    'position: absolute',
    'bottom: 0',
    'left: 0',
    'width: 220px',
    'height: 220px',
    'border: none',
    'background: transparent',
    'pointer-events: auto',
    'overflow: hidden',
  ].join(';')
  iframe.setAttribute('scrolling', 'no')
  iframe.setAttribute('frameborder', '0')
  iframe.setAttribute('allowtransparency', 'true')
  iframe.setAttribute('title', 'Sentinel status')
  iframe.setAttribute('aria-label', 'Sentinel status')
  // Sandbox: allow-scripts + allow-storage-access-by-user-activation
  // We do NOT allow-same-origin on purpose so the iframe has its own origin
  // (chrome-extension://) and can't access page storage.
  // chrome.storage is accessed via the background service worker instead.
  // Note: we actually want same-origin for chrome.storage — extension pages
  // ARE same-origin with each other, so we can use chrome.storage directly.
  // No sandbox attribute needed.

  shadow.appendChild(iframe)
  document.documentElement.appendChild(host)

  // Listen for messages from the overlay (e.g. resize requests)
  window.addEventListener('message', (e) => {
    if (!e.data || typeof e.data !== 'object') return
    if (e.data.source !== 'sentinel-overlay') return

    if (e.data.type === 'resize') {
      const { width, height } = e.data
      iframe.style.width = `${width}px`
      iframe.style.height = `${height}px`
    }

    if (e.data.type === 'minimise') {
      iframe.style.width = '48px'
      iframe.style.height = '48px'
    }

    if (e.data.type === 'expand') {
      iframe.style.width = '220px'
      iframe.style.height = '220px'
    }
  })

  // Tell the overlay the current page theme so the bubble matches
  function sendTheme() {
    const isDark = !document.documentElement.classList.contains('light') &&
      (document.documentElement.dataset.theme !== 'light') &&
      window.matchMedia('(prefers-color-scheme: dark)').matches
    iframe.contentWindow?.postMessage(
      { source: 'sentinel-content', type: 'theme', value: isDark ? 'dark' : 'light' },
      `chrome-extension://${EXT_ID}`
    )
  }

  iframe.addEventListener('load', () => {
    sendTheme()
  })

  // Watch for theme changes on the page
  const themeObserver = new MutationObserver(sendTheme)
  themeObserver.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ['class', 'data-theme'],
  })
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', sendTheme)
})()
