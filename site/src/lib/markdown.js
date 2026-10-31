// A model's reply as blocks and inline pieces, never as HTML: React writes the text, so a reply cannot inject anything into the page.
// Covers what chat models write: headings, lists, code, tables, quotes, bold, italics, code spans and links. A link must be http(s).

const FENCE = /^```\s*([\w+-]*)\s*$/
const HEADING = /^(#{1,4})\s+(.+)$/
const BULLET = /^\s*[-*+]\s+(.+)$/
const NUMBER = /^\s*\d+[.)]\s+(.+)$/
const QUOTE = /^>\s?(.*)$/
const TABLE_RULE = /^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$/

const cells = (line) => line.trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map((c) => c.trim())

export function parseBlocks(text) {
  const lines = String(text ?? '').replace(/\r\n/g, '\n').split('\n')
  const blocks = []
  let i = 0
  while (i < lines.length) {
    const line = lines[i]
    if (!line.trim()) { i += 1; continue }
    const fence = line.match(FENCE)
    if (fence) {
      const body = []
      i += 1
      while (i < lines.length && !FENCE.test(lines[i])) { body.push(lines[i]); i += 1 }
      i += 1
      blocks.push({ type: 'code', lang: fence[1], text: body.join('\n') })
      continue
    }
    const heading = line.match(HEADING)
    if (heading) { blocks.push({ type: 'heading', level: heading[1].length, text: heading[2] }); i += 1; continue }
    if (line.includes('|') && i + 1 < lines.length && TABLE_RULE.test(lines[i + 1])) {
      const rows = []
      const head = cells(line)
      i += 2
      while (i < lines.length && lines[i].includes('|')) { rows.push(cells(lines[i])); i += 1 }
      blocks.push({ type: 'table', head, rows })
      continue
    }
    if (BULLET.test(line) || NUMBER.test(line)) {
      const ordered = NUMBER.test(line)
      const pattern = ordered ? NUMBER : BULLET
      const items = []
      while (i < lines.length) {
        const m = lines[i].match(pattern)
        if (m) { items.push(m[1]); i += 1 } else if (!lines[i].trim() && i + 1 < lines.length && pattern.test(lines[i + 1])) { i += 1 } else break
      }
      blocks.push({ type: 'list', ordered, items })
      continue
    }
    if (QUOTE.test(line)) {
      const body = []
      while (i < lines.length && QUOTE.test(lines[i])) { body.push(lines[i].match(QUOTE)[1]); i += 1 }
      blocks.push({ type: 'quote', text: body.join('\n') })
      continue
    }
    const para = []
    while (i < lines.length && lines[i].trim() && !FENCE.test(lines[i]) && !HEADING.test(lines[i]) && !BULLET.test(lines[i]) && !NUMBER.test(lines[i]) && !QUOTE.test(lines[i])) {
      para.push(lines[i])
      i += 1
    }
    blocks.push({ type: 'paragraph', text: para.join('\n') })
  }
  return blocks
}

const INLINE = /(`[^`\n]+`)|(\*\*[^*\n]+\*\*)|(__[^_\n]+__)|(\*[^*\s][^*\n]*\*)|(\[[^\]\n]+\]\([^)\s]+\))/

export function parseInline(text) {
  const out = []
  let rest = String(text ?? '')
  while (rest) {
    const m = rest.match(INLINE)
    if (!m) { out.push({ type: 'text', text: rest }); break }
    if (m.index > 0) out.push({ type: 'text', text: rest.slice(0, m.index) })
    const hit = m[0]
    if (m[1]) out.push({ type: 'code', text: hit.slice(1, -1) })
    else if (m[2] || m[3]) out.push({ type: 'bold', text: hit.slice(2, -2) })
    else if (m[4]) out.push({ type: 'italic', text: hit.slice(1, -1) })
    else {
      const link = hit.match(/^\[([^\]]+)\]\(([^)]+)\)$/)
      out.push(/^https?:\/\//i.test(link[2]) ? { type: 'link', text: link[1], href: link[2] } : { type: 'text', text: link[1] })
    }
    rest = rest.slice(m.index + hit.length)
  }
  return out
}
