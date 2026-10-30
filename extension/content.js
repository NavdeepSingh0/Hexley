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
  // Watch where the main content starts (its left edge = sidebar width).
  // Claude.ai: <main> shifts right when the sidebar opens.
  // ChatGPT.com: same pattern.
  // transition on host.style.left gives the smooth slide effect.
  const BASE_LEFT = 20 // px from left edge when sidebar is fully closed

  function getSidebarWidth() {
    // Strategy 1: main element's left edge IS the sidebar width
    const main = document.querySelector('main') ||
                 document.querySelector('[role="main"]') ||
                 document.querySelector('[data-testid="conversation-turn-0"]')?.closest('div[class]')
    if (main) {
      const left = Math.round(main.getBoundingClientRect().left)
      if (left > 10) return left  // sidebar is open (main shifted right)
    }

    // Strategy 2: look for a fixed/sticky left nav whose right edge > 40px
    const navCandidates = [
      ...document.querySelectorAll('nav, aside, [role="navigation"]'),
    ]
    for (const el of navCandidates) {
      const r = el.getBoundingClientRect()
      // Must be: near left edge, tall (> half viewport), not tiny
      if (r.left < 10 && r.width > 40 && r.height > window.innerHeight * 0.4) {
        return Math.round(r.width)
      }
    }
    return 0
  }

  function updateHostLeft() {
    const sidebarW = getSidebarWidth()
    host.style.left = `${BASE_LEFT + sidebarW}px`
  }

  // Run immediately and on every layout change
  updateHostLeft()

  // ResizeObserver on <main> — fires when its size/position changes
  const sidebarObserver = new ResizeObserver(updateHostLeft)

  function observeMain() {
    const main = document.querySelector('main') || document.querySelector('[role="main"]')
    if (main) sidebarObserver.observe(main)
  }
  observeMain()

  // MutationObserver: catch SPA renders where <main> appears late
  const domObserver = new MutationObserver(() => {
    updateHostLeft()
    observeMain()
  })
  domObserver.observe(document.documentElement, { childList: true, subtree: true })

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
