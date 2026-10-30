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
 *
 * Sidebar slide: watches the left sidebar width on claude.ai / chatgpt.com
 * and smoothly shifts the host's left position so the mascot slides out of
 * the way when the sidebar opens, and back when it closes.
 */

(function () {
  'use strict'

  const EXT_ID = chrome.runtime.id
  const OVERLAY_URL = `chrome-extension://${EXT_ID}/overlay.html`
  const HOST_ID = 'sentinel-ext-host'

  // Don't inject twice (e.g. on SPA navigation events)
  if (document.getElementById(HOST_ID)) return

  // ── Host element — fixed bottom-left, zero-size, overflow visible ──────────
  const host = document.createElement('div')
  host.id = HOST_ID
  host.style.cssText = [
    'position:fixed',
    'bottom:20px',
    'left:20px',          // default; updated by sidebar watcher
    'z-index:2147483647',
    'width:0',
    'height:0',
    'overflow:visible',
    'pointer-events:none',
    'border:none',
    'background:none',
    'padding:0',
    'margin:0',
    'transition:left 0.28s cubic-bezier(0.4,0,0.2,1)', // smooth slide
  ].join(';')

  const shadow = host.attachShadow({ mode: 'closed' })

  // ── iframe — transparent, no borders, pointer-events on ───────────────────
  const iframe = document.createElement('iframe')
  iframe.src = OVERLAY_URL
  iframe.style.cssText = [
    'position:absolute',
    'bottom:0',
    'left:0',
    'width:260px',
    'height:260px',
    'border:0',
    'background:transparent',   // key: transparent bg
    'pointer-events:auto',
    'overflow:visible',
    'color-scheme:normal',      // don't inherit forced light scheme
  ].join(';')
  iframe.setAttribute('scrolling', 'no')
  iframe.setAttribute('frameborder', '0')
  iframe.setAttribute('allowtransparency', 'true')
  iframe.setAttribute('title', 'Sentinel status')
  iframe.setAttribute('aria-label', 'Sentinel status')

  shadow.appendChild(iframe)
  document.documentElement.appendChild(host)

  // ── Sidebar slide ──────────────────────────────────────────────────────────
  // We watch the left sidebar element (if any) and mirror its width into
  // the host's `left` so the mascot slides right when the sidebar opens.
  //
  // Claude.ai:    nav sidebar is a <nav> or <aside> that grows from 0 → ~260px
  // ChatGPT.com:  sidebar is a <nav> on the left; its width changes similarly
  //
  // Strategy: find the element whose right-edge is closest to the left viewport
  // edge (i.e. the leftmost sidebar), read its offsetWidth, and set host.left.
  const BASE_LEFT = 20 // px from left edge when sidebar is closed

  function getSidebarWidth() {
    // Claude.ai sidebar selector — covers both old and new layouts
    const selectors = [
      '[data-testid="sidebar"]',
      'nav[class*="sidebar"]',
      'aside[class*="sidebar"]',
      '[class*="Sidebar"]',
      'nav[class*="Sidebar"]',
      // ChatGPT.com
      'nav[aria-label="Chat history"]',
      '#sidebar',
      '[data-sidebar]',
    ]
    for (const sel of selectors) {
      try {
        const el = document.querySelector(sel)
        if (el) {
          const w = el.getBoundingClientRect().width
          if (w > 40) return Math.round(w) // ignore tiny/collapsed states
        }
      } catch (_) { /* skip */ }
    }
    return 0
  }

  function updateHostLeft() {
    const sidebarW = getSidebarWidth()
    const newLeft = BASE_LEFT + sidebarW
    host.style.left = `${newLeft}px`
  }

  // Run once now, then watch for DOM mutations that resize the sidebar
  updateHostLeft()

  const sidebarObserver = new ResizeObserver(updateHostLeft)

  function attachSidebarObserver() {
    const selectors = [
      '[data-testid="sidebar"]', 'nav[class*="sidebar"]', 'aside[class*="sidebar"]',
      '[class*="Sidebar"]', 'nav[aria-label="Chat history"]', '#sidebar',
    ]
    for (const sel of selectors) {
      try {
        const el = document.querySelector(sel)
        if (el) { sidebarObserver.observe(el); return }
      } catch (_) { /* skip */ }
    }
  }

  // Try immediately; if the sidebar isn't in the DOM yet, wait for it
  attachSidebarObserver()

  // MutationObserver to catch deferred sidebar renders (SPA pages)
  const domObserver = new MutationObserver(() => {
    updateHostLeft()
    attachSidebarObserver()
  })
  domObserver.observe(document.body || document.documentElement, {
    childList: true, subtree: false,
  })

  // Also re-check on window resize (layout shift can change sidebar width)
  window.addEventListener('resize', updateHostLeft, { passive: true })

  // ── Messages from the overlay ──────────────────────────────────────────────
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
      iframe.style.width = '260px'
      iframe.style.height = '260px'
    }
  })

  // ── Theme detection ────────────────────────────────────────────────────────
  function sendTheme() {
    const isDark = !document.documentElement.classList.contains('light') &&
      (document.documentElement.dataset.theme !== 'light') &&
      window.matchMedia('(prefers-color-scheme: dark)').matches
    iframe.contentWindow?.postMessage(
      { source: 'sentinel-content', type: 'theme', value: isDark ? 'dark' : 'light' },
      `chrome-extension://${EXT_ID}`
    )
  }

  iframe.addEventListener('load', sendTheme)

  const themeObserver = new MutationObserver(sendTheme)
  themeObserver.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ['class', 'data-theme'],
  })
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', sendTheme)
})()
