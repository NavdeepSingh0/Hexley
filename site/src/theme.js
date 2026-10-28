// Dark is the default. The choice is a per-viewer convenience: storage may be blocked, so every access is guarded.
const KEY = 'sentinel.theme'

export function getTheme() {
  try {
    return localStorage.getItem(KEY) === 'light' ? 'light' : 'dark'
  } catch {
    return 'dark'
  }
}

export function setTheme(theme) {
  document.documentElement.dataset.theme = theme
  try {
    localStorage.setItem(KEY, theme)
  } catch { /* the page still works, the choice just is not remembered */ }
}

export function applySavedTheme() {
  // ?theme=light|dark forces a theme for this page load without saving it (for screenshots and reviews).
  const forced = new URLSearchParams(window.location.search).get('theme')
  document.documentElement.dataset.theme = forced === 'light' || forced === 'dark' ? forced : getTheme()
}
