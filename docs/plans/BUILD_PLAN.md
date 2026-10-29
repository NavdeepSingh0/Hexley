# Build plan: everything that remains (28 Oct 2026; supersedes the phase list in `FRONTEND_PLAN.md` and the frontend-related parts of `CORE_PLAN.md`)

Status: **draft for Navdeep's review, nothing in it is built yet.** Navdeep decided on 28 Oct 2026 not to plan around the clock: the full scope stays in, with the order below. Teammates are out; Navdeep and Claude build everything. Look and layouts: `docs/DESIGN_BRIEF.md`. Contracts, honesty rules and the common QA checklist in `FRONTEND_PLAN.md` still apply.

## Method (unchanged)
Each phase: goal, deliverables, QA checklist. **QA pass, then commit, then next phase.** QA fail: rework only what failed, QA again. **Three attempts per phase, then stop and discuss.** Every attempt is a row in `docs/PHASE_LOG.md`. Security core stays frozen except correctness fixes (D-040).

**Common QA (every UI phase):** dark and light theme; 1280x720 and 1920x1080 with nothing clipped; no horizontal scroll at 390 px; keyboard focus visible; every text pairing at least 4.5:1 (the contrast test reads the real token file); no external network request (DevTools network tab); honesty rules (no "100% secure", every number from `evidence.json` with its n and caveat, Tested / Should work / Planned labels, chat disclosure line, no OpenAI or Anthropic branding); the one-headline / one-line / one-action rule from the brief; `npm run build` and vitest pass; screenshots reviewed by looking at them.

## Order and dependencies
```
F0 tokens ──> F2 console ──────────────┐
   │                                   ├──> F8 integration ──> F9 rehearsal
   ├──> F1 mascot (needs the image) ───┤
   ├──> F3 site shell + home ──> F4 pages ──> F5 docs
   └──> F6 evidence + serving the site at /
F7 chat backend (B5) ──> F7b chat page        (independent of F2 to F5)
F7c blind red-team (B4): needs a person at the venue; can run any time after F6
```

## Phases

**F0 Tokens and primitives.** Rewrite `design/tokens.css` to the palette in the brief (dark default, light by toggle, glow and top-highlight utilities, three type sizes). Update `console/src/contrast.test.js` to the new values and pairings. Shared primitives used by both apps: Button (primary uses black text on the dark violet fill), Panel, Label, Verdict word, StatusBadge. QA: contrast test green against the real file; a `/styleguide` page showing every primitive in both themes (reviewed by screenshot).

**F1 Mascot. Done 28 Oct 2026** (see `docs/contracts/MASCOT.md` and the PHASE_LOG rows). Direction agreed 28 Oct 2026 from Navdeep's reference image: an original **rounded screen-cube robot** (Navdeep chose the cube over the retro monitor) drawn as an animated SVG (fluid motion; pixel sprite sheets dropped, see `docs/contracts/MASCOT.md`), badge = a small dark tile whose dot shows the decision colour; no caret mark. A first prototype of the nine states was drawn and looked over in both themes (the monitor version is in the scratchpad; the cube is redrawn in F1; the review caught one bug: eyes drawn in the page's ink colour vanished on the dark screen in the light theme; the screen now uses fixed bright colours). Remaining: (1) refine the drawing with Navdeep (face spacing, foot, the slot and light), (2) fluid transitions between states (an eased morph of the eyes rather than a cut, a squash when a decision lands, a settle back to idle), (3) `<sentinel-mascot>` Web Component per the contract (framework-free, speech bubble at most 90 characters, reduced motion respected, `speak` optional) and a `/mascot` dev page with a button per state, (4) tests: unknown state falls back to idle, message truncated, reduced motion stops animation. QA: all nine states legible at 48, 64 and 128 px on both themes; works in a plain HTML page; no red on the body; a screen recording of state changes reviewed; Navdeep approves the look before it goes into any screen.

**F2 Console redesign** (B6 redone). Top bar with logo, run, `[?]`, theme, mascot. Task line. Three lanes, each one verdict word, one sentence, counts, "Show steps". Right-hand drawer for the denied step (plain reason, highlighted value, chain, one-sentence rule). Officer approval modal with exactly what, to where, which data, Approve, Deny. Slip screen: task, allowed tools, where restricted data may go, limits, one confirm button. Presenter keys moved under `[?]`. Audit footer with Verify and Tamper. QA: common checklist; every screen from the existing flow (start, slip, stage, verdict, approval, quarantine, audit tamper) screenshotted in both themes at both sizes; the Enter / V / T / N keys exercised in a real browser (still never done); vitest updated, nothing deleted without a replacement.

