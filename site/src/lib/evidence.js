// Evidence strip data. Every number on the site comes from /evidence.json (written from eval/results/, see F6), never typed
// into a page. An entry that does not carry its sample size, interval, source and caveat is dropped, not shown bare.

const FIELDS = ['group', 'group_title', 'arm', 'label', 'value', 'n', 'ci95', 'source_file', 'caveat']

export function isComplete(item) {
  if (!item || typeof item !== 'object') return false
  if (FIELDS.some((f) => item[f] === undefined || item[f] === null || item[f] === '')) return false
  if (!Number.isFinite(item.n) || item.n <= 0) return false
  if (!Array.isArray(item.ci95) || item.ci95.length !== 2 || !item.ci95.every(Number.isFinite)) return false
  return item.arm === 'protected' || item.arm === 'unprotected'
}

// "0 to 8.6 percent"; whole numbers lose their decimal.
export function formatInterval([lo, hi]) {
  const pct = (x) => `${Number((x * 100).toFixed(1))}`
  return `${pct(lo)} to ${pct(hi)} percent`
}

// Pair the numbers into groups: {title, protectedItem, unprotectedItem}. A group without a protected number is dropped,
// because the "without" figure alone would be a claim about nothing.
export function groupEvidence(items) {
  const groups = new Map()
  const dropped = []
  for (const item of Array.isArray(items) ? items : []) {
    if (!isComplete(item)) { dropped.push(item); continue }
    const g = groups.get(item.group) ?? { id: item.group, title: item.group_title, protectedItem: null, unprotectedItem: null }
    if (item.arm === 'protected') g.protectedItem = item
    else g.unprotectedItem = item
    groups.set(item.group, g)
  }
  return { groups: [...groups.values()].filter((g) => g.protectedItem), dropped }
}

// Build-time check (scripts/check-evidence.mjs): every problem that would make the home page drop or mislead, as plain
// sentences. An empty list means the file is fit to ship. The build fails otherwise, so no bare number reaches a page.
export function validateEvidence(items) {
  if (!Array.isArray(items) || items.length === 0) return ['evidence.json is empty or not a list']
  const problems = []
  items.forEach((item, i) => {
    const name = `entry ${i + 1}${item && item.label ? ` ("${item.label}")` : ''}`
    if (!isComplete(item)) {
      const missing = FIELDS.filter((f) => !item || item[f] === undefined || item[f] === null || item[f] === '')
      problems.push(`${name} is incomplete${missing.length ? `: missing ${missing.join(', ')}` : ' (bad n, interval or arm)'}`)
      return
    }
    const m = /^(\d+) of (\d+)$/.exec(item.value)
    if (!m || Number(m[2]) !== item.n || Number(m[1]) > item.n) problems.push(`${name}: value "${item.value}" does not match n = ${item.n}`)
    if (item.ci95[0] > item.ci95[1] || item.ci95[0] < 0 || item.ci95[1] > 1) problems.push(`${name}: the interval is not between 0 and 1`)
  })
  if (problems.length === 0 && groupEvidence(items).groups.length === 0) problems.push('no group has a protected figure, so the home page would show no number')
  return problems
}
