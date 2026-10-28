// Pure helpers for the Integrations and Connect pages. The client list, statuses and snippets come from the gateway
// (GET /api/v1/connect); nothing about a client's status is decided here.
import { useEffect, useState } from 'react'
import { getConnect } from '../api/client.js'

export const STATUS_ORDER = ['tested', 'should_work', 'planned']
export const STATUS_LABEL = { tested: 'Tested', should_work: 'Should work', planned: 'Planned' }
export const STATUS_MEANING = {
  tested: 'We connected a real session and have the screenshot.',
  should_work: 'It speaks the same standard (MCP) but we have not run it yet.',
  planned: 'Designed for, not built.',
}
export const KIND_LABEL = { web: 'Web app', ide: 'Code editor', cli: 'Command line', local: 'Local model', other: 'Other agents' }
export const METHOD_LABEL = { oauth: 'Sign in (OAuth)', header: 'Access token (header)', none: 'No way to connect yet' }

// Clients grouped by status, in the fixed order Tested, Should work, Planned; empty groups are left out.
export function groupByStatus(clients) {
  const list = Array.isArray(clients) ? clients : []
  return STATUS_ORDER.map((status) => ({ status, clients: list.filter((c) => c.status === status) })).filter((g) => g.clients.length > 0)
}

// Fill {mcp_url} and {header_value} in a snippet. A placeholder with no value is left as written, so a missing token is
// visible in the text instead of silently producing a broken command.
export function fillSnippet(snippet, values) {
  if (!snippet) return null
  return snippet.replace(/\{(mcp_url|header_value)\}/g, (whole, key) => (values[key] ? values[key] : whole))
}

// "14 min 05 s left", or "expired".
export function countdown(expiresAt, now = Date.now()) {
  const t = Date.parse(expiresAt)
  if (!Number.isFinite(t)) return ''
  const s = Math.floor((t - now) / 1000)
  if (s <= 0) return 'expired'
  const m = Math.floor(s / 60)
  return m > 0 ? `${m} min ${String(s % 60).padStart(2, '0')} s left` : `${s} s left`
}

export function methodOf(connect, id) {
  return connect?.methods?.find((m) => m.id === id) ?? null
}

// One request per page load, shared by every component that asks (the home strip, Integrations and Connect).
let pending = null
export function loadConnect({ fresh = false } = {}) {
  if (!pending || fresh) pending = getConnect()
  pending.catch(() => { pending = null }) // a failure is not remembered: the next visit asks again
  return pending
}

export function useConnect() {
  const [state, setState] = useState({ status: 'loading', data: null, error: '' })
  useEffect(() => {
    let live = true
    loadConnect()
      .then((data) => { if (live) setState({ status: 'ready', data, error: '' }) })
      .catch((e) => { if (live) setState({ status: 'error', data: null, error: e.message }) })
    return () => { live = false }
  }, [])
  return state
}