**F3 Site shell and home. Done 28 Oct 2026** (see PHASE_LOG). Scaffold in `site/` exists from B0. Nav, footer, routes, theme toggle. Home: hero with one sentence and two buttons, the three-step story with real screenshots from F2, the evidence strip (placeholder until F6), the integrations strip, honest-limits link. QA: common checklist; no number typed by hand.

**F4 How it works, Integrations, Connect. Done 28 Oct 2026** (see PHASE_LOG, D-041). How it works: slip, rules in plain English (R1 to R7), audit, approval, quarantine, each with a real screenshot. Integrations: Tested (Claude.ai via OAuth, with its real screenshot), Should work, Planned; no screenshot for anything not tested. Connect: choose a client, then the method; OAuth path and header path; snippets; needs `GET /api/v1/connect` and the officer token endpoint from the contracts (backend work included in this phase if not already present, with tests). QA: common checklist; the connect flow works end to end against a running gateway.

**F5 Docs. Done 28 Oct 2026** (see PHASE_LOG). One page with a side index: getting started, concepts, connecting a client, your own tools, limits and honest scope (from README, THREAT_MODEL, D-0xx), judge FAQ. QA: every claim traceable to a doc or result file (Claude checks, Navdeep reviews); common checklist.

**F6 Evidence and serving. Done 29 Oct 2026** (see PHASE_LOG, D-042). `scripts/export_evidence.py` writes `site/public/evidence.json` from `eval/results/` (already written once by hand; becomes a script with a test; it must emit the `group`, `group_title` and `arm` fields the home page pairs on, see `site/src/lib/evidence.js`). Gateway serves `site/dist` at `/` with SPA fallback; FastAPI's own `/docs` page switched off; `up` opens `/`. QA: fresh clone, `up --demo`, home page renders with evidence from the file; test that the site build fails if a number is missing its n.

**F7 Chat backend (B5). Done 29 Oct 2026** (see PHASE_LOG, D-043; the chat page F7b and the blind red-team F7c remain). `chat.py` manager and `/api/v1/chat*` routes per the API contract; multi-turn agent runner with per-step callbacks; key failover across the NVIDIA keys (never logged); server-side mascot-state function; presets; record and replay of a chat as fallback. QA: tests with a fake model transport (scripted tool calls), 429 failover test, disclosure present, one live smoke conversation.
**F7b Chat page. Done 29 Oct 2026** (see PHASE_LOG). Slim preset list, wide message column, one-line action chips under assistant messages, mascot beside the composer, permanent disclosure line, slip card and officer confirm before the first message, approval card, quarantined state disables the composer, "model busy, retrying" state. QA: common checklist; a screenshot for each of clean, denied, needs-approval, quarantined and model-busy.
**F7c Blind red-team (B4).** Attack cards written by someone who has not read the rules (a mentor or participant at the venue), converted to eval cases with the author's "saw rules: yes/no"; results reported as "blind, n people, date" next to the informed ones. QA: every card converted or rejected with a written reason; result file with commit, n, date.

**F8 Integration.** Real-client matrix: Claude.ai free (OAuth, done once), Claude.ai Pro or Claude Code (header) if available; screenshots and statuses written into the connect data; every Tested label backed by a screenshot. Pricing page last, only if everything else passed: one section marked "Illustrative, not offered". Browser extension stays cut unless Navdeep reopens it. QA: fresh clone on unused ports runs the whole flow.

**F9 Rehearsal and fallback.** Three timed rehearsals of the five-minute flow with a stopwatch (site, See it work, three lanes, why denied, quarantine, approval, audit verify and tamper, your own task with the compromised PDF, real Claude.ai); a fix list; a screen-recorded fallback video; README and DECISIONS brought up to date; code freeze before judging.

## Open items that touch this plan
- Mascot reference image from Navdeep (blocks F1 only).
- Eval-fixture flake still unexplained (1 failure in 7 full-suite runs); if it recurs, read the fixture's own message from the full log.
- A larger live-model sample needs hosted-API quota; ask first.
- Four commits are not pushed; push only on Navdeep's word.
