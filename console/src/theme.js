// Dark is the default (the deck's look). The choice is a per-viewer convenience: storage may be blocked, so every access is
// guarded. The key is the same one the website uses, so choosing a theme on one page carries over to the other.
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

// `#theme=light` (or dark) in the address overrides the saved choice for this page load only and is never saved: it is for
// screenshots and for a projector room where the presenter wants the other theme without touching the saved setting.
// Read when this module is first loaded: App.jsx removes the address fragment (it holds the API token) as soon as it is
// evaluated, which is before main.jsx's own code runs, so reading the fragment later would find it already gone.
const FROM_URL = new URLSearchParams(window.location.hash.slice(1)).get('theme')

export function applySavedTheme() {
  document.documentElement.dataset.theme = FROM_URL === 'light' || FROM_URL === 'dark' ? FROM_URL : getTheme()
}
