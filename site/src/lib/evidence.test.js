import { describe, expect, it } from 'vitest'
import { formatInterval, groupEvidence, isComplete } from './evidence.js'

const item = (over = {}) => ({
  group: 'g', group_title: 'G', arm: 'protected', label: 'l', value: '0 of 41', n: 41, ci95: [0, 0.086], source_file: 'eval/results/x.json', caveat: 'c',
  ...over,
})

describe('isComplete', () => {
  it('accepts a full entry', () => expect(isComplete(item())).toBe(true))
  it('rejects an entry with no sample size', () => expect(isComplete(item({ n: undefined }))).toBe(false))
  it('rejects a zero or non-numeric n', () => {
    expect(isComplete(item({ n: 0 }))).toBe(false)
    expect(isComplete(item({ n: '41' }))).toBe(false)
  })
  it('rejects a missing caveat, source or interval', () => {
    expect(isComplete(item({ caveat: '' }))).toBe(false)
    expect(isComplete(item({ source_file: null }))).toBe(false)
    expect(isComplete(item({ ci95: [0] }))).toBe(false)
  })
  it('rejects an unknown arm', () => expect(isComplete(item({ arm: 'other' }))).toBe(false))
  it('rejects junk', () => {
    expect(isComplete(null)).toBe(false)
    expect(isComplete('x')).toBe(false)
  })
})

describe('formatInterval', () => {
  it('writes percentages without trailing zeros', () => {
    expect(formatInterval([0, 0.086])).toBe('0 to 8.6 percent')
    expect(formatInterval([0.914, 1])).toBe('91.4 to 100 percent')
  })
})

describe('groupEvidence', () => {
  it('pairs the two arms of a group', () => {
    const r = groupEvidence([item(), item({ arm: 'unprotected', value: '41 of 41' })])
    expect(r.groups).toHaveLength(1)
    expect(r.groups[0].protectedItem.value).toBe('0 of 41')
    expect(r.groups[0].unprotectedItem.value).toBe('41 of 41')
  })
  it('drops an incomplete entry and reports it', () => {
    const r = groupEvidence([item(), item({ arm: 'unprotected', n: undefined })])
    expect(r.dropped).toHaveLength(1)
    expect(r.groups[0].unprotectedItem).toBeNull()
  })
  it('drops a group that has only the unprotected number', () => {
    const r = groupEvidence([item({ arm: 'unprotected' })])
    expect(r.groups).toHaveLength(0)
  })
  it('tolerates a non-array', () => expect(groupEvidence(null)).toEqual({ groups: [], dropped: [] }))
})
