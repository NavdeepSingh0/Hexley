// The conversations started in this browser, for the sidebar. A per-viewer convenience only: the server keeps the real chats
// (in memory), this list just remembers their ids and titles so they can be reopened with ?chat=<id>. Storage may be blocked,
// so every access is guarded and the page works without it.
const KEY = 'sentinel.chats'
const MAX = 30

function defaultStore() {
  try { return window.localStorage } catch { return null }
}

export function loadChats(store = defaultStore()) {
  try {
    const list = JSON.parse(store?.getItem(KEY) ?? '[]')
    return Array.isArray(list) ? list.filter((c) => c && typeof c.id === 'string' && typeof c.title === 'string') : []
  } catch {
    return []
  }
}

function write(list, store) {
  try { store?.setItem(KEY, JSON.stringify(list.slice(0, MAX))) } catch { /* the sidebar just forgets */ }
  return list.slice(0, MAX)
}

// Add or update one chat (newest first). `entry`: { id, title, preset, ts, status }.
export function saveChat(entry, store = defaultStore()) {
  const rest = loadChats(store).filter((c) => c.id !== entry.id)
  const old = loadChats(store).find((c) => c.id === entry.id)
  return write([{ ...old, ...entry, ts: old?.ts ?? entry.ts ?? Date.now() }, ...rest], store)
}

export function removeChat(id, store = defaultStore()) {
  return write(loadChats(store).filter((c) => c.id !== id), store)
}
