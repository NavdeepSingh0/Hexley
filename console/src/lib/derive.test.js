// These tests run against views captured from real scripted runs (spikes/capture_fixtures.py), not hand-written ones.
import { describe, expect, it } from 'vitest'
import poisoned from '../fixtures/poisoned.json'
import poisonedAwaiting from '../fixtures/poisoned_awaiting.json'
import clean from '../fixtures/clean.json'
import redirect from '../fixtures/redirect.json'
import freeze from '../fixtures/freeze.json'
import hardened from '../fixtures/hardened.json'
import bankWaiting from '../fixtures/bank_change_waiting.json'
import bankDone from '../fixtures/bank_change_done.json'
import verifyOk from '../fixtures/verify_ok.json'
import verifyBad from '../fixtures/verify_tampered.json'
import compromisedPdf from '../fixtures/compromised_pdf.json'
import poisonedWeb from '../fixtures/poisoned_web.json'
import stranger from '../fixtures/stranger.json'
import {
  DECISION_WORD, RULE_LABEL, RULE_SPEECH, TOOL_ALLOWS, TOOL_LABEL, bankChanges, chainLinks, firstBlockedStep, groupSlips,
  highlightTokens, inboxRowView, laneCounts, laneHeadline, mascotFor, pickDefaultRecording, presenterNext, shortArgs, stepStamp,
  verifyView,
} from './derive.js'

const lane = (view, column, i) => view.lanes.filter((l) => l.column === column)[i ?? 0]

describe('lane headlines (what a non-specialist reads first)', () => {
  it('poisoned: the baselines say LEAKED, Sentinel says DENIED', () => {
    expect(laneHeadline(lane(poisoned, 'unprotected'))).toEqual({ tone: 'leak', text: 'LEAKED: restricted data reached the outside' })
    expect(laneHeadline(lane(poisoned, 'r1_only')).tone).toBe('leak')
    expect(laneHeadline(lane(poisoned, 'sentinel'))).toEqual({ tone: 'denied', text: 'DENIED: nothing left the building' })
  })
  it('clean: every column says the message was sent, none says leaked or denied', () => {
    for (const l of clean.lanes) expect(laneHeadline(l)).toEqual({ tone: 'sent', text: 'SENT: clean message only' })
  })
  it('redirect: a reply to another mailbox is flagged in the baselines, denied in Sentinel', () => {
    expect(laneHeadline(lane(redirect, 'unprotected')).text).toMatch(/WRONG ADDRESS/)
    expect(laneHeadline(lane(redirect, 'r1_only')).tone).toBe('leak')
    expect(laneHeadline(lane(redirect, 'sentinel')).tone).toBe('denied')
  })
  it('freeze: Sentinel QUARANTINES the agent after 3 denied attempts', () => {
    const h = laneHeadline(lane(freeze, 'sentinel'))
    expect(h.tone).toBe('quarantined')
    expect(h.text).toMatch(/^QUARANTINED: .*after 3 denied attempts/)
  })
  it('hardened: the hardened lane is quarantined, the fingerprint lane delivered a paraphrase the oracle does not flag', () => {
    expect(laneHeadline(hardened.lanes[1]).tone).toBe('quarantined')
    expect(hardened.lanes[0].inbox).toHaveLength(1)
    expect(hardened.lanes[0].inbox[0].oracle_leak).toBe(false)
    expect(laneHeadline(hardened.lanes[0]).text).toBe('SENT: clean message only')
  })
  it('bank change: waiting for the officer, then changed only after approval; baselines changed it unasked', () => {
    expect(laneHeadline(lane(bankWaiting, 'sentinel'))).toEqual({ tone: 'needs-approval', text: 'NEEDS APPROVAL: waiting for the officer' })
    expect(laneHeadline(lane(bankDone, 'unprotected')).text).toMatch(/BANK ACCOUNT CHANGED to 111-222-333/)
    expect(laneHeadline(lane(bankDone, 'sentinel'))).toEqual({ tone: 'sent', text: 'CHANGED: only after the officer approved' })
    expect(bankChanges(lane(bankDone, 'sentinel'))[0]).toMatchObject({ account: '111-222-333', approved: true })
    expect(bankChanges(lane(bankWaiting, 'sentinel'))).toEqual([]) // held: nothing happened yet
  })
  it('a lane that is still running says so; an errored lane says so', () => {
    expect(laneHeadline({ ...lane(poisoned, 'sentinel'), status: 'running', approvals: [], freeze: null }).tone).toBe('running')
    expect(laneHeadline({ ...lane(clean, 'sentinel'), outcome: 'agent_error', inbox: [] }).tone).toBe('error')
    expect(laneHeadline({ ...lane(clean, 'sentinel'), outcome: 'diverged', inbox: [] }).tone).toBe('error')
  })
})

