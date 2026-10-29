// Routes the mock API. Chat scenarios are chosen with ?mock=<name> in the page URL (default: denied):
// clean | denied | needs-approval | quarantined | model-busy
import { CHAT_PRESETS, CHAT_SCENARIOS, CONNECT, CONNECT_TOKEN, OAUTH_REQUEST } from './data.js'

const delay = (ms = 120) => new Promise((r) => setTimeout(r, ms))
const scenarioName = () => {
  const m = new URLSearchParams(window.location.search).get('mock')
  return m && CHAT_SCENARIOS[m] ? m : 'denied'
}

// Minimal in-memory chat so the page can be exercised end to end on mocks.
let chat = null

export async function mockApi(path, method, body) {
  await delay()
  if (path === '/api/v1/connect') return structuredClone(CONNECT)
  if (path === '/api/v1/connect/token' && method === 'POST') return structuredClone(CONNECT_TOKEN)
  if (path.startsWith('/api/v1/oauth/requests/')) {
    if (method === 'POST') {
      if (body?.decision === 'approve' && body?.officer_code !== '123456') {
        const e = new Error('That officer code is not right.')
        e.status = 403
        throw e
      }
      return { redirect_to: '/?connected=1' }
    }
    return structuredClone(OAUTH_REQUEST)
  }
  if (path === '/api/v1/chat/presets') return structuredClone(CHAT_PRESETS)
  if (path === '/api/v1/chat' && method === 'POST') {
    chat = structuredClone(CHAT_SCENARIOS.awaiting)
    return structuredClone(chat)
  }
  if (/^\/api\/v1\/chat\/[^/]+\/confirm$/.test(path)) {
    chat = { ...structuredClone(CHAT_SCENARIOS.awaiting), status: 'ready', mascot: { state: 'idle', message: '' } }
    return structuredClone(chat)
  }
  if (/^\/api\/v1\/chat\/[^/]+\/messages$/.test(path)) {
    chat = structuredClone(CHAT_SCENARIOS[scenarioName()])
    return { message_id: 'msg_mock' }
  }
  if (/^\/api\/v1\/chat\/[^/]+$/.test(path)) return structuredClone(chat ?? CHAT_SCENARIOS[scenarioName()])
  if (path === '/audit/verify') return { ok: true, checked: 12, head: 'mock', first_bad_seq: null, reason: null, tamper_enabled: false }
  if (/^\/api\/v1\/chat\/[^/]+\/recording$/.test(path)) return { schema: 'sentinel.chat-recording/1', model: 'mock', preset: 'quotation', recorded_at: '2026-10-30T10:00:00Z', messages: [] }
  if (path.startsWith('/approvals/')) return { status: body?.decision === 'approve' ? 'approved' : 'denied' }
  const e = new Error(`No mock for ${method} ${path}. Ask Navdeep before inventing an endpoint.`)
  e.status = 404
  throw e
}
