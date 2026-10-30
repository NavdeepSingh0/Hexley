import { describe, expect, it } from 'vitest'
import { approvalView } from './derive.js'

describe('approvalView', () => {
  it('shows every argument of a connector tool, untruncated, because the officer approves this exact request', () => {
    const body = 'x'.repeat(400)
    const v = approvalView({ tool: 'gmail.send_message', args: { to: ['ops@team.example'], subject: 'Status', body }, summary: 'Approval needed.' })
    expect(v.what).toBe('gmail.send_message')
    expect(v.detail).toContain('ops@team.example')
    expect(v.detail).toContain('subject: Status')
    expect(v.detail).toContain(body)
    expect(v.why).toBe('Approval needed.')
  })

  it('keeps the plain sentence for the demo tools', () => {
    const v = approvalView({ tool: 'send_email', args: { to: 'a@b.example', body: 'hello' }, summary: 'x' })
    expect(v.detail).toContain('to a@b.example')
  })
})
