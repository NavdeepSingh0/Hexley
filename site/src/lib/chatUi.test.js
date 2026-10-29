import { describe, expect, it } from 'vitest'
import { ago, chatTitle, statusChip, toolSummary } from './chat.js'
import { loadChats, removeChat, saveChat } from './chatHistory.js'

const a = (decision) => ({ action_id: Math.random().toString(36), decision })

describe('toolSummary', () => {
  it('counts the tools and names how many were denied, in the gateway\'s words', () => {
    const s = toolSummary([a('ALLOWED'), a('ALLOWED'), a('DENIED')])
    expect(s.label).toBe('Used 3 tools')
    expect(s.parts).toEqual([{ kind: 'denied', text: '1 denied' }])
  })
  it('says one tool in the singular and nothing extra when everything was allowed', () => {
    expect(toolSummary([a('ALLOWED')])).toEqual({ n: 1, label: 'Used 1 tool', parts: [] })
  })
  it('lists several kinds, each once, in a fixed order', () => {
    const s = toolSummary([a('PENDING'), a('NEEDS_APPROVAL'), a('DENIED'), a('DENIED'), a('QUARANTINED')])
    expect(s.parts.map((p) => p.kind)).toEqual(['denied', 'approval', 'quarantined', 'pending'])
    expect(s.parts[0].text).toBe('2 denied')
  })
  it('copes with no actions', () => {
    expect(toolSummary(undefined).n).toBe(0)
  })
})

describe('statusChip', () => {
  it('is empty without a chat', () => expect(statusChip(null)).toBeNull())
  it('names each state in plain words', () => {
    expect(statusChip({ status: 'awaiting_confirmation' }).text).toBe('Waiting for the officer')
    expect(statusChip({ status: 'thinking' }).text).toBe('Working')
    expect(statusChip({ status: 'model_busy' }).text).toMatch(/trying again/)
    expect(statusChip({ status: 'ended' }).text).toBe('Slip expired')
  })
  it('only a quarantine is loud', () => {
    expect(statusChip({ status: 'quarantined' })).toEqual({ kind: 'quarantined', text: 'Quarantined' })
    for (const s of ['awaiting_confirmation', 'thinking', 'ready']) expect(statusChip({ status: s, slip: {} }).kind).not.toBe('quarantined')
  })
  it('a confirmed slip shows when it ends, if the time is readable', () => {
    expect(statusChip({ status: 'ready', slip: { expires_at: '2026-10-30T10:15:00Z' } }).text).toMatch(/^Slip confirmed until \d/)
    expect(statusChip({ status: 'ready', slip: { expires_at: 'soon' } }).text).toBe('Slip confirmed')
  })
})

describe('titles and times', () => {
  it('uses the task title, then the preset id, then a default', () => {
    expect(chatTitle({ title: 'Process a vendor quotation' }, null)).toBe('Process a vendor quotation')
    expect(chatTitle(undefined, { preset: 'own-pdf' })).toBe('own-pdf')
    expect(chatTitle(undefined, null)).toBe('New chat')
  })
  it('says how long ago', () => {
    const now = 1_000_000_000
    expect(ago(now - 10_000, now)).toBe('just now')
    expect(ago(now - 5 * 60_000, now)).toBe('5 min ago')
    expect(ago(now - 3 * 3_600_000, now)).toBe('3 h ago')
    expect(ago(now - 2 * 86_400_000, now)).toBe('2 d ago')
  })
})

const memory = () => { const m = {}; return { getItem: (k) => (k in m ? m[k] : null), setItem: (k, v) => { m[k] = v } } }

describe('chat history', () => {
  it('remembers chats newest first and updates one in place', () => {
    const s = memory()
    saveChat({ id: 'chat_1', title: 'One', ts: 1 }, s)
    saveChat({ id: 'chat_2', title: 'Two', ts: 2 }, s)
    saveChat({ id: 'chat_1', title: 'One again', status: 'quarantined' }, s)
    const list = loadChats(s)
    expect(list.map((c) => c.id)).toEqual(['chat_1', 'chat_2'])
    expect(list[0]).toMatchObject({ title: 'One again', status: 'quarantined', ts: 1 })
  })
  it('removes a chat', () => {
    const s = memory()
    saveChat({ id: 'a', title: 'A' }, s)
    saveChat({ id: 'b', title: 'B' }, s)
    expect(removeChat('a', s).map((c) => c.id)).toEqual(['b'])
  })
  it('keeps at most thirty', () => {
    const s = memory()
    for (let i = 0; i < 40; i += 1) saveChat({ id: `c${i}`, title: `T${i}` }, s)
    expect(loadChats(s)).toHaveLength(30)
    expect(loadChats(s)[0].id).toBe('c39')
  })
  it('survives blocked storage and bad data', () => {
    expect(loadChats(null)).toEqual([])
    expect(loadChats({ getItem: () => { throw new Error('blocked') } })).toEqual([])
    expect(loadChats({ getItem: () => '{not json' })).toEqual([])
    expect(loadChats({ getItem: () => '[1, {"id": 2}, {"id": "x", "title": "ok"}]' })).toEqual([{ id: 'x', title: 'ok' }])
    expect(() => saveChat({ id: 'a', title: 'A' }, { getItem: () => null, setItem: () => { throw new Error('full') } })).not.toThrow()
  })
})
