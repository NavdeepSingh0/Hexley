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
