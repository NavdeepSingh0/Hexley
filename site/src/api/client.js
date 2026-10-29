// The ONLY place the site talks to the backend. Pages never call fetch directly (docs/contracts/API.md).
//
// Mocks: with VITE_USE_MOCKS=1 (the default in development) the same shapes come from src/mocks/, so pages can be built
// before the backend exists. VITE_USE_MOCKS=0 calls the real API. Production builds default to the real API.
//
// Auth is the console's: the API token arrives once in the URL fragment (#token=...), moves to sessionStorage and is
// removed from the address bar. The key is shared with /console/, so signing in once covers both. Never log the token.
import { mockApi } from '../mocks/handlers.js'

const KEY = 'sentinel.token'
const USE_MOCKS = (import.meta.env.VITE_USE_MOCKS ?? (import.meta.env.DEV ? '1' : '0')) === '1'
let token = null

export const usingMocks = () => USE_MOCKS

export function initAuth() {
  const h = new URLSearchParams(window.location.hash.slice(1))
  const fromUrl = h.get('token')
  try {
    if (fromUrl) sessionStorage.setItem(KEY, fromUrl)
    token = fromUrl || sessionStorage.getItem(KEY)
  } catch {
    token = fromUrl
  }
  if (fromUrl) window.history.replaceState(null, '', window.location.pathname + window.location.search)
  return { hasToken: Boolean(token) }
}

export class ApiError extends Error {
  constructor(status, detail) {
    super(detail)
    this.status = status
  }
}

export async function api(path, { method = 'GET', body } = {}) {
  if (USE_MOCKS) return mockApi(path, method, body)
  let r
  try {
    r = await fetch(path, {
      method,
      headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}), ...(body ? { 'Content-Type': 'application/json' } : {}) },
      body: body ? JSON.stringify(body) : undefined,
    })
  } catch {
    throw new ApiError(0, 'Cannot reach Sentinel. Is `python -m sentinel up --demo` running?')
  }
  if (!r.ok) {
    let detail = r.statusText
    try {
      const j = await r.json()
      detail = typeof j.detail === 'string' ? j.detail : JSON.stringify(j.detail)
    } catch { /* keep statusText */ }
    if (r.status === 401) detail = 'The access token is missing or wrong. Re-open the link printed by `python -m sentinel up`.'
    throw new ApiError(r.status, detail)
  }
  return r.json()
}

// ---- the endpoints the site uses (docs/contracts/API.md) ---------------------------------------------------------
export const getConnect = () => api('/api/v1/connect') // public: no token needed
export const hasToken = () => Boolean(token)
export const createConnectToken = (preset) => api('/api/v1/connect/token', { method: 'POST', body: { preset } })
export const getOAuthRequest = (id) => api(`/api/v1/oauth/requests/${id}`)
export const decideOAuthRequest = (id, decision, officer_code) =>
  api(`/api/v1/oauth/requests/${id}`, { method: 'POST', body: { decision, officer_code } })
export const getChatPresets = () => api('/api/v1/chat/presets')
export const createChat = (preset, mode = 'auto') => api('/api/v1/chat', { method: 'POST', body: { preset, mode } })
export const confirmChat = (id) => api(`/api/v1/chat/${id}/confirm`, { method: 'POST' })
export const sendChatMessage = (id, text) => api(`/api/v1/chat/${id}/messages`, { method: 'POST', body: { text } })
export const getChat = (id) => api(`/api/v1/chat/${id}`)
export const decideApproval = (id, decision) => api(`/approvals/${id}`, { method: 'POST', body: { decision } })
export const getChatRecording = (id) => api(`/api/v1/chat/${id}/recording`)
export const verifyAudit = () => api('/audit/verify')

// evidence.json is a static file generated from eval/results/ (never typed by hand).
export async function getEvidence() {
  const r = await fetch('/evidence.json')
  if (!r.ok) throw new ApiError(r.status, 'evidence.json is missing')
  return r.json()
}
