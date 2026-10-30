// The console talks only to the Hexley API that served it (same origin). The API token arrives once, in the URL
// fragment printed/opened by `python -m sentinel up`; it moves to sessionStorage and is removed from the address bar.
const KEY = 'sentinel.token'
let token = null

export function initAuth() {
  const h = new URLSearchParams(window.location.hash.slice(1))
  const fromUrl = h.get('token')
  try {
    if (fromUrl) sessionStorage.setItem(KEY, fromUrl)
    token = fromUrl || sessionStorage.getItem(KEY)
  } catch {
    token = fromUrl
  }
  const run = h.get('run')
  if (fromUrl || run) window.history.replaceState(null, '', window.location.pathname + window.location.search)
  return { run, verdict: h.get('verdict') === '1', hasToken: Boolean(token) }
}

export class ApiError extends Error {
  constructor(status, detail) {
    super(detail)
    this.status = status
  }
}

export async function api(path, { method = 'GET', body } = {}) {
  let r
  try {
    r = await fetch(path, {
      method,
      headers: { Authorization: `Bearer ${token ?? ''}`, ...(body ? { 'Content-Type': 'application/json' } : {}) },
      body: body ? JSON.stringify(body) : undefined,
    })
  } catch {
    throw new ApiError(0, 'Cannot reach the Hexley API')
  }
  if (!r.ok) {
    let detail = r.statusText
    try {
      const j = await r.json()
      detail = typeof j.detail === 'string' ? j.detail : JSON.stringify(j.detail)
    } catch { /* keep statusText */ }
    if (r.status === 401) detail = "The access token is missing or wrong. Re-open the officer's link."
    throw new ApiError(r.status, detail)
  }
  return r.json()
}

export const getScenarios = () => api('/scenarios').then((j) => j.scenarios)
export const getRecordings = () => api('/recordings').then((j) => j.recordings)
export const createRun = (scenario, source, recording_id) =>
  api('/runs', { method: 'POST', body: { scenario, source, ...(recording_id ? { recording_id } : {}) } })
export const confirmRun = (id) => api(`/runs/${id}/confirm`, { method: 'POST' })
export const cancelRun = (id) => api(`/runs/${id}/cancel`, { method: 'POST' })
export const getRun = (id) => api(`/runs/${id}`)
export const listRuns = () => api('/runs')
export const decideApproval = (id, decision) => api(`/approvals/${id}`, { method: 'POST', body: { decision } })
export const pendingApprovals = () => api('/approvals').then((j) => j.pending)
export const verifyAudit = () => api('/audit/verify')
export const tamperAudit = () => api('/audit/tamper', { method: 'POST' })
export const restoreAudit = () => api('/audit/restore', { method: 'POST' })
