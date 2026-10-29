import { describe, expect, it } from 'vitest'
import { STATES, MAX_MESSAGE } from '../../../design/mascot/sentinel-mascot.js'
import { SAY, SCENARIOS, STATE_INFO, allTransitions, dwell, trace } from './mascotLab.js'

describe('what the lab says about each state', () => {
  it('covers exactly the nine states, each with a trigger, a hold and a motion description', () => {
    expect(Object.keys(STATE_INFO).sort()).toEqual([...STATES].sort())
    for (const s of STATES) expect(Object.values(STATE_INFO[s]).every((t) => typeof t === 'string' && t.length >= 3), s).toBe(true)
  })
  it('speech is the product\'s own words and short enough for the bubble', () => {
    for (const s of STATES) expect(SAY[s].length).toBeLessThanOrEqual(MAX_MESSAGE)
    expect(SAY.denied).toBe('That would send restricted data out.')
    expect(SAY['needs-approval']).toBe("This needs the officer's approval.")
  })
})

describe('motion traces come from the real motion function', () => {
  it('idle moves a few pixels at most and sleeping barely moves', () => {
    expect(trace('idle').steady.dy).toBeGreaterThan(1)
    expect(trace('idle').steady.dy).toBeLessThanOrEqual(3.01)
    expect(trace('sleeping').peak.dy).toBe(0)
  })
  it('a decision reacts hard at first and then calms down', () => {
    const d = trace('denied')
    expect(d.peak.dx).toBeGreaterThan(d.steady.dx * 5)
    const a = trace('allowed')
    expect(a.peak.scale).toBeGreaterThan(a.steady.scale)
  })
  it('checking scans wider than idle, and tamper jitters', () => {
    expect(trace('checking').steady.gaze).toBeGreaterThan(trace('idle').steady.gaze)
    expect(trace('tamper').steady.dx).toBeGreaterThan(0.5)
  })
  it('samples cover the whole window at a fixed step', () => {
    const t = trace('idle', 2, 0.1)
    expect(t.samples[0].t).toBe(0)
    expect(t.samples.at(-1).t).toBeCloseTo(2, 5)
    expect(t.samples).toHaveLength(21)
  })
})

describe('transitions and sequences', () => {
  it('there are 72 changes of state, none from a state to itself', () => {
    const all = allTransitions()
    expect(all).toHaveLength(72)
    expect(all.every((t) => t.from !== t.to)).toBe(true)
    expect(new Set(all.map((t) => `${t.from}>${t.to}`)).size).toBe(72)
  })
  it('every scripted sequence uses real states, positive holds and short speech', () => {
    expect(SCENARIOS.length).toBeGreaterThanOrEqual(4)
    for (const sc of SCENARIOS) {
      expect(sc.steps.length).toBeGreaterThan(0)
      for (const s of sc.steps) {
        expect(STATES).toContain(s.state)
        expect(s.ms).toBeGreaterThan(0)
        expect(s.message.length).toBeLessThanOrEqual(MAX_MESSAGE)
      }
    }
  })
  it('the sequences follow the event table: a denied or allowed state follows a check, quarantine follows a denial', () => {
    for (const sc of SCENARIOS) {
      sc.steps.forEach((s, i) => {
        if (['allowed', 'denied', 'quarantined'].includes(s.state)) expect(sc.steps[i - 1]?.state, `${sc.id} step ${i}`).toBe('checking')
      })
    }
  })
  it('slower playback holds longer, and never forever', () => {
    expect(dwell(1000, 1)).toBe(1000)
    expect(dwell(1000, 0.5)).toBe(2000)
    expect(dwell(1000, 0)).toBe(4000)
    expect(dwell(1000, 2)).toBe(500)
  })
})
