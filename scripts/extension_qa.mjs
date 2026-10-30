// Drives the extension in real Chromium against a running Sentinel and checks what it does (overlay, approvals from the browser, the
// per-site switch, the local-address rule). It needs: a Chromium that accepts --load-extension (Playwright's build does; branded
// Chrome 137 and later ignores that flag), network access to claude.ai (the content script runs on its check page), and a Sentinel
// started as:  SENTINEL_API_TOKEN=ext-token python -m sentinel up --demo --no-browser --api-port 19930 --gateway-port 19931 --tools-port 19932
// Run:  CHROMIUM=<path to chrome.exe> node scripts/extension_qa.mjs
// It runs scripted chats only (no model, no key) and prints PASS or FAIL for each check.
import { spawn, execSync } from 'node:child_process'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const HERE = path.dirname(fileURLToPath(import.meta.url))
const CHROME = process.env.CHROMIUM
if (!CHROME) throw new Error('set CHROMIUM to the path of a Chromium that accepts --load-extension')
const EXT = path.resolve(HERE, '..', 'extension')
const API = process.env.SENTINEL_API || 'http://127.0.0.1:19930'
const TOKEN = process.env.SENTINEL_TOKEN_FOR_QA || 'ext-token'
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const WORK = fs.mkdtempSync(path.join(os.tmpdir(), 'sentinel-ext-qa-'))
const SHOTS = path.join(WORK, 'shots')
fs.mkdirSync(SHOTS, { recursive: true })
const results = {}
const check = (name, ok, detail = '') => { results[name] = { ok: Boolean(ok), detail }; console.error((ok ? 'PASS ' : 'FAIL ') + name + (detail ? '  ' + JSON.stringify(detail) : '')) }

async function sentinel(method, p, body) {
  const r = await fetch(API + p, { signal: AbortSignal.timeout(20000), method, headers: { Authorization: `Bearer ${TOKEN}`, 'Content-Type': 'application/json' }, body: body ? JSON.stringify(body) : undefined })
  const text = await r.text()
  return { status: r.status, json: text ? JSON.parse(text) : {} }
}
async function chat(preset, text) {
  const v = (await sentinel('POST', '/api/v1/chat', { preset, mode: 'scripted' })).json
  await sentinel('POST', `/api/v1/chat/${v.chat_id}/confirm`)
  await sentinel('POST', `/api/v1/chat/${v.chat_id}/messages`, { text })
  return v.chat_id
}

const port = 9350
const profile = path.join(WORK, 'profile')
fs.rmSync(profile, { recursive: true, force: true })
fs.mkdirSync(profile, { recursive: true })
const proc = spawn(CHROME, ['--headless=new', '--disable-gpu', `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`, `--disable-extensions-except=${EXT}`, `--load-extension=${EXT}`, '--no-first-run', 'about:blank'], { stdio: 'ignore' })
let v
for (let i = 0; i < 60; i++) { try { v = await (await fetch(`http://127.0.0.1:${port}/json/version`)).json(); break } catch { await sleep(250) } }
const ws = new WebSocket(v.webSocketDebuggerUrl)
await new Promise((res) => { ws.onopen = res })
let id = 0
const pend = new Map()
ws.onmessage = (m) => { const d = JSON.parse(m.data); if (d.id && pend.has(d.id)) { pend.get(d.id)(d); pend.delete(d.id) } }
const send = (method, params = {}, sessionId) => new Promise((res) => { const i = ++id; pend.set(i, res); ws.send(JSON.stringify({ id: i, method, params, ...(sessionId ? { sessionId } : {}) })) })
const targets = async () => (await send('Target.getTargets')).result.targetInfos
const attach = async (targetId) => (await send('Target.attachToTarget', { targetId, flatten: true })).result.sessionId
const evalIn = async (sessionId, expression) => {
  const r = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true }, sessionId)
  return r.result?.exceptionDetails ? { error: r.result.exceptionDetails.exception?.description } : r.result?.result?.value
}
const waitIn = async (sessionId, expr, ms = 10000) => { const t0 = Date.now(); while (Date.now() - t0 < ms) { if (await evalIn(sessionId, `Boolean(${expr})`)) return true; await sleep(250) } return false }

