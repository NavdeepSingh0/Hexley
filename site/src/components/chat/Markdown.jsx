import { useState } from 'react'
import { parseBlocks, parseInline } from '../../lib/markdown.js'

function Inline({ text }) {
  return parseInline(text).map((p, i) => {
    if (p.type === 'code') return <code key={i}>{p.text}</code>
    if (p.type === 'bold') return <strong key={i}>{p.text}</strong>
    if (p.type === 'italic') return <em key={i}>{p.text}</em>
    if (p.type === 'link') return <a key={i} href={p.href} target="_blank" rel="noopener noreferrer nofollow">{p.text}</a>
    return <span key={i}>{p.text}</span>
  })
}

export function CopyButton({ text, label = 'Copy' }) {
  const [done, setDone] = useState(false)
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text)
      setDone(true)
      setTimeout(() => setDone(false), 1500)
    } catch { /* the browser refused; nothing to do but leave the text selectable */ }
  }
  return <button type="button" className="cx-copy" onClick={copy}>{done ? 'Copied' : label}</button>
}

export default function Markdown({ text }) {
  return (
    <div className="cx-md">
      {parseBlocks(text).map((b, i) => {
        switch (b.type) {
          case 'code':
            return (
              <div key={i} className="cx-code">
                <div className="cx-code-head"><span>{b.lang || 'text'}</span><CopyButton text={b.text} /></div>
                <pre><code>{b.text}</code></pre>
              </div>
            )
          case 'heading': {
            const Tag = `h${Math.min(b.level + 2, 6)}`
            return <Tag key={i}><Inline text={b.text} /></Tag>
          }
          case 'list': {
            const Tag = b.ordered ? 'ol' : 'ul'
            return <Tag key={i}>{b.items.map((item, j) => <li key={j}><Inline text={item} /></li>)}</Tag>
          }
          case 'quote':
            return <blockquote key={i}><Inline text={b.text} /></blockquote>
          case 'table':
            return (
              <div key={i} className="cx-table-wrap">
                <table>
                  <thead><tr>{b.head.map((c, j) => <th key={j}><Inline text={c} /></th>)}</tr></thead>
                  <tbody>{b.rows.map((r, j) => <tr key={j}>{r.map((c, k) => <td key={k}><Inline text={c} /></td>)}</tr>)}</tbody>
                </table>
              </div>
            )
          default:
            return <p key={i}><Inline text={b.text} /></p>
        }
      })}
    </div>
  )
}