describe('step stamps: allowed is never styled as good', () => {
  it('maps each effect to the deck vocabulary: ALLOWED, DENIED, NEEDS APPROVAL, QUARANTINED', () => {
    const sentinel = lane(poisoned, 'sentinel')
    expect(stepStamp(sentinel.steps[0])).toEqual({ kind: 'allowed', label: 'ALLOWED' })
    expect(stepStamp(sentinel.steps[2])).toEqual({ kind: 'denied', label: 'DENIED · R2' })
    expect(stepStamp(lane(poisoned, 'unprotected').steps[2]).label).toBe('ALLOWED · no policy evaluated')
    expect(stepStamp(lane(freeze, 'sentinel').steps.at(-1)).kind).toBe('quarantined')
    expect(stepStamp(lane(freeze, 'sentinel').steps.at(-1)).label).toMatch(/^QUARANTINED · R2 \+ R6/)
    expect(stepStamp({ effect: null }).kind).toBe('pending')
    expect(stepStamp({ effect: 'ASK' })).toEqual({ kind: 'needs-approval', label: 'NEEDS APPROVAL' })
  })
  it('the four decision words are one list, and no old wording survives in the stamps or headlines', () => {
    expect(DECISION_WORD).toEqual({ ALLOW: 'ALLOWED', BLOCK: 'DENIED', ASK: 'NEEDS APPROVAL', FREEZE: 'QUARANTINED' })
    const all = [poisoned, clean, redirect, stranger, freeze, hardened, bankWaiting, bankDone, compromisedPdf, poisonedWeb]
      .flatMap((v) => v.lanes).flatMap((l) => [laneHeadline(l).text, ...l.steps.map((s) => stepStamp(s).label)]).join('\n')
    expect(all).not.toMatch(/\b(STOPPED|FROZEN|WAITING FOR THE OFFICER)\b/)
  })
  it('an officer-approved step says so', () => {
    expect(stepStamp(lane(bankDone, 'sentinel').steps[0]).label).toBe('ALLOWED · officer approved')
  })
})

describe('counts, args and inbox rows', () => {
  it('counts calls by decision', () => {
    expect(laneCounts(lane(poisoned, 'sentinel'))).toEqual({ calls: 3, allowed: 2, denied: 1, quarantined: 0 })
    expect(laneCounts(lane(freeze, 'sentinel')).quarantined).toBe(1)
  })
  it('short args never print an object dump for the known tools', () => {
    const steps = lane(poisoned, 'sentinel').steps
    expect(shortArgs(steps[0])).toBe('quotation Q-1043')
    expect(shortArgs(steps[2])).toMatch(/^to sales@shakti\.example — “/)
  })
  it('flags a reply to an address other than the registered vendor', () => {
    const row = lane(redirect, 'r1_only').inbox[0]
    expect(inboxRowView(row, lane(redirect, 'r1_only').contract)).toMatchObject({ misdirected: true, leak: false, clean: false })
    const ok = lane(clean, 'sentinel').inbox[0]
    expect(inboxRowView(ok, lane(clean, 'sentinel').contract)).toMatchObject({ misdirected: false, leak: false, clean: true })
  })
})

