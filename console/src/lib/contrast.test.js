// WCAG contrast of the shared design tokens (design/tokens.css), checked from the real file so nobody can quietly break it,
// including the website, which uses the same tokens. Text needs 4.5:1; borders and focus rings of controls need 3:1.
// Semantic backgrounds are translucent, so they are composited over the panel colour first, as they appear on screen.
import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const css = readFileSync(new URL('../../../design/tokens.css', import.meta.url), 'utf8')

function themeVars(selector) {
  const start = css.indexOf(selector)
  const body = css.slice(css.indexOf('{', start) + 1, css.indexOf('}', start))
  return Object.fromEntries([...body.matchAll(/--([\w-]+):\s*([^;]+);/g)].map((m) => [m[1], m[2].trim()]))
}

const parse = (v) => {
  if (v.startsWith('#')) {
    const n = parseInt(v.slice(1), 16)
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255, 1]
  }
  const p = v.match(/rgba?\(([^)]+)\)/)[1].split(',').map(parseFloat)
  return [p[0], p[1], p[2], p[3] ?? 1]
}
const over = (fg, bg) => [0, 1, 2].map((i) => fg[i] * fg[3] + bg[i] * (1 - fg[3]))
const luminance = (rgb) => {
  const f = (c) => ((c /= 255) <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4)
  return 0.2126 * f(rgb[0]) + 0.7152 * f(rgb[1]) + 0.0722 * f(rgb[2])
}
const ratio = (a, b) => {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x)
  return (hi + 0.05) / (lo + 0.05)
}

describe.each([['dark', ':root[data-theme="dark"]'], ['light', ':root[data-theme="light"]']])('%s theme tokens', (_name, selector) => {
  const t = themeVars(selector)
  const col = (k) => parse(t[k])
  const bg = col('bg')
  const panel = col('panel')
  const tint = (k) => over(col(k), panel)

  const TEXT = [
    ['ink', bg], ['ink', panel], ['muted', bg], ['muted', panel],
    ['denied', tint('denied-bg')], ['harm', tint('harm-bg')], ['approval', tint('approval-bg')], ['ok', tint('ok-bg')],
    ['denied', panel], ['harm', panel], ['approval', panel], ['ok', panel],
    ['quarantined-ink', col('quarantined-bg')],
  ]
  it.each(TEXT.map(([fg, back], i) => [fg, i]))('text colour %s is readable on its background (4.5:1)', (fg, i) => {
    expect(ratio(col(fg), TEXT[i][1]), `${fg} on background #${i}`).toBeGreaterThanOrEqual(4.5)
  })

  it('a control boundary (ink or muted) and the focus ring are visible against every surface (3:1)', () => {
    for (const k of ['ink', 'muted', 'focus']) {
      for (const surface of [bg, panel]) expect(ratio(col(k), surface), k).toBeGreaterThanOrEqual(3)
    }
  })

  it('the hairline colour is decorative only: it must not be relied on as a control boundary', () => {
    // documented in tokens.css; this records the fact so a future change cannot silently start using it for controls
    expect(ratio(col('line'), bg)).toBeLessThan(3)
  })

  it('the quarantined block is a true inversion of the page (maximum separation from it)', () => {
    expect(ratio(col('quarantined-bg'), bg)).toBeGreaterThanOrEqual(7)
  })
})
