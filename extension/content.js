/**
 * content.js — Sentinel Chrome Extension
 *
 * Injected into claude.ai and chatgpt.com by the manifest.
 * Does ONE job: injects a fixed-position Shadow DOM host containing an
 * <iframe src="chrome-extension://.../overlay.html"> at the bottom-left
 * of the page.
 *
 * The iframe handles all mascot rendering and API communication.
 * This script never touches the token and never reads page content: the only
 * things it looks at are where the page's sidebar ends (a layout measurement)
 * and the popup's show/hide switch for this site.
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
  const SITE_KEY = location.hostname === 'chatgpt.com' ? 'showChatGPT' : 'showClaude' // the popup's switch for this site
  const BASE_LEFT = 20 // px from left edge when sidebar is fully closed
  const SIZE_MIN = 48 // bounds for what the overlay may ask its frame to become
  const SIZE_MAX_W = 420
  const SIZE_MAX_H = 640

  let running = null // { stop() } while the overlay is on the page

  function clampSize(value, max) {
    const n = Number(value)
    if (!Number.isFinite(n)) return null
    return Math.min(max, Math.max(SIZE_MIN, Math.round(n)))
  }

  function start() {
    if (running || document.getElementById(HOST_ID)) return // never inject twice (SPA navigation, repeated switch changes)

    // ── Host element — fixed bottom-left, zero-size, overflow visible ────────
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

    // ── iframe — transparent, no borders, pointer-events on ─────────────────
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

    // ── Sidebar slide ────────────────────────────────────────────────────────
    // Watch where the main content starts (its left edge = sidebar width).
    // transition on host.style.left gives the smooth slide effect.
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
      host.style.left = `${BASE_LEFT + getSidebarWidth()}px`
    }

    // A chat page changes its DOM constantly while a reply streams, and measuring layout on every change would slow it. The
    // measurement runs at most once per animation frame, however many changes arrived.
    let frame = 0
    function schedule() {
      if (frame) return
      frame = requestAnimationFrame(() => { frame = 0; updateHostLeft() })
    }

    updateHostLeft()

    // ResizeObserver on <main> — fires when its size/position changes
    const sidebarObserver = new ResizeObserver(schedule)

    function observeMain() {
      const main = document.querySelector('main') || document.querySelector('[role="main"]')
      if (main) sidebarObserver.observe(main) // observing the same element again does nothing
    }
    observeMain()

    // MutationObserver: catch SPA renders where <main> appears late
    const domObserver = new MutationObserver(() => {
      schedule()
      observeMain()
    })
    domObserver.observe(document.documentElement, { childList: true, subtree: true })

    window.addEventListener('resize', schedule, { passive: true })

    // ── Messages from the overlay ────────────────────────────────────────────
    // Only the overlay frame itself may ask for a size, and only within bounds: a script on the page can post any message it
    // likes, but it is not that frame.
    function onMessage(e) {
      if (e.source !== iframe.contentWindow) return
      const d = e.data
      if (!d || typeof d !== 'object' || d.source !== 'sentinel-overlay') return
      if (d.type === 'resize') {
        const width = clampSize(d.width, SIZE_MAX_W)
        const height = clampSize(d.height, SIZE_MAX_H)
        if (width === null || height === null) return
        iframe.style.width = `${width}px`
        iframe.style.height = `${height}px`
      }
    }
    window.addEventListener('message', onMessage)

    // ── Theme detection ──────────────────────────────────────────────────────
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
    const colourScheme = window.matchMedia('(prefers-color-scheme: dark)')
    colourScheme.addEventListener('change', sendTheme)

    running = {
      stop() {
        if (frame) cancelAnimationFrame(frame)
        sidebarObserver.disconnect()
        domObserver.disconnect()
        themeObserver.disconnect()
        window.removeEventListener('resize', schedule)
        window.removeEventListener('message', onMessage)
        colourScheme.removeEventListener('change', sendTheme)
        host.remove()
      },
    }
  }

  function stop() {
    if (!running) return
    running.stop()
    running = null
  }

  // The popup's switch for this site: off means the overlay is not on the page at all, and it follows the switch live.
  chrome.storage.local.get([SITE_KEY], (prefs) => {
    if (prefs[SITE_KEY] !== false) start()
  })
  chrome.storage.onChanged.addListener((changes, area) => {
    if (area !== 'local' || !changes[SITE_KEY]) return
    if (changes[SITE_KEY].newValue === false) stop()
    else start()
  })
})()
