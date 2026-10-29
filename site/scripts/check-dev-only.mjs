// Runs after every production build: the build fails if any part of a development-only page ended up in dist/.
// Today those are the mascot lab (src/pages/MascotLab.jsx, marked MASCOT_LAB_DEV_ONLY and its own css classes), the mascot
// page (MASCOT_PAGE_DEV_ONLY) and the styleguide (STYLEGUIDE_DEV_ONLY).
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const dist = fileURLToPath(new URL('../dist/', import.meta.url))
const FORBIDDEN = ['MASCOT_LAB_DEV_ONLY', 'mascot-lab', 'lab-controls', 'lab-stage-mascot', 'MASCOT_PAGE_DEV_ONLY', 'STYLEGUIDE_DEV_ONLY']

function* files(dir) {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name)
    if (e.isDirectory()) yield* files(p)
    else if (/\.(js|css|html|map)$/.test(e.name)) yield p
  }
}

const hits = []
for (const f of files(dist)) {
  const text = fs.readFileSync(f, 'utf8')
  for (const word of FORBIDDEN) if (text.includes(word)) hits.push(`${path.relative(dist, f)} contains "${word}"`)
}
if (hits.length) {
  console.error('development-only check failed: the production build contains a development-only page:')
  for (const h of hits) console.error('  - ' + h)
  process.exit(1)
}
console.log('development-only check passed: the mascot lab, the mascot page and the styleguide are not in the production build')