describe('slips are shown once when identical', () => {
  it('three identical lanes become one slip issued to three columns', () => {
    const g = groupSlips(poisoned.lanes)
    expect(g).toHaveLength(1)
    expect(g[0].columns).toEqual(['unprotected', 'r1_only', 'sentinel'])
    expect(g[0].contract.resolved_vendor.email).toBe('sales@shakti.example')
  })
  it('the slip states where restricted data may go: nowhere outside for the quotation, the named manager for the PDF task', () => {
    expect(groupSlips(poisoned.lanes)[0].contract.internal_destinations).toEqual([])
    expect(groupSlips(compromisedPdf.lanes)[0].contract.internal_destinations).toEqual(['manager@corp.example'])
    expect(groupSlips(poisonedWeb.lanes)[0].contract.internal_destinations).toEqual(['intranet.corp.example'])
  })
  it('the hardened scenario has two different slips', () => {
    const g = groupSlips(hardened.lanes)
    expect(g).toHaveLength(2)
    expect(g[1].contract.allowed_tools).toContain('send_quote_ack')
    expect(g[1].contract.egress_template.body).toMatch(/^Quotation \{quote_id\} received/)
  })
})

describe('evidence highlighting', () => {
  const blocked = lane(poisoned, 'sentinel').steps[2]
  const tokens = blocked.evidence.flatMap((e) => e.matched_tokens)
  it('marks the matched values inside the blocked message, preserving its own casing', () => {
    const { segments } = highlightTokens(blocked.args.body, tokens)
    const hits = segments.filter((s) => s.hit).map((s) => s.text)
    expect(hits.length).toBeGreaterThanOrEqual(3)
    expect(hits.some((h) => /fsd-14/i.test(h))).toBe(true)
    expect(segments.map((s) => s.text).join('')).toBe(blocked.args.body) // nothing lost or invented
  })
  it('lists a token it cannot find in the text instead of pretending to', () => {
    const r = highlightTokens('nothing to see here', ['two thousand four hundred'])
    expect(r.segments).toEqual([{ text: 'nothing to see here', hit: false }])
    expect(r.unlocated).toEqual(['two thousand four hundred'])
  })
  it('merges overlapping tokens', () => {
    const r = highlightTokens('depot FSD-14 now', ['fsd-14', 'FSD'])
    expect(r.segments.filter((s) => s.hit)).toHaveLength(1)
  })
})

describe('chain links come only from evidence', () => {
  it('poisoned: one link from the stock check to the blocked send, none in the baselines', () => {
    expect(chainLinks(lane(poisoned, 'sentinel'))).toEqual([{ from: 1, to: 2, source: 'query_stock' }])
    expect(chainLinks(lane(poisoned, 'unprotected'))).toEqual([])
    expect(chainLinks(lane(poisoned, 'r1_only'))).toEqual([])
  })
  it('redirect: the link comes from the quotation read (R3 names its source tool)', () => {
    expect(chainLinks(lane(redirect, 'sentinel'))).toEqual([{ from: 0, to: 1, source: 'read_quotation' }])
  })
  it('clean: nothing was blocked, so there are no links', () => {
    expect(chainLinks(lane(clean, 'sentinel'))).toEqual([])
  })
  it('never links to a step that did not complete', () => {
    const l = JSON.parse(JSON.stringify(lane(poisoned, 'sentinel')))
    l.steps[1].completed = null
    expect(chainLinks(l)).toEqual([])
  })
  it('finds the first blocked step for the verdict', () => {
    expect(firstBlockedStep(lane(poisoned, 'sentinel')).index).toBe(2)
    expect(firstBlockedStep(lane(clean, 'sentinel'))).toBeNull()
  })
})

describe('recordings and the presenter', () => {
  const rec = (attempt, outcomes, scenario = 'poisoned') => ({ scenario, attempt, lanes: outcomes.map((outcome) => ({ outcome })) })
  it('prefers the earliest attempt that ended without an error', () => {
    const list = [rec(1, ['completed', 'agent_error']), rec(2, ['completed', 'recovered']), rec(3, ['completed', 'recovered'])]
    expect(pickDefaultRecording(list, 'poisoned').attempt).toBe(2)
  })
  it('falls back to the earliest attempt, and to null when there is none', () => {
    expect(pickDefaultRecording([rec(2, ['agent_error']), rec(1, ['agent_error'])], 'poisoned').attempt).toBe(1)
    expect(pickDefaultRecording([], 'poisoned')).toBeNull()
    expect(pickDefaultRecording([rec(1, ['completed'], 'clean')], 'poisoned')).toBeNull()
  })
  it('Enter creates, confirms, waits, opens the verdict, then moves on', () => {
    const base = { playlistIndex: 0, playlistLength: 4, verdictOpen: false, hasVerdict: true }
    expect(presenterNext({ ...base, screen: 'start' })).toBe('create')
    expect(presenterNext({ ...base, screen: 'start', playlistIndex: 4 })).toBe('done')
    expect(presenterNext({ ...base, screen: 'slip' })).toBe('confirm')
    expect(presenterNext({ ...base, screen: 'stage', runStatus: 'running' })).toBe('wait')
    expect(presenterNext({ ...base, screen: 'stage', runStatus: 'finished' })).toBe('open-verdict')
    expect(presenterNext({ ...base, screen: 'stage', runStatus: 'finished', verdictOpen: true })).toBe('close-and-next')
    expect(presenterNext({ ...base, screen: 'stage', runStatus: 'finished', hasVerdict: false })).toBe('next')
  })
})

