// Whether the home page plays its one-off launch (the mascot's boosters): the first time the home page loads in this browser.
// The flag lives in localStorage (a per-viewer convenience, so it is wrapped in try/catch). When storage is blocked the launch
// plays once per page load instead, and a visit that stays inside the app never plays it twice.
export const LAUNCH_KEY = 'sentinel.launched'

let playedThisLoad = false

function browserStorage() {
  try { return window.localStorage } catch { return null }
}

// True exactly once for a browser that has never launched; remembers that it did.
export function claimLaunch(storage = browserStorage()) {
  if (playedThisLoad) return false
  playedThisLoad = true
  try {
    if (storage && storage.getItem(LAUNCH_KEY)) return false
    storage?.setItem(LAUNCH_KEY, '1')
  } catch { /* blocked or full: play it, once per page load */ }
  return true
}

// For tests only: behave as if the page had just been loaded.
export function forgetThisLoad() { playedThisLoad = false }
