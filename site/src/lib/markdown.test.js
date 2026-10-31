import { describe, expect, it } from 'vitest'
import { parseBlocks, parseInline } from './markdown.js'

describe('parseBlocks', () => {
  it('reads what chat models write', () => {
    const blocks = parseBlocks('# Title\n\nA line\nand another\n\n- one\n- two\n\n1. first\n2. second\n\n> said\n\n```py\nprint(1)\n```\n\n| a | b |\n|---|---|\n| 1 | 2 |\n')
    expect(blocks.map((b) => b.type)).toEqual(['heading', 'paragraph', 'list', 'list', 'quote', 'code', 'table'])
    expect(blocks[2]).toEqual({ type: 'list', ordered: false, items: ['one', 'two'] })
    expect(blocks[3].ordered).toBe(true)
    expect(blocks[5]).toEqual({ type: 'code', lang: 'py', text: 'print(1)' })
    expect(blocks[6]).toEqual({ type: 'table', head: ['a', 'b'], rows: [['1', '2']] })
  })

  it('keeps a code block still being written, and nothing is lost from an empty reply', () => {
    expect(parseBlocks('```\nhalf')).toEqual([{ type: 'code', lang: '', text: 'half' }])
    expect(parseBlocks('')).toEqual([])
    expect(parseBlocks(null)).toEqual([])
  })

  it('a numbered list split by blank lines stays one list', () => {
    expect(parseBlocks('1. a\n\n2. b')).toEqual([{ type: 'list', ordered: true, items: ['a', 'b'] }])
  })
})

describe('parseInline', () => {
  it('reads bold, italics, code and links', () => {
    expect(parseInline('a **b** *c* `d` [e](https://x.example/y)')).toEqual([
      { type: 'text', text: 'a ' }, { type: 'bold', text: 'b' }, { type: 'text', text: ' ' }, { type: 'italic', text: 'c' }, { type: 'text', text: ' ' },
      { type: 'code', text: 'd' }, { type: 'text', text: ' ' }, { type: 'link', text: 'e', href: 'https://x.example/y' },
    ])
  })

  it('a link that is not http(s) becomes plain text, so a reply cannot run a script', () => {
    expect(parseInline('[click](javascript:alert(1))').some((p) => p.type === 'link')).toBe(false)
    expect(parseInline('[click](data:text/html,x)').some((p) => p.type === 'link')).toBe(false)
  })

  it('leaves a lone star and plain sums alone', () => {
    expect(parseInline('2 * 3 = 6')).toEqual([{ type: 'text', text: '2 * 3 = 6' }])
  })
})
