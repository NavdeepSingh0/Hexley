// The mascot's pure logic (design/mascot/sentinel-mascot.js): states, poses, easing, motion, speech timing. The element itself is
// checked in a real browser (the F1 QA script), because it needs a DOM, shadow roots and animation frames.
import { describe, expect, it } from 'vitest'
import {
  BUBBLE_MS, MAX_MESSAGE, POSES, STATES, VECTOR_LENGTH, blinkScale, bubbleVisible, easeToward, motionAt, normalizeState, parseSpeed, poseVector,
  truncateMessage,
} from '../../../design/mascot/sentinel-mascot.js'

describe('states', () => {
  it('are exactly the nine in the contract, each with a pose', () => {
    expect(STATES).toEqual(['sleeping', 'idle', 'checking', 'allowed', 'denied', 'needs-approval', 'quarantined', 'verified', 'tamper'])
    expect(Object.keys(POSES).sort()).toEqual([...STATES].sort())
  })
  it('an unknown or missing state falls back to idle', () => {
    for (const bad of [undefined, null, '', 'nope', 'ALLOWED', 'idle ']) expect(normalizeState(bad)).toBe('idle')
    expect(poseVector('nope')).toEqual(poseVector('idle'))
  })
  it('every pose is a full vector of finite numbers', () => {
    for (const s of STATES) {
      const v = poseVector(s)
      expect(v).toHaveLength(VECTOR_LENGTH)
      expect(v.every(Number.isFinite), s).toBe(true)
    }
  })
  it('only quarantined inverts the body; only sleeping shows the z; only needs-approval shows the question mark', () => {
    for (const s of STATES) {
      const v = poseVector(s)
      expect(v[26], `${s} inversion`).toBe(s === 'quarantined' ? 1 : 0)
      expect(v[27], `${s} z`).toBe(s === 'sleeping' ? 1 : 0)
      expect(v[28], `${s} ?`).toBe(s === 'needs-approval' ? 1 : 0)
    }
  })
  it('no state paints red on the body: red is only an eye colour in the tamper state', () => {
    for (const s of STATES) {
      const v = poseVector(s)
      const eye = v.slice(29, 32)
      const red = eye[0] === 255 && eye[1] === 84 && eye[2] === 104
      expect(red, s).toBe(s === 'tamper')
    }
  })
  it('the cross of the tamper state is the only pose whose B stroke is not on its A stroke', () => {
    for (const s of STATES) {
      const v = poseVector(s)
      const same = v.slice(0, 6).every((x, i) => x === v[6 + i]) && v.slice(12, 18).every((x, i) => x === v[18 + i])
      expect(same, s).toBe(s !== 'tamper')
    }
  })
})

describe('speech', () => {
  it('is cut to 90 characters with an ellipsis, whitespace tidied', () => {
    const long = 'x'.repeat(200)
    expect(truncateMessage(long)).toHaveLength(MAX_MESSAGE)
    expect(truncateMessage(long).endsWith('…')).toBe(true)
    expect(truncateMessage('  hello \n  there ')).toBe('hello there')
    expect(truncateMessage(null)).toBe('')
    expect(truncateMessage('a'.repeat(90))).toBe('a'.repeat(90))
  })
  it('hides after 6 s, except while quarantined or waiting for the officer', () => {
    expect(bubbleVisible('denied', 'No.', BUBBLE_MS - 1)).toBe(true)
    expect(bubbleVisible('denied', 'No.', BUBBLE_MS + 1)).toBe(false)
    expect(bubbleVisible('allowed', 'Ok.', BUBBLE_MS + 1)).toBe(false)
    expect(bubbleVisible('quarantined', 'Frozen.', 10 * 60 * 1000)).toBe(true)
    expect(bubbleVisible('needs-approval', 'Officer.', 10 * 60 * 1000)).toBe(true)
    expect(bubbleVisible('quarantined', '', 0)).toBe(false) // nothing to say, nothing shown
  })
})

