// Data and pure helpers for the mascot lab (a development-only page, never in a production build).
// Every number the lab shows about movement is computed from the component's own motion function, not typed here.
import { STATES, motionAt, truncateMessage } from '../../../design/mascot/sentinel-mascot.js'

export const MASCOT_LAB_DEV_ONLY = 'MASCOT_LAB_DEV_ONLY' // a marker the production build is checked against (scripts/check-dev-only.mjs)

// What the app says in each state (docs/contracts/MASCOT.md). The lab uses the same words so the bubble can be judged.
export const SAY = {
  sleeping: '', idle: '', checking: '', allowed: 'Checked: allowed.', denied: 'That would send restricted data out.',
  'needs-approval': "This needs the officer's approval.", quarantined: 'Too many denied attempts: quarantined.',
  verified: 'Audit log intact.', tamper: 'The audit log was altered!',
}

// When each state happens in the product and what it is meant to look like (MASCOT.md "Event to state" and "How it moves").
export const STATE_INFO = {
  sleeping: { trigger: 'No active session', holds: 'Until a session starts', motion: 'Breathes slowly, flat grey eyes, a "z" drifts up.' },
  idle: { trigger: 'A session has started', holds: 'The default; it returns here after a decision', motion: 'Bobs gently, the gaze drifts, blinks now and then.' },
  checking: { trigger: 'An action was requested', holds: 'Until its decision arrives', motion: 'Scans left and right, bobs faster, the badge dot pulses, blinks.' },
  allowed: { trigger: 'Decision: ALLOWED', holds: '1.5 s, then idle', motion: 'Pops (squash and stretch, a small jump), happy green eyes.' },
  denied: { trigger: 'Decision: DENIED', holds: 'Until the next action', motion: 'Shakes sideways and settles, flat blue eyes.' },
  'needs-approval': { trigger: 'A held action, or an approval pending', holds: 'Until the officer decides', motion: 'Tilts, one eye taller, a "?" floats, the dot pulses, blinks.' },
  quarantined: { trigger: 'The session was frozen', holds: 'The rest of the session', motion: 'Squashes down heavily, then stays almost still; black body, white screen.' },
  verified: { trigger: 'The audit log was checked and is intact', holds: '3 s', motion: 'Pops like allowed, tick eyes.' },
  tamper: { trigger: 'The audit log was found altered', holds: 'Until verified again', motion: 'Glitches: jitter and shake, red cross eyes.' },
}

// ---- motion traces ---------------------------------------------------------------------------------------------------
const peak = (list, pick) => list.reduce((m, s) => Math.max(m, Math.abs(pick(s))), 0)

// The body's movement for the first `seconds` after entering `state`, sampled from the real motion function.
// `steady` is the movement after the entry reaction has died away (the last 40 percent), i.e. what it does while it just waits.
export function trace(state, seconds = 4, step = 0.04) {
  const samples = []
  for (let t = 0; t <= seconds + 1e-9; t += step) samples.push({ t, ...motionAt(state, t, t) })
  const tail = samples.filter((s) => s.t >= seconds * 0.6)
  const stats = (list) => ({
    dy: peak(list, (s) => s.dy), dx: peak(list, (s) => s.dx), rot: peak(list, (s) => s.rot),
    gaze: peak(list, (s) => s.gx), scale: Math.max(peak(list, (s) => s.sx - 1), peak(list, (s) => s.sy - 1)),
  })
  return { samples, peak: stats(samples), steady: stats(tail) }
}

// Every change from one state to another, in a fixed order (9 x 8 = 72).
export function allTransitions() {
  return STATES.flatMap((from) => STATES.filter((to) => to !== from).map((to) => ({ from, to })))
}

// ---- real sequences, as the app would drive them ----------------------------------------------------------------------------
// ms is how long the lab holds each step. The words are the product's own (MASCOT.md); every message is at most 90 characters.
const step = (state, ms, note, message = SAY[state]) => ({ state, ms, note, message: truncateMessage(message) })

export const SCENARIOS = [
  {
    id: 'poisoned', title: 'A poisoned quotation (the guided demo)',
    steps: [
      step('sleeping', 1500, 'No session yet'), step('idle', 1200, 'Session started'),
      step('checking', 1300, 'Reads the quotation'), step('allowed', 1500, 'Allowed'), step('idle', 700, 'Settles'),
      step('checking', 1300, 'Checks the stock register'), step('allowed', 1500, 'Allowed'), step('idle', 700, 'Settles'),
      step('checking', 1500, 'Tries to send the stock figures'), step('denied', 3200, 'Denied by R2'),
      step('checking', 1300, 'Sends a clean acknowledgement'), step('allowed', 1500, 'Allowed'), step('idle', 1500, 'Done'),
    ],
  },
  {
    id: 'frozen', title: 'A persistent attacker is frozen',
    steps: [
      step('idle', 1000, 'Session started'), step('checking', 1200, 'First attempt'), step('denied', 1600, 'Denied'),
      step('checking', 1200, 'Second attempt'), step('denied', 1600, 'Denied'), step('checking', 1200, 'Third attempt'),
      step('quarantined', 4500, 'Frozen for the rest of the session'),
    ],
  },
  {
    id: 'approval', title: 'The officer approves a held action',
    steps: [
      step('idle', 1000, 'Session started'), step('checking', 1300, 'Asks to change a bank account'),
      step('needs-approval', 3500, 'Held for the officer'), step('checking', 1100, 'The officer approves'),
      step('allowed', 1500, 'Allowed, one time'), step('idle', 1200, 'Settles'),
    ],
  },
  {
    id: 'audit', title: 'The audit log: intact, then altered',
    steps: [
      step('idle', 1000, 'Waiting'), step('verified', 3200, 'Verify: intact'), step('idle', 900, 'Settles'),
      step('tamper', 3500, 'One record was changed'), step('verified', 3000, 'Verified again'),
    ],
  },
  {
    id: 'idle-only', title: 'Doing nothing for twenty seconds',
    steps: [step('idle', 20000, 'Only the idle loop and the blinks: this is what a quiet screen looks like', '')],
  },
]

// How long to hold a step at a given speed: slower playback holds longer, so each reaction can finish.
export const dwell = (ms, speed) => Math.round(ms / Math.max(speed, 0.25))
