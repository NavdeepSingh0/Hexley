import { describe, expect, it } from 'vitest'
import { countdown, fillSnippet, groupByStatus, methodOf } from './connect.js'

const c = (id, status) => ({ id, status })

describe('groupByStatus', () => {
  it('orders Tested, Should work, Planned and drops empty groups', () => {
    const g = groupByStatus([c('a', 'planned'), c('b', 'tested'), c('c', 'planned')])
    expect(g.map((x) => x.status)).toEqual(['tested', 'planned'])
    expect(g[1].clients.map((x) => x.id)).toEqual(['a', 'c'])
  })
  it('tolerates a non-array', () => expect(groupByStatus(null)).toEqual([]))
  it('never invents a status: an unknown one is not shown', () => expect(groupByStatus([c('a', 'verified')])).toEqual([]))
})

describe('fillSnippet', () => {
  const snippet = 'claude mcp add sentinel {mcp_url} --header "Authorization: {header_value}"'
  it('fills both placeholders', () => {
    expect(fillSnippet(snippet, { mcp_url: 'http://x/mcp', header_value: 'Bearer T' })).toBe('claude mcp add sentinel http://x/mcp --header "Authorization: Bearer T"')
  })
  it('leaves a placeholder visible when there is no value yet', () => {
    expect(fillSnippet(snippet, { mcp_url: 'http://x/mcp' })).toContain('{header_value}')
  })
  it('returns null for no snippet', () => expect(fillSnippet(null, {})).toBeNull())
})

describe('countdown', () => {
  const now = Date.parse('2026-10-30T10:00:00Z')
  it('shows minutes and seconds', () => expect(countdown('2026-10-30T10:14:05Z', now)).toBe('14 min 05 s left'))
  it('shows seconds under a minute', () => expect(countdown('2026-10-30T10:00:30Z', now)).toBe('30 s left'))
  it('says expired at or after the time', () => {
    expect(countdown('2026-10-30T10:00:00Z', now)).toBe('expired')
    expect(countdown('2026-10-30T09:00:00Z', now)).toBe('expired')
  })
  it('gives nothing for a bad date', () => expect(countdown('soon', now)).toBe(''))
})

describe('methodOf', () => {
  it('finds a method or returns null', () => {
    expect(methodOf({ methods: [{ id: 'oauth' }] }, 'oauth')).toEqual({ id: 'oauth' })
    expect(methodOf({ methods: [] }, 'header')).toBeNull()
    expect(methodOf(null, 'header')).toBeNull()
  })
})
