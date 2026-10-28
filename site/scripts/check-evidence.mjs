// Runs before every build (npm run build): the build stops if evidence.json has a number without its sample size,
// interval, source or caveat. See src/lib/evidence.js.
import fs from 'node:fs'
import { fileURLToPath } from 'node:url'
import { validateEvidence } from '../src/lib/evidence.js'

const file = fileURLToPath(new URL('../public/evidence.json', import.meta.url))
let items
try {
  items = JSON.parse(fs.readFileSync(file, 'utf8'))
} catch (e) {
  console.error(`evidence check failed: cannot read public/evidence.json (${e.message})`)
  process.exit(1)
}
const problems = validateEvidence(items)
if (problems.length) {
  console.error('evidence check failed: the site will not build with these numbers:')
  for (const p of problems) console.error('  - ' + p)
  process.exit(1)
}
console.log(`evidence check passed: ${items.length} figures, each with n, interval, source and caveat`)
