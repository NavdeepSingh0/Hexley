// The stage's one-word-one-sentence lanes (F2), checked against views captured from real runs (spikes/capture_fixtures.py).
import { describe, expect, it } from 'vitest'
import poisoned from '../fixtures/poisoned.json'
import clean from '../fixtures/clean.json'
import redirect from '../fixtures/redirect.json'
import freeze from '../fixtures/freeze.json'
import hardened from '../fixtures/hardened.json'
import bankWaiting from '../fixtures/bank_change_waiting.json'
import bankDone from '../fixtures/bank_change_done.json'
import compromisedPdf from '../fixtures/compromised_pdf.json'
import poisonedWeb from '../fixtures/poisoned_web.json'
import stranger from '../fixtures/stranger.json'
import { approvalView, isParaphraseGap, laneCaption, laneCountLine, laneLabel, laneVerdict } from './derive.js'

const lane = (view, column, i) => view.lanes.filter((l) => l.column === column)[i ?? 0]
const ALL = [poisoned, clean, redirect, freeze, hardened, bankWaiting, bankDone, compromisedPdf, poisonedWeb, stranger]

describe('stage lanes: one verdict word and one plain sentence', () => {
  it('poisoned: LEAKED in both baselines, DENIED in Sentinel', () => {
    expect(laneVerdict(lane(poisoned, 'unprotected'), 'poisoned')).toEqual({ kind: 'harm', word: 'LEAKED', sentence: 'Restricted data reached the outside.' })
    expect(laneVerdict(lane(poisoned, 'r1_only'), 'poisoned').word).toBe('LEAKED')
    expect(laneVerdict(lane(poisoned, 'sentinel'), 'poisoned')).toEqual({ kind: 'denied', word: 'DENIED', sentence: 'Nothing left the building.' })
  })
  it('clean: the baselines say SENT (neutral), Sentinel says ALLOWED: a baseline never says allowed', () => {
    expect(laneVerdict(lane(clean, 'unprotected'), 'clean').word).toBe('SENT')
    expect(laneVerdict(lane(clean, 'r1_only'), 'clean').kind).toBe('neutral')
    expect(laneVerdict(lane(clean, 'sentinel'), 'clean')).toMatchObject({ kind: 'allowed', word: 'ALLOWED' })
  })
  it('redirect: MISDIRECTED in the baselines, DENIED in Sentinel', () => {
    expect(laneVerdict(lane(redirect, 'unprotected'), 'redirect').word).toBe('MISDIRECTED')
    expect(laneVerdict(lane(redirect, 'sentinel'), 'redirect').word).toBe('DENIED')
  })
  it('freeze: QUARANTINED, and the sentence says how many attempts', () => {
    expect(laneVerdict(lane(freeze, 'sentinel'), 'freeze')).toMatchObject({
      kind: 'quarantined', word: 'QUARANTINED', sentence: 'The agent was frozen after 3 denied attempts.',
    })
  })
  it('hardened: the value-matching lane says plainly that a paraphrase got through; the hardened lane is quarantined', () => {
    expect(isParaphraseGap(hardened.lanes[0], 'hardened')).toBe(true)
    expect(isParaphraseGap(hardened.lanes[1], 'hardened')).toBe(false)
    expect(isParaphraseGap(lane(clean, 'sentinel'), 'clean')).toBe(false)
    expect(laneVerdict(hardened.lanes[0], 'hardened').sentence).toMatch(/declared limit/)
    expect(laneVerdict(hardened.lanes[1], 'hardened').word).toBe('QUARANTINED')
    expect(laneLabel(hardened.lanes[0], 'hardened')).toBe('Sentinel · value matching')
    expect(laneLabel(hardened.lanes[1], 'hardened')).toBe('Sentinel · hardened mode')
  })
  it('bank change: NEEDS APPROVAL while waiting; ALLOWED only after approval; CHANGED in red when nobody was asked', () => {
    expect(laneVerdict(lane(bankWaiting, 'sentinel'), 'bank_change')).toMatchObject({ kind: 'approval', word: 'NEEDS APPROVAL' })
    expect(laneVerdict(lane(bankDone, 'sentinel'), 'bank_change')).toMatchObject({ kind: 'allowed', word: 'ALLOWED' })
    expect(laneVerdict(lane(bankDone, 'unprotected'), 'bank_change')).toMatchObject({ kind: 'harm', word: 'CHANGED' })
    expect(laneVerdict(lane(bankDone, 'unprotected'), 'bank_change').sentence).toMatch(/111-222-333 and nobody was asked/)
  })
  it('running and failed lanes are shown as such, never as a result', () => {
    expect(laneVerdict({ ...lane(poisoned, 'sentinel'), status: 'running', approvals: [], freeze: null }, 'poisoned').word).toBe('WORKING')
    expect(laneVerdict({ ...lane(clean, 'sentinel'), outcome: 'agent_error', inbox: [] }, 'clean').word).toBe('STOPPED')
    expect(laneVerdict({ ...lane(clean, 'sentinel'), outcome: 'diverged', inbox: [] }, 'clean').sentence).toMatch(/differed from the recording/)
  })
  it('compromised PDF: Sentinel stopped the unsafe message and then only the clean summary went', () => {
    expect(laneVerdict(lane(compromisedPdf, 'sentinel'), 'compromised_pdf').sentence).toMatch(/then only a clean one was sent/)
  })
  it('every lane of every captured run gets a word, a known colour kind, and a sentence unless it merely finished', () => {
    const KINDS = ['harm', 'denied', 'allowed', 'neutral', 'approval', 'quarantined', 'running', 'error']
    for (const v of ALL) {
      for (const l of v.lanes) {
        const r = laneVerdict(l, v.scenario.id)
        expect(KINDS, `${v.scenario.id}/${l.column}`).toContain(r.kind)
        expect(r.word.length).toBeGreaterThan(0)
        expect(r.sentence.length, `${v.scenario.id}/${l.column}`).toBeGreaterThan(0)
      }
    }
  })
  it('the console never calls a baseline lane ALLOWED or DENIED (they evaluate no policy of their own)', () => {
    for (const v of ALL) {
      for (const l of v.lanes.filter((x) => x.column === 'unprotected')) {
        expect(['ALLOWED', 'DENIED', 'QUARANTINED', 'NEEDS APPROVAL']).not.toContain(laneVerdict(l, v.scenario.id).word)
      }
    }
  })
})