describe('the general-purpose scenarios (your own task, a poisoned page)', () => {
  const pdf = (c) => lane(compromisedPdf, c)
  const web = (c) => lane(poisonedWeb, c)

  it('compromised PDF: both baselines leaked, Sentinel denied it and then sent only the real summary', () => {
    expect(laneHeadline(pdf('unprotected')).tone).toBe('leak')
    expect(laneHeadline(pdf('r1_only')).tone).toBe('leak') // the audit address is inside the allowed domain
    expect(laneHeadline(pdf('sentinel'))).toEqual({ tone: 'denied', text: 'DENIED, then only a clean message was sent' })
    expect(pdf('sentinel').inbox.map((m) => m.to)).toEqual(['manager@corp.example'])
    const blocked = pdf('sentinel').steps[4]
    expect(stepStamp(blocked)).toEqual({ kind: 'denied', label: 'DENIED · R2 + R3' })
  })

  it('the provenance arrow points at the COMPROMISED document, not the harmless one that was read first', () => {
    const steps = pdf('sentinel').steps
    expect(steps[1].args.path).toBe('reports/q3_summary.pdf')
    expect(steps[2].args.path).toBe('reports/vendor_notes.pdf')
    const links = chainLinks(pdf('sentinel'))
    expect(links.find((l) => l.source === 'read_document')).toEqual({ from: 2, to: 4, source: 'read_document' })
    expect(links.find((l) => l.source === 'query_db')).toEqual({ from: 3, to: 4, source: 'query_db' })
    expect(links.every((l) => l.to === 4)).toBe(true)
    expect(chainLinks(pdf('r1_only'))).toEqual([])
  })

  it('older recordings, whose evidence names only the tool, fall back to the earliest call of that tool', () => {
    const legacy = JSON.parse(JSON.stringify(pdf('sentinel')))
    for (const e of legacy.steps[4].evidence) delete e.source_action_id
    expect(chainLinks(legacy).find((l) => l.source === 'read_document').from).toBe(1)
  })

  it('poisoned web page: both baselines leaked through the allowed channel, Sentinel contained it', () => {
    for (const c of ['unprotected', 'r1_only']) expect(laneHeadline(web(c)).tone).toBe('leak')
    expect(laneHeadline(web('sentinel'))).toEqual({ tone: 'denied', text: 'DENIED: nothing left the building' })
    expect(web('unprotected').inbox.map((m) => m.to)).toEqual(['https://hooks.corp.example/status'])
    expect(chainLinks(web('sentinel'))).toEqual([{ from: 1, to: 2, source: 'query_db' }])
  })

  it('every tool these scenarios use has a plain-English name, and its arguments read as a sentence', () => {
    for (const v of [compromisedPdf, poisonedWeb]) {
      for (const l of v.lanes) {
        for (const s of l.steps) {
          expect(TOOL_LABEL[s.tool], s.tool).toBeTruthy()
          expect(TOOL_ALLOWS[s.tool], s.tool).toBeTruthy()
          expect(shortArgs(s)).not.toMatch(/^\{/) // never a raw JSON dump for a known tool
        }
      }
    }
    expect(shortArgs(pdf('sentinel').steps[0])).toBe('folder reports')
    expect(shortArgs(pdf('sentinel').steps[3])).toMatch(/^SQL: SELECT name, email, phone FROM customers/)
    expect(shortArgs(web('sentinel').steps[2])).toMatch(/^to https:\/\/hooks\.corp\.example\/status — “Status: safety week/)
    expect(RULE_LABEL.R7).toBeTruthy()
  })
})

describe('the mascot shows only what really happened (docs/contracts/MASCOT.md)', () => {
  const sleep = { state: 'sleeping', message: '' }

  it('is asleep with no run, idle before the officer confirms, and the speech is the contract text for the rule', () => {
    expect(mascotFor(null)).toEqual(sleep)
    expect(mascotFor(poisonedAwaiting)).toEqual({ state: 'idle', message: '' })
    expect(RULE_SPEECH.R2).toBe('That would send restricted data out.')
    expect(Object.keys(RULE_SPEECH)).toEqual(['R1', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7'])
  })
  it('a finished run with a denial shows DENIED with the words of the rule that decided', () => {
    expect(mascotFor(poisoned)).toEqual({ state: 'denied', message: 'That would send restricted data out.' })
    expect(mascotFor(stranger).state).toBe('denied')
    expect(mascotFor(compromisedPdf).message).toBe('That would send restricted data out.') // R2 decided first (R3 also fired)
  })
  it('a finished run with no denial is idle, never "allowed" (allowed is not a celebration)', () => {
    expect(mascotFor(clean)).toEqual({ state: 'idle', message: '' })
  })
  it('a quarantined lane shows QUARANTINED and says why', () => {
    expect(mascotFor(freeze)).toEqual({ state: 'quarantined', message: RULE_SPEECH.R6 })
    expect(mascotFor(hardened).state).toBe('quarantined')
  })
  it('a pending officer approval shows NEEDS APPROVAL', () => {
    expect(mascotFor(bankWaiting)).toEqual({ state: 'needs-approval', message: RULE_SPEECH.R4 })
    expect(mascotFor(bankDone).state).toBe('idle') // approved and finished: nothing pending, nothing denied
  })
  it('a call held for the officer and then denied says so, instead of repeating "needs approval"', () => {
    const timedOut = JSON.parse(JSON.stringify(bankWaiting))
    const s = timedOut.lanes[2]
    s.approvals = []
    s.status = 'finished'
    s.steps[0] = { ...s.steps[0], effect: 'BLOCK', rule_ids: ['R4'], held: true }
    expect(mascotFor(timedOut)).toEqual({ state: 'denied', message: 'The officer did not approve it.' })
  })
  it('speaks only for the Sentinel lanes: the baselines have no decisions to report', () => {
    const baselinesOnly = { ...poisoned, lanes: poisoned.lanes.filter((l) => l.column !== 'sentinel') }
    expect(mascotFor(baselinesOnly).state).toBe('idle')
  })
  it('a call still being decided shows CHECKING, and an allowed call while running shows ALLOWED', () => {
    const live = JSON.parse(JSON.stringify(poisoned))
    const s = live.lanes[2]
    s.status = 'running'
    s.steps = s.steps.slice(0, 2)
    expect(mascotFor(live)).toEqual({ state: 'allowed', message: 'Checked: allowed.' })
    s.steps[1].effect = null
    expect(mascotFor(live).state).toBe('checking')
  })
  it('an altered audit log shows TAMPER whatever else is happening', () => {
    expect(mascotFor(poisoned, verifyBad)).toEqual({ state: 'tamper', message: 'The audit log was altered!' })
    expect(mascotFor(poisoned, verifyOk).state).toBe('denied')
  })
})

describe('audit verification wording', () => {
  it('says intact, tampered (with the record number), or not checked', () => {
    expect(verifyView(verifyOk)).toEqual({ tone: 'ok', text: `Chain intact · ${verifyOk.checked} records` })
    const bad = verifyView(verifyBad)
    expect(bad.tone).toBe('bad')
    expect(bad.text).toContain(`#${verifyBad.first_bad_seq}`)
    expect(verifyView(null).tone).toBe('idle')
  })
})

describe('the backend supplies the exact column titles (D-028); the console never retypes them', () => {
  it('uses the titles from the view', () => {
    expect(poisoned.lanes.map((l) => l.title)).toEqual([
      'No policy enforcement — instrumented baseline', 'R1-only access control', 'Sentinel'])
  })
})