try {
  let opt
  for (let i = 0; i < 40 && !opt; i++) { opt = (await targets()).find((t) => t.url.endsWith('/options.html')); if (!opt) await sleep(250) }
  check('extension loads and opens its options page', Boolean(opt))
  const extId = opt.url.split('/')[2]
  const optS = await attach(opt.targetId)
  await send('Runtime.evaluate', { expression: `chrome.storage.session.set({sentinelBase:'${API}', token:'${TOKEN}'})`, awaitPromise: true }, optS)

  // ---- the page, with the content script -------------------------------------------------------------------------------------
  const pageTarget = (await send('Target.createTarget', { url: 'https://claude.ai/login' })).result.targetId
  const page = await attach(pageTarget)
  await send('Emulation.setDeviceMetricsOverride', { width: 1100, height: 700, deviceScaleFactor: 1, mobile: false }, page)
  check('overlay is injected on the page', await waitIn(page, `document.getElementById('sentinel-ext-host')`, 20000))
  let frame
  for (let i = 0; i < 40 && !frame; i++) { frame = (await targets()).find((t) => t.type === 'iframe' && t.url.includes('overlay.html')); if (!frame) await sleep(250) }
  const ov = await attach(frame.targetId)
  await waitIn(ov, `document.getElementById('mascot')`)
  const h0 = await evalIn(ov, 'window.innerHeight')
  check('the frame starts at 260 px tall', h0 === 260, h0)

  // ---- a held action, then Review ---------------------------------------------------------------------------------------------
  const chatId = await chat('bank-change', 'Update the vendor bank details')
  check('needs-approval reaches the overlay', await waitIn(ov, `document.getElementById('mascot').getAttribute('state')==='needs-approval'`, 15000))
  await evalIn(ov, `document.getElementById('review-btn').click()`)
  await sleep(1500)
  const h1 = await evalIn(ov, 'window.innerHeight')
  const top = await evalIn(ov, `document.querySelector('#approval-panel h3').getBoundingClientRect().top`)
  check('the frame grows when the approval panel opens', h1 > 260, { before: h0, after: h1 })
  check('the panel heading is inside the frame (not clipped)', top >= 0, { heading_top: top })
  check('the panel shows the tool and the arguments', (await evalIn(ov, `document.getElementById('approval-tool').textContent`)) === 'update_vendor_bank')
  await send('Page.bringToFront', {}, page)
  await sleep(500)
  fs.writeFileSync(path.join(SHOTS, 'review_open.png'), Buffer.from((await send('Page.captureScreenshot', { format: 'png' }, page)).result.data, 'base64'))

  // ---- a script on the page cannot resize the frame ----------------------------------------------------------------------------
  await evalIn(page, `window.postMessage({source:'sentinel-overlay', type:'resize', width:1, height:99999}, '*')`)
  await sleep(600)
  check('a message from the page itself is ignored', (await evalIn(ov, 'window.innerHeight')) === h1, await evalIn(ov, 'window.innerHeight'))

  // ---- approve from the browser ------------------------------------------------------------------------------------------------
  await evalIn(ov, `document.getElementById('approve-btn').click()`)
  await sleep(400)
  await evalIn(ov, `document.getElementById('approve-btn').click()`)
  await sleep(3000)
  const pending = (await sentinel('GET', '/approvals')).json.pending
  check('Approve in the browser resolves the held action', pending.length === 0 && (await sentinel('GET', `/api/v1/chat/${chatId}`)).json.status === 'ready',
    { pending: pending.length, chat: (await sentinel('GET', `/api/v1/chat/${chatId}`)).json.status })
  check('the frame shrinks back when the panel closes', (await evalIn(ov, 'window.innerHeight')) === 260, await evalIn(ov, 'window.innerHeight'))

  // ---- the popup's switch for this site -----------------------------------------------------------------------------------------
  await send('Runtime.evaluate', { expression: `chrome.storage.local.set({showClaude:false})`, awaitPromise: true }, optS)
  let gone = false
  for (let i = 0; i < 12 && !gone; i++) { gone = !(await evalIn(page, `Boolean(document.getElementById('sentinel-ext-host'))`)); if (!gone) await sleep(250) }
  check('switching the site off removes the overlay at once', gone)
  await send('Runtime.evaluate', { expression: `chrome.storage.local.set({showClaude:true})`, awaitPromise: true }, optS)
  check('switching it on puts it back (once)', await waitIn(page, `document.querySelectorAll('#sentinel-ext-host').length === 1`, 5000))

  // ---- the options page refuses an address that is not this computer ------------------------------------------------------------
  const opt2 = (await send('Target.createTarget', { url: `chrome-extension://${extId}/options.html` })).result.targetId
  const o2 = await attach(opt2)
  await sleep(1200)
  await evalIn(o2, `(() => { const i = document.getElementById('full-link'); i.value = 'https://evil.example/#token=stolen'; i.dispatchEvent(new Event('input')); document.getElementById('save-btn').click() })()`)
  await sleep(1500)
  const status = await evalIn(o2, `document.getElementById('status').textContent`)
  const stored = await evalIn(o2, `chrome.storage.session.get(['sentinelBase','token']).then(s => JSON.stringify(s))`)
  check('an address that is not this computer is refused', /on this computer/.test(status), status)
  check('and the stored address and token are unchanged', stored.includes(API) && !stored.includes('stolen'), stored.replace(TOKEN, '<token>'))
} catch (e) {
  check('script ran to the end', false, String(e && e.stack || e))
} finally {
  try { ws.close() } catch { /* */ }
  try { execSync(`taskkill /pid ${proc.pid} /T /F`, { stdio: 'ignore' }) } catch { /* */ }
}
fs.writeFileSync(path.join(WORK, 'results.json'), JSON.stringify(results, null, 1))
console.log('screenshots and results in ' + WORK)
const failed = Object.entries(results).filter(([, r]) => !r.ok)
console.log(failed.length ? `FAILED: ${failed.map(([k]) => k).join('; ')}` : `ALL ${Object.keys(results).length} CHECKS PASSED`)