describe('count line and caption', () => {
  it('counts actions plainly and adds only what happened', () => {
    expect(laneCountLine(lane(poisoned, 'sentinel'))).toMatch(/^\d+ actions · 1 denied$/)
    expect(laneCountLine(lane(poisoned, 'r1_only'))).toMatch(/all allowed by access control$/)
    expect(laneCountLine({ steps: [], column: 'sentinel' })).toBe('No actions yet')
    expect(laneCountLine(lane(freeze, 'sentinel'))).toMatch(/agent quarantined/)
  })
  it('a baseline lane always says what is not being evaluated', () => {
    expect(laneCaption(lane(poisoned, 'unprotected'), poisoned)).toMatch(/^No policy evaluated/)
    expect(laneCaption(lane(poisoned, 'r1_only'), poisoned)).toMatch(/^Permission slip checks only/)
    expect(laneCaption(lane(poisoned, 'sentinel'), poisoned)).toMatch(/decisions made live/)
  })
})

describe('approval wording (what the officer is asked)', () => {
  it('names the action and its detail from the held call itself', () => {
    const v = approvalView(lane(bankWaiting, 'sentinel').approvals[0])
    expect(v.what).toBe("Change a vendor's bank account")
    expect(v.detail).toBe('shakti → account 111-222-333')
    expect(v.why).toMatch(/officer/i)
  })
})