describe('easing', () => {
  it('moves toward the target without overshooting, and does so at any frame rate', () => {
    const a = [0, 10]
    const b = [10, 0]
    let x = a
    for (let i = 0; i < 20; i++) {
      const next = easeToward(x, b, 1 / 60)
      expect(next[0]).toBeGreaterThan(x[0]); expect(next[0]).toBeLessThanOrEqual(10)
      x = next
    }
    // 60 steps of 1/60 s land where 1 step of 1 s does (frame-rate independence)
    let fine = a
    for (let i = 0; i < 60; i++) fine = easeToward(fine, b, 1 / 60)
    const coarse = easeToward(a, b, 1)
    expect(fine[0]).toBeCloseTo(coarse[0], 6)
  })
  it('almost arrives within half a second', () => {
    let v = poseVector('idle')
    const target = poseVector('denied')
    for (let i = 0; i < 30; i++) v = easeToward(v, target, 1 / 60)
    const worst = Math.max(...v.map((x, i) => Math.abs(x - target[i])))
    expect(worst).toBeLessThan(255 * 0.02)
  })
  it('passes through in-between shapes, so a change of state is a morph and not a cut', () => {
    const from = poseVector('idle')
    const to = poseVector('denied')
    const mid = easeToward(from, to, 0.08)
    const moved = mid.map((x, i) => (x - from[i]) / (to[i] - from[i] || 1)).filter((r, i) => to[i] !== from[i])
    expect(moved.length).toBeGreaterThan(5)
    expect(moved.every((r) => r > 0 && r < 1)).toBe(true)
  })
})

describe('motion', () => {
  it('is deterministic: the same time gives the same pose', () => {
    for (const s of STATES) expect(motionAt(s, 3.3, 1.1)).toEqual(motionAt(s, 3.3, 1.1))
  })
  it('stays small: nothing ever leaves the cube or turns it over', () => {
    for (const s of STATES) {
      for (let t = 0; t < 12; t += 0.07) {
        const m = motionAt(s, t, t)
        expect(Math.abs(m.dx), s).toBeLessThan(10); expect(Math.abs(m.dy), s).toBeLessThan(14)
        expect(Math.abs(m.rot), s).toBeLessThan(4); expect(m.sx).toBeGreaterThan(0.85); expect(m.sx).toBeLessThan(1.15)
        expect(m.sy).toBeGreaterThan(0.85); expect(m.sy).toBeLessThan(1.15)
        expect(Math.abs(m.gx), s).toBeLessThanOrEqual(9.01)
      }
    }
  })
  it('a decision lands with a reaction that dies away: pop, shake, squash', () => {
    const early = motionAt('allowed', 5, 0.1)
    const late = motionAt('allowed', 5, 3)
    expect(Math.abs(early.sy - 1)).toBeGreaterThan(Math.abs(late.sy - 1))
    expect(Math.abs(motionAt('denied', 5, 0.03).dx)).toBeGreaterThan(Math.abs(motionAt('denied', 5, 3).dx))
    expect(motionAt('quarantined', 5, 0.05).sy).toBeLessThan(motionAt('quarantined', 5, 3).sy)
  })
  it('checking scans left and right; sleeping only breathes', () => {
    const xs = [0, 0.3, 0.6, 0.9, 1.2, 1.5].map((t) => motionAt('checking', t, t).gx)
    expect(Math.max(...xs)).toBeGreaterThan(5); expect(Math.min(...xs)).toBeLessThan(-5)
    const s = motionAt('sleeping', 1.1, 1.1)
    expect([s.dx, s.dy, s.gx, s.rot]).toEqual([0, 0, 0, 0])
  })
  it('a blink closes the eyes briefly and opens them again', () => {
    expect(blinkScale(-1)).toBe(1); expect(blinkScale(0.5)).toBe(1)
    expect(blinkScale(0.07)).toBeCloseTo(0.1, 5)
    expect(blinkScale(0.03)).toBeLessThan(1)
  })
})

describe('the speed review attribute', () => {
  it('is a time scale: 0 freezes, 0.25 is slow motion, anything unusable is 1', () => {
    expect(parseSpeed('0')).toBe(0)
    expect(parseSpeed('0.25')).toBe(0.25)
    expect(parseSpeed('2')).toBe(2)
    for (const bad of [null, undefined, '', 'fast', NaN]) expect(parseSpeed(bad)).toBe(1)
  })
  it('is held between 0 and 4, so a typo cannot make it run backwards or race', () => {
    expect(parseSpeed('-3')).toBe(0)
    expect(parseSpeed('100')).toBe(4)
  })
})
