// WCAG contrast of the shared design tokens (design/tokens.css), checked from the real file so nobody can quietly break it,
// including the website, which uses the same tokens. Text needs 4.5:1; borders and focus rings of controls need 3:1.
// Semantic backgrounds are translucent, so they are composited over the panel colour first, as they appear on screen.
import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

// A Windows clone checks these out with CRLF, and block() below looks for an exact newline.
const read = (path) => readFileSync(new URL(path, import.meta.url), 'utf8').replace(/\r\n/g, '\n')
const css = read('../../../design/tokens.css')
const primitives = read('../../../design/primitives.css')

function block(source, selector) {
  const start = source.indexOf(selector)
  return source.slice(source.indexOf('{', start) + 1, source.indexOf('}', start))
}
function themeVars(selector) {
  return Object.fromEntries([...block(css, selector).matchAll(/--([\w-]+):\s*([^;]+);/g)].map((m) => [m[1], m[2].trim()]))
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
  const surfaces = { bg: col('bg'), panel: col('panel'), raised: col('raised') }

  // Every text colour, on every surface it can sit on.
  const TEXT_COLOURS = ['ink', 'muted', 'brand', 'allowed', 'denied', 'approval', 'harm']
  const TEXT = TEXT_COLOURS.flatMap((fg) => Object.keys(surfaces).map((s) => [fg, s]))
  it.each(TEXT)('text colour %s is readable on %s (4.5:1)', (fg, s) => {
    expect(ratio(col(fg), surfaces[s])).toBeGreaterThanOrEqual(4.5)
  })

  it.each(['brand', 'allowed', 'denied', 'approval', 'harm'])('%s text is readable on its own tinted background (4.5:1)', (k) => {
    const tint = over(col(`${k}-bg`), surfaces.panel)
    expect(ratio(col(k), tint)).toBeGreaterThanOrEqual(4.5)
  })

  it('primary button text is readable on the brand fill (4.5:1); white on the dark fill would not be', () => {
    expect(ratio(col('on-brand-fill'), col('brand-fill'))).toBeGreaterThanOrEqual(4.5)
  })

  it('quarantined text is readable on the inverted block (4.5:1)', () => {
    expect(ratio(col('quarantined-ink'), col('quarantined-bg'))).toBeGreaterThanOrEqual(4.5)
  })

  it('a control boundary (ink or muted) and the focus ring are visible against every surface (3:1)', () => {
    for (const k of ['ink', 'muted', 'focus']) {
      for (const [name, surface] of Object.entries(surfaces)) expect(ratio(col(k), surface), `${k} on ${name}`).toBeGreaterThanOrEqual(3)
    }
  })

  it('the hairline colour is decorative only: it must not be relied on as a control boundary', () => {
    // documented in tokens.css; this records the fact so a future change cannot silently start using it for controls
    expect(ratio(col('line'), surfaces.bg)).toBeLessThan(3)
  })

  it('the quarantined block is a true inversion of the page (maximum separation from it)', () => {
    expect(ratio(col('quarantined-bg'), surfaces.bg)).toBeGreaterThanOrEqual(7)
  })

  it('page, panel and raised surfaces are distinguishable layers (the first version looked flat)', () => {
    expect(ratio(surfaces.bg, surfaces.panel)).toBeGreaterThanOrEqual(1.08)
    expect(ratio(surfaces.panel, surfaces.raised)).toBeGreaterThanOrEqual(1.05)
  })
})

describe('token coverage', () => {
  it('every token used by the shared primitives is defined in both themes (or is a per-element variable set in primitives.css)', () => {
    const used = new Set([...primitives.matchAll(/var\(--([\w-]+)/g)].map((m) => m[1]))
    const setLocally = new Set([...primitives.matchAll(/(?:^|[;{\s])--([\w-]+):/g)].map((m) => m[1]))
    const dark = themeVars(':root[data-theme="dark"]')
    const light = themeVars(':root[data-theme="light"]')
    const shared = Object.fromEntries([...block(css, ':root {\n  --font').matchAll(/--([\w-]+):/g)].map((m) => [m[1], true]))
    for (const name of used) {
      if (setLocally.has(name)) continue
      const defined = (dark[name] && light[name]) || shared[name]
      expect(defined, `--${name} is used in primitives.css but not defined in both themes`).toBeTruthy()
    }
  })
})

describe('the lavender frame on the website (UI v2)', () => {
  const shared = Object.fromEntries([...block(css, ':root {\n  --font').matchAll(/--([\w-]+):\s*([^;]+);/g)].map((m) => [m[1], m[2].trim()]))
  it('ink on the frame is readable at both of its colours', () => {
    for (const name of ['frame', 'frame-2']) {
      const r = ratio(parse(shared['on-frame']), parse(shared[name]))
      expect(r, `${name}`).toBeGreaterThanOrEqual(7)
    }
  })
  it('the frame is clearly lighter than a black page, so its edge is visible', () => {
    expect(ratio(parse(shared.frame), parse('#07070a'))).toBeGreaterThanOrEqual(3)
  })
})
