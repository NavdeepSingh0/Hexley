import { beforeEach, describe, expect, it } from 'vitest'
import { LAUNCH_KEY, claimLaunch, forgetThisLoad } from './firstVisit.js'

const memory = (start = {}) => {
  const data = { ...start }
  return { data, getItem: (k) => (k in data ? data[k] : null), setItem: (k, v) => { data[k] = String(v) } }
}

beforeEach(() => forgetThisLoad())

describe('the home page launch fires once', () => {
  it('plays for a browser that has never launched, and remembers it', () => {
    const s = memory()
    expect(claimLaunch(s)).toBe(true)
    expect(s.data).toEqual({ [LAUNCH_KEY]: '1' })
  })
  it('does not play again in the same page load, however often the home page is shown', () => {
    const s = memory()
    expect(claimLaunch(s)).toBe(true)
    for (let i = 0; i < 5; i++) expect(claimLaunch(s)).toBe(false)
  })
  it('does not play on a later page load once it has been played', () => {
    const s = memory()
    claimLaunch(s)
    forgetThisLoad() // a reload
    expect(claimLaunch(s)).toBe(false)
  })
  it('writes nothing but its own flag', () => {
    const s = memory({ other: 'x' })
    claimLaunch(s)
    expect(Object.keys(s.data).sort()).toEqual([LAUNCH_KEY, 'other'].sort())
  })
})

describe('when storage cannot be used', () => {
  const broken = { getItem() { throw new Error('blocked') }, setItem() { throw new Error('blocked') } }
  it('plays once per page load, and never throws', () => {
    expect(claimLaunch(broken)).toBe(true)
    expect(claimLaunch(broken)).toBe(false)
    forgetThisLoad()
    expect(claimLaunch(broken)).toBe(true) // a new page load: it cannot remember, so it plays again
  })
  it('plays when there is no storage at all', () => {
    expect(claimLaunch(null)).toBe(true)
    expect(claimLaunch(null)).toBe(false)
  })
  it('plays when only writing fails (a full or read-only store)', () => {
    const s = { getItem: () => null, setItem() { throw new Error('quota') } }
    expect(claimLaunch(s)).toBe(true)
  })
})
