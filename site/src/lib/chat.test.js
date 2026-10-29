import { describe, expect, it } from 'vitest'
import { allActions, busyLine, composerBlock, decisionKind, decisionWord, pendingApproval, pollDelay, ruleLabel } from './chat.js'

const view = (status, actions = [], retry = null) => ({ status, retry, messages: [{ id: 'm1', role: 'assistant', text: '', actions }] })
const act = (decision, extra = {}) => ({ action_id: 'a', tool: 't', decision, approval_id: null, ...extra })

describe('pollDelay', () => {
  it('is quick while an answer is written and slow when idle', () => {
    expect(pollDelay('thinking')).toBe(700)
    expect(pollDelay('model_busy')).toBe(700)
    expect(pollDelay('ready')).toBe(2500)
    expect(pollDelay('awaiting_confirmation')).toBe(2500)
  })
  it('stops when the chat is over', () => {
    expect(pollDelay('quarantined')).toBeNull()
    expect(pollDelay('ended')).toBeNull()
  })
})

describe('decision words', () => {
  it('are the four deck words, with spaces', () => {
    expect(decisionWord('NEEDS_APPROVAL')).toBe('NEEDS APPROVAL')
    expect(decisionWord('DENIED')).toBe('DENIED')
    expect(decisionWord('ALLOWED')).toBe('ALLOWED')
    expect(decisionWord('QUARANTINED')).toBe('QUARANTINED')
  })
  it('a call still being checked is not called allowed', () => {
    expect(decisionWord('PENDING')).toBe('CHECKING')
    expect(decisionKind('PENDING')).toBe('pending')
  })
  it('an unknown decision is not dressed up as a known one', () => {
    expect(decisionKind('WHATEVER')).toBe('pending')
    expect(decisionWord('SOME_NEW')).toBe('SOME NEW')
  })
})

describe('pendingApproval', () => {
  it('finds the first held action that has an approval id', () => {
    const v = view('thinking', [act('ALLOWED'), act('NEEDS_APPROVAL', { approval_id: 'apr_1' }), act('NEEDS_APPROVAL', { approval_id: 'apr_2' })])
    expect(pendingApproval(v).approval_id).toBe('apr_1')
  })
  it('ignores a held action with nothing to approve and a resolved one', () => {
    expect(pendingApproval(view('ready', [act('NEEDS_APPROVAL')]))).toBeNull()
    expect(pendingApproval(view('ready', [act('ALLOWED', { approval_id: 'apr_1' })]))).toBeNull()
    expect(pendingApproval(null)).toBeNull()
  })
})

describe('composerBlock', () => {
  it('is open only when the chat is ready', () => {
    expect(composerBlock(view('ready'))).toBe('')
    for (const s of ['awaiting_confirmation', 'thinking', 'model_busy', 'quarantined', 'ended']) expect(composerBlock(view(s))).not.toBe('')
    expect(composerBlock(null)).not.toBe('')
  })
  it('says why in plain words for a quarantine', () => {
    expect(composerBlock(view('quarantined'))).toMatch(/quarantined/)
  })
})

describe('busyLine', () => {
  it('names the attempt and the wait', () => {
    expect(busyLine(view('model_busy', [], { attempt: 2, waiting_s: 7.6 }))).toBe('The model is busy. Trying again (attempt 2, about 8 s).')
  })
  it('is empty unless the model is busy', () => {
    expect(busyLine(view('ready'))).toBe('')
    expect(busyLine(view('model_busy', [], null))).toBe('')
  })
})

describe('ruleLabel and allActions', () => {
  it('names a known rule and leaves an unknown one alone', () => {
    expect(ruleLabel('R2')).toBe('R2: Restricted data stays in')
    expect(ruleLabel('R9')).toBe('R9: Found credentials are never used')
    expect(ruleLabel('R42')).toBe('R42')
  })
  it('collects actions from every message', () => {
    const v = { messages: [{ actions: [act('ALLOWED')] }, { actions: [act('DENIED'), act('DENIED')] }, {}] }
    expect(allActions(v)).toHaveLength(3)
    expect(allActions(null)).toEqual([])
  })
})
