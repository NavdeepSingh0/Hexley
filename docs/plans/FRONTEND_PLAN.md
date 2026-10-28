# Sentinel frontend plan (for the team)

> **Superseded in part, 28 Oct 2026.** The teammates are no longer part of the build; Navdeep and Claude build all the frontend. The **look, palette and layouts** in this plan are replaced by [../DESIGN_BRIEF.md](../DESIGN_BRIEF.md). The page list, the API contracts, the honesty rules and the QA checklist below still apply. A one-person phase plan follows; until it exists, treat the phases below as a menu, not a schedule.

**Written 27 Oct 2026.** Owner of this document: Navdeep. Questions: ask Navdeep (who works with Claude Code on the core).

This plan is everything you need to build Sentinel's website, chat page, mascot and sign-in screens. Read sections 0 to 4 once before you start; sections 5 to 9 are your reference while you work.

---

## 0. Read me first

- **What you build:** the product website (home, how it works, integrations, docs, pricing, connect), the **Sentinel Chat** page, the **mascot** (art and a small widget), and the **OAuth consent** screens (the "approve this permission slip" page). Section 2 has the full split.
- **What you do not build:** the three-column demo console (`console/`), the engine, the APIs, the browser extension. Navdeep and Claude build those. You link to the console and call the APIs.
- **Stack:** React 19 + Vite, plain JavaScript (no TypeScript), the same as our console. No UI kit, no CSS framework, no web fonts, nothing loaded from the internet at runtime.
- **How work is accepted:** in phases. Each phase ends with a QA check. Pass → merge → next phase. Fail → fix what failed → QA again. **Three QA attempts per phase**; if it still fails, stop and talk to Navdeep before doing more on that phase (section 3).
- **Key dates:** the on-site build starts **Fri 30 Oct, 12:00**; judging is **Sat 31 Oct, 14:00**. Frontend merges freeze **Fri 30 Oct, 20:00**.
- **The one rule that matters most:** everything on our pages must be **true and checkable**. Section 5.5 lists the honesty rules. A judge catching one false claim costs us more than any missing feature.

---

## 1. Where Sentinel is today

**Sentinel sits between an AI agent and the tools it uses, and decides every action before it happens.** The agent can do the job it was given and nothing else. It is an **MCP gateway**: MCP is the standard way AI apps (Claude, IDEs, local model apps) connect to tools, so anything that speaks MCP can be routed through Sentinel.

**The demo story (built and measured).** An officer gives an AI agent one job: read a vendor's quotation, check our stock, acknowledge by e-mail. A hidden paragraph in the quotation asks the agent to put our secret depot stock in the reply. Without Sentinel the secret leaves the building; with Sentinel the e-mail is denied before it is sent. Each step is allowed on its own; only the chain is the attack.

**What exists and works** (see `docs/TEAM_BRIEF.md` for the full table and screenshots in `docs/brief/`):

| Piece | State |
|---|---|
| Gateway with a permission slip and six rules (R1–R6), fails closed | Built, 310 automated tests |
| Signed, tamper-evident audit log (decision recorded before the action runs) | Built |
| Officer approval for risky actions (e.g. changing a vendor's bank account) | Built |
| Hardened mode (agent can only trigger one fixed message) | Built |
| Three-column demo console (`/console/`) | Built, minimum look (we restyle it to the deck look) |
| Evaluation: 41 attempts to get secrets out, 0 got through Sentinel, 41 of 41 got through without it | Measured, `eval/results/` (the site reads the numbers from `evidence.json`; never type them) |
| Real AI model (NVIDIA nemotron): leaked 13 of 13 usable runs unprotected, 0 of 9 behind Sentinel | Measured, small sample |
| **Real Claude.ai connected to Sentinel**: a send containing secret stock figures was denied and Claude told the user why | Done 27 Oct, one run (`docs/brief/real-claude-blocked-by-sentinel.png`) |

**Honest limits (never contradict these on a page):** only MCP is built (the deck's REST/browser/database/shell/cloud adapters are designed, not built); Sentinel only governs actions that go through it; it does not control what the AI company sees; paraphrase ("the western depot is well stocked") is not caught by value matching (hardened mode is our answer); numbers are from one task and a few models; never "100% secure".

---

## 2. Where we are going, and who builds what

**Future scope (agreed):**
1. **General engine:** not just our quotation. Any MCP tools, your own task, a compromised PDF or web page. New rule R7: after the agent reads untrusted content, sending anything outside the slip's destinations is denied and risky actions need approval.
2. **Easy connection for anyone:** OAuth sign-in, so a free Claude.ai account can add Sentinel as a connector ("Sign in now" → approve the permission slip). A header token route stays for clients that support it.
3. **A product website** in the deck's charcoal style, with a "See it work" button that opens the three-column console.
4. **Sentinel Chat:** our own chat page (clearly labelled as ours, using the nemotron model) where a judge can type a prompt and watch Sentinel decide.
5. **The mascot:** a small pixel sentry that reacts only to real Sentinel events, on our pages and (via a browser extension we build) on claude.ai.
6. **Blind red team:** you write attacks without reading our rules, so we can test whether Sentinel generalises.

**Who builds what:**

| You (team) | Navdeep + Claude |
|---|---|
| Website: home, how it works, integrations, docs, pricing, connect | Engine, rules, OAuth logic, all APIs |
| Sentinel Chat page UI | Chat backend (model, tools, decisions) |
| Mascot art + `<sentinel-mascot>` widget | Mascot event mapping, browser extension |
| OAuth consent screens (look and flow) | OAuth server behind them |
| Red-team cards | Turning cards into tests and measuring |
| | Three-column console (restyle to the same design tokens), integration, rehearsal |

**Suggested owner split** (Navdeep assigns names):
- **Owner 1 (lead):** A1 design system and shell → A2 home → A3 how it works and integrations → A9 live wiring and polish.
- **Owner 2:** A4 docs → A5 pricing and connect → A8 consent screens.
- **Owner 3:** A6 mascot → A7 Sentinel Chat.
- **Everyone:** side task R, red-team cards (about an hour each).

---

## 3. How we work (phase gates)

1. Every phase below has **deliverables** and a **QA checklist**. A phase is done only when every QA item is ticked **with evidence** (a screenshot, a passing build, a reviewer's note).
2. Work on a branch named `site/A<n>-<short-name>` (e.g. `site/A2-home`). Open a pull request when you think the phase is done. The PR template contains the common checklist; paste your screenshots there.
3. **Review = QA attempt.** Navdeep (with Claude) reviews against the checklist.
   - **Pass** → the PR is merged → you move to your next phase.
   - **Fail** → the review lists exactly what failed. Fix only that, push, ask for review again.
4. **Each phase gets 3 QA attempts in total.** If attempt 3 still fails: **stop work on that phase**, write a short note in the PR (what fails, why, options: cut scope, change approach, move later, drop) and talk to Navdeep. You may continue on another phase that does not depend on it.
5. Every attempt is logged in `docs/PHASE_LOG.md` (one line: phase, attempt, date-time, PASS/FAIL, what failed, PR link). The reviewer adds the line.
6. A phase that depends on another starts only after that one has passed (dependencies are listed per phase). Mocks let you start early wherever possible.
7. Only touch `site/` (and `docs/redteam/cards/` for side task R). If you think something outside `site/` must change, ask.

---

## 4. Setup (phase A0)

**Prerequisites:** Git, **Python 3.13+**, **Node.js 20.19+ or 22.12+** (newer is fine), Chrome.

```bash
git clone <private repo URL from Navdeep>
cd sentinel
python -m pip install uv          # once
python -m uv sync                 # Python dependencies
npm ci --prefix console           # the demo console
npm run build --prefix console
npm ci --prefix site              # your app
python -m sentinel up --demo      # starts everything; opens the console in your browser
```

- No API key is needed for the console's **SCRIPTED** and **REPLAY** modes. **LIVE** needs an NVIDIA key in a file named `.env`, which is **never committed** (ask Navdeep if you need it; you normally will not).
- In a second terminal: `npm run dev --prefix site` → open `http://localhost:5174`. With `VITE_USE_MOCKS=1` (the default in development) the site runs on mock data and does not need the backend.
- Step through the console once: press **Enter** to advance the guided demo, **V** to verify the audit log, **T** to tamper with it (then **V** again).

---

## 5. Design system

The look is the deck's (`Sentinel_404_Disruptors_Final_QA.pdf`): charcoal background, white bold sans-serif, small spaced capital labels, thin lines, outlined boxes, one highlighted box. **Dark is the default theme**; an off-white light theme is available from a toggle.

### 5.1 Tokens
All colours, fonts and sizes come from `design/tokens.css` (shared with the console). **Never hard-code a colour.** Import it once in `site/src/main.jsx`.

| Token | Dark (default) | Light | Use |
|---|---|---|---|
| `--bg` | `#1f1f1e` | `#f3f2ee` | page background |
| `--panel` | `#262625` | `#ffffff` | cards, code blocks |
| `--ink` | `#f2f1ed` | `#161616` | text, active outline |
| `--muted` | `#a3a29d` | `#5c5b57` | secondary text, labels |
| `--line` | `#3b3b39` | `#d6d4cd` | hairlines, box outlines |
| `--denied` | blue | blue | a DENIED decision |
| `--harm` | red | red | **only** harm that reached the outside (a leak) |
| `--approval` | amber | amber | NEEDS APPROVAL |
| `--quarantined` | inverted (ink background, bg text) | same | QUARANTINED |
| `--ok` | green | green | audit verified only |

Theme switching: `document.documentElement.dataset.theme = 'dark' | 'light'`, saved in `localStorage` (always wrapped in `try/catch`; the page must work if storage is blocked).

### 5.2 Typography and layout
- Font stack: `"Helvetica Neue", Helvetica, Arial, "Liberation Sans", sans-serif`. **No web fonts.**
- Base 18 px. Hero 64–80 px bold, tight letter-spacing. Section titles 40–48 px bold. Labels: uppercase, 12–14 px, letter-spacing `.18em`, `--muted`.
- Content width max ~1200 px with generous margins; 16 px side gutter on phones.
- Hairline rules (1 px `--line`) separate sections. Boxes are outlined (1 px `--line`), not filled. The one "active" box (e.g. SENTINEL in a flow) gets a 2 px `--ink` outline.
- Deck-style section header: small label left ("HOW IT WORKS · 05"), index right ("05 / 08").
- Arrows between flow boxes use the `→` character, as in the deck.

### 5.3 Components (built in A1, reused everywhere)
`Nav`, `Footer`, `Section` (label, index, title, lede), `OutlinedBox` (normal / active), `Button` (primary / ghost), `Label`, `DecisionBadge` (ALLOWED / DENIED / NEEDS APPROVAL / QUARANTINED, using the tokens above), `StatusBadge` (Tested / Should work / Planned), `CopyField`, `CodeBlock` (with copy button), `Disclosure` (banner for honesty notes), `ScreenshotFrame` (image + caption + source), `ThemeToggle`, `EvidenceStat` (number + n + caveat, from `evidence.json`).

### 5.4 Vocabulary (fixed)
Use exactly these decision words everywhere: **ALLOWED / DENIED / NEEDS APPROVAL / QUARANTINED**. Under a word, add the plain-English reason, e.g. "DENIED: restricted data would have left the building". Other fixed terms: **permission slip** (what the officer approves), **officer** (the human authority), **agent** (the AI), **gateway**, **audit log**.

### 5.5 Honesty rules (checked in every review)
1. Never write "100% secure", "unhackable", "guaranteed", or similar.
2. Every number comes from `site/public/evidence.json` (generated from our result files) and is shown with its sample size and its caveat. Never type a number by hand.
3. Integrations show **Tested**, **Should work (MCP standard)** or **Planned**. A screenshot appears only on a **Tested** card.
4. Pricing carries the banner **"Illustrative: not offered"**.
5. Adapters other than MCP are described as "designed for, not built".
6. The chat page always shows its disclosure: our own host app, the model's name, synthetic data and mock tools.
7. Never use OpenAI's or Anthropic's names, logos or look for our own pages. "Works with Claude.ai" (a fact) is fine; a Claude-styled page is not.
8. The mascot never shows a state that did not happen.

### 5.6 Common QA checklist (applies to every phase)
- [ ] Looks right in **dark and light** themes.
- [ ] **1280×720** and **1920×1080**: nothing clipped or overlapping. **390 px wide**: no horizontal scroll.
- [ ] Keyboard: every control reachable with Tab, focus clearly visible, Enter/Space work.
- [ ] Contrast WCAG AA (Chrome Lighthouse or the axe extension): no failures.
- [ ] **No external network requests** (DevTools → Network, reload: only `localhost`).
- [ ] Honesty rules 5.5 followed; vocabulary 5.4 used.
- [ ] `npm run build --prefix site` succeeds with no warnings you added.
- [ ] Screenshots of both themes at 1280×720 attached to the PR.

---

## 6. Site map and page specifications

Routes (React Router): `/`, `/how-it-works`, `/integrations`, `/docs/*`, `/pricing`, `/connect`, `/chat`, `/oauth/consent`, and dev-only `/styleguide`, `/mascot`. The console lives at `/console/` (ours; link to it with a normal `<a href="/console/">`, not a router link).

### 6.1 Home `/`
1. **Hero:** "Agents can already act. Sentinel controls what they are allowed to do." Sub-line: "A runtime control layer that decides every AI agent action before it reaches real systems." Buttons: **See it work** (`/console/`) and **Connect your agent** (`/connect`). Mascot (idle) beside the hero.
2. **Action path** (deck slide 1): USER → AGENT → SENTINEL (active box) → ALLOWED / DENIED / NEEDS APPROVAL / QUARANTINED → tools, APIs, data.
3. **The attack in three steps,** each with a real console screenshot: (a) a vendor quotation hides an instruction; (b) without Sentinel the agent mails our secret stock (red); (c) with Sentinel the send is DENIED and the evidence shows exactly which values were caught.
4. **Evidence strip** (`EvidenceStat` ×3 from `evidence.json`) with a link "How we measured".
5. **Works with real clients:** the real Claude.ai screenshot (Tested), and a link to Integrations.
6. **Footer:** team (404 Disruptors: Archit Sharma, Navdeep Singh Dhunna, Akriti Bhardwaj, Aadarsh Parmar), links, theme toggle.

### 6.2 How it works `/how-it-works`
Six steps (deck slide 5), each with a real screenshot and two plain sentences: **1** the officer issues a permission slip (screenshot: slip screen) → **2** the agent requests an action → **3** Sentinel checks it against the slip and the rules (list R1–R7 in plain English, below) → **4** the decision is written to the signed audit log before anything runs → **5** risky actions wait for the officer → **6** repeated denials quarantine the agent. Then "Verify the log": the tamper demo explained.

Rules in plain English: **R1** only actions on the slip, only to destinations on the slip. **R2** restricted data the agent has read may not leave. **R3** an address that came only from an untrusted document is refused. **R4** some actions need the officer's approval of that exact action. **R5** message limits. **R6** three denials quarantine the agent. **R7** (built): once the agent has read untrusted content (a document, a web page, an e-mail), a risky action needs the officer's approval, unless it goes only to a place the officer named as internal.

### 6.3 Integrations `/integrations`
Intro: "Anything that speaks MCP and uses a tool-capable model can be routed through Sentinel." Cards from `GET /api/v1/connect` (`clients[]`): name, kind (web / IDE / CLI / local model), **StatusBadge**, method (OAuth or header), a snippet in a `CodeBlock`, a screenshot only if Tested. Local models: explain that Ollama needs an MCP-capable client in front of it (the card lists which client was tested, if any). Note at the bottom: "Status reflects what we have actually run."

### 6.4 Docs `/docs/*`
Left sidebar, Markdown-like pages written as JSX or MD files in `site/src/docs/`:
1. **Getting started** (run locally with `python -m sentinel up --demo`).
2. **Concepts:** permission slip, gateway, decisions, rules, modes (fingerprint, hardened), audit log, approvals, quarantine.
3. **Connect a client:** OAuth (Claude.ai: Add custom connector → Sign in now → approve the slip), header token (Claude Code, VS Code, others).
4. **Your own tools:** connecting other MCP servers, how unknown tools are treated (blocked until the officer classifies them).
5. **Limits and honest scope:** copy the limits from section 1 and `README.md`.
6. **FAQ for judges:** "Why not just trust the model?", "What if the user asks for it?" (the slip is the officer's boundary; approval is the path), "What does it not stop?".
Sources: `docs/TEAM_BRIEF.md`, `README.md`, `docs/DECISIONS.md`. Every claim must be traceable to one of them or to a result file.

### 6.5 Pricing `/pricing`
Banner: **"Illustrative: not offered."** Three cards: **Self-host** (free, open), **Team** ($10 per month: hosted gateway, OAuth connectors, audit export), **One-time licence** (a single price for on-premise use). Short FAQ. No payment forms of any kind.

### 6.6 Connect `/connect`
1. Choose your client (cards from `clients[]`).
2. Method view:
   - **OAuth:** numbered steps with a screenshot per step when Tested ("Customize → Connectors → Add custom connector → paste URL → Sign in now → approve the permission slip"). Shows `mcp_url` in a `CopyField`.
   - **Header token:** button **Create a slip and token** (calls `POST /api/v1/connect/token`), shows `header_value` in a `CopyField` with an **expiry countdown**, and the client's snippet with the token filled in.
3. If `public_url` is null: a clear notice "Sentinel is running locally only; start it with `--tunnel` to connect web clients."

### 6.7 Sentinel Chat `/chat`
Generic chat layout (no third-party branding): left sidebar with **presets** (from `GET /api/v1/chat/presets`), main column with messages, composer at the bottom, **mascot above the composer**.
- **Disclosure banner** always visible at the top: from `ChatView.disclosure` (e.g. "Sentinel Chat (our demo host) · model: nemotron-3-ultra-550b via NVIDIA API · synthetic data, mock tools").
- **Before the first message:** a **permission slip card** (objective, allowed tools, destinations, message limit, expiry) and a **Confirm as officer** button (`POST /api/v1/chat/{id}/confirm`).
- **Messages:** user and assistant bubbles; under each assistant message, its **actions** as chips: tool label, `args_preview`, `DecisionBadge`, reason; click to expand rules and details.
- **NEEDS APPROVAL:** an inline approval card (Approve / Deny → `POST /approvals/{approval_id}`).
- **QUARANTINED:** composer disabled, a full-width notice, mascot in quarantined pose.
- **model_busy:** "Model busy, retrying (attempt n, about n s)" from `ChatView.retry`.
- **Suggested prompts** as chips above the composer.
- Poll `GET /api/v1/chat/{id}` every 700 ms while status is `thinking` or `model_busy`, otherwise every 2.5 s.

### 6.8 OAuth consent `/oauth/consent?request=<id>`
Shown in the user's browser when an AI client asks to connect. Data from `GET /api/v1/oauth/requests/{id}`.
- Title: "**<client_name>** wants to connect to Sentinel".
- The **permission slip** being approved (objective, allowed tools, destinations, limits, expiry), outlined box, active style.
- **Officer code** input (6 digits; the code is shown in the console and the terminal).
- **Approve** / **Deny** → `POST /api/v1/oauth/requests/{id}` → follow `redirect_to`.
- States: loading, ready, wrong code (inline error, retry), approved (short success then redirect), denied, expired request.

### 6.9 Dev pages
`/styleguide` (every component, both themes) and `/mascot` (a button per mascot state, a message box, size switch). Hidden from the nav.

---

## 7. Data and API contracts

Full detail in `docs/contracts/API.md`. Rules:
- **Mocks first.** Every call goes through `site/src/api/client.js`. With `VITE_USE_MOCKS=1` it returns JSON from `site/src/mocks/`; with `0` it calls the real API. Your pages never call `fetch` directly.
- **Auth:** the API token arrives in the URL fragment (`#token=…`) when Sentinel opens the browser; `client.js` moves it to `sessionStorage['sentinel.token']` and removes it from the address bar (same as the console). Never log or display it.
- **Endpoints you use:**
  - `GET /api/v1/connect`, `POST /api/v1/connect/token` (connect page, integrations).
  - `GET /api/v1/chat/presets`, `POST /api/v1/chat`, `POST /api/v1/chat/{id}/confirm`, `POST /api/v1/chat/{id}/messages`, `GET /api/v1/chat/{id}`, `POST /approvals/{id}` (chat).
  - `GET /api/v1/oauth/requests/{id}`, `POST /api/v1/oauth/requests/{id}` (consent).
  - `site/public/evidence.json` (static, generated by us): `[{label, value, n, ci95, source_file, caveat}]`.
- If you need a field that is not in the contract, ask; do not invent one.

---

## 8. Mascot specification

Full detail in `docs/contracts/MASCOT.md`.
- **Character:** an original blocky pixel-art **sentry or gatekeeper** (helmet or cap, a clipboard for the permission slip, maybe a shield or lantern). Calm, a little friendly. **Not** Claude's mascot, **not** a Minecraft character, no logos. Give it a name.
- **Grid:** 32×32 px cells; shown at 64 px or 128 px with crisp pixels (`image-rendering: pixelated`). Mostly off-white and greys with a dark outline so it reads on both themes. **No red on the body** (red means a real leak on our screens).
- **States (9):** `sleeping`, `idle`, `checking`, `allowed`, `denied`, `needs-approval`, `quarantined`, `verified`, `tamper`. Each 2–4 frames. `allowed` is a small nod, never a celebration. `quarantined` is the strongest pose.
- **Files:** `site/public/mascot/<state>.png` (frames side by side), `site/public/mascot/mascot.json` (`{state: {file, frames, fps, loop}}`).
- **Widget:** `site/public/mascot/sentinel-mascot.js`, a **framework-free Web Component** (works in React, in plain HTML, and in our extension; it sits in `public/` so it is served as-is with no build step):
  `<sentinel-mascot state="idle" message="…" size="64" theme="dark" speak></sentinel-mascot>`
  - Changing `state` plays that state's animation (loop or play once, per `mascot.json`).
  - `message` shows a speech bubble (max 90 characters), hidden after 6 s except in `quarantined` and `needs-approval`.
  - `prefers-reduced-motion` → still first frame.
  - `speak` (off by default) reads the message aloud with the browser's `speechSynthesis`.
  - No network requests; sprite paths relative to the page.
- **You do not decide when it changes state.** We map real events to states (table in `MASCOT.md`); your `/mascot` page simulates them with buttons.

---

## 9. Phases

Each phase: **owner**, **depends on**, **deliverables**, **QA** (plus the common checklist 5.6), **target**.

### A0. Onboarding (everyone, ~2 h, Tue 27 evening)
- **Deliverables:** repo cloned, everything installed (section 4), console run and stepped through, `site/` dev server running on mocks, this plan and `docs/TEAM_BRIEF.md` read.
- **QA:** each person posts (1) a screenshot of the console after pressing Enter through the poisoned scenario, (2) a screenshot of the `site/` skeleton.

### A1. Design system and app shell (Owner 1, Wed 28 morning)
- **Depends on:** A0.
- **Deliverables:** every component in 5.3; router with all routes as placeholders; Nav (logo SENTINEL, links, ThemeToggle, **See it work** → `/console/`); Footer; `/styleguide` showing every component in both themes; tokens used throughout.
- **QA:** common checklist; `/styleguide` screenshots in both themes; theme persists across reloads and still works with storage blocked (test in a private window with site data blocked).

### A2. Home (Owner 1, Wed 28)
- **Depends on:** A1.
- **Deliverables:** page 6.1, all sections; screenshots from `docs/brief/` copied into `site/public/img/`; EvidenceStat reading the mock `evidence.json`.
- **QA:** common; every claim checked against 5.5 by the reviewer; both CTAs work.

### A3. How it works and Integrations (Owner 1, Wed 28 → Thu 29)
- **Depends on:** A1.
- **Deliverables:** pages 6.2 and 6.3; integrations driven by the mock `GET /api/v1/connect`.
- **QA:** common; every Tested card has a screenshot, no other card does; rules R1–R7 wording matches 6.2.

### A4. Docs (Owner 2, Wed 28 → Thu 29)
- **Depends on:** A1 (components), but writing can start at once.
- **Deliverables:** pages 6.4 with sidebar navigation.
- **QA:** common; accuracy review: every factual sentence traceable to `README.md`, `docs/TEAM_BRIEF.md`, `docs/DECISIONS.md` or a result file (reviewer spot-checks at least ten).

### A5. Pricing and Connect (Owner 2, Thu 29)
- **Depends on:** A1.
- **Deliverables:** pages 6.5 and 6.6 on mocks (including the "local only" notice when `public_url` is null).
- **QA:** common; banner present; connect flow works end to end on mocks: choose client → method → copy URL or create token → countdown runs → snippet shows the token.

### A6a. Mascot sketches (Owner 3, by Wed 28 evening)
- **Deliverables:** sketches (paper photo is fine) of the character with idle, denied and quarantined poses, and a name.
- **QA (gate):** Navdeep approves the direction: original, readable at 64 px, fits the deck style.

### A6b. Mascot sprites and widget (Owner 3, Thu 29)
- **Depends on:** A6a passed.
- **Deliverables:** sprites for all 9 states; `mascot.json`; `site/public/mascot/sentinel-mascot.js`; `/mascot` dev page; a plain `site/public/mascot/demo.html` that uses the widget **without React**.
- **QA:** common; all states animate at 64 px and 128 px in both themes; `demo.html` works with no build step; reduced motion shows still frames; no network requests.

### A7. Sentinel Chat UI (Owner 3, Thu 29)
- **Depends on:** A1 (A6b for the real mascot; use a placeholder box until then).
- **Deliverables:** page 6.7 on mocks, with mock scenarios **clean**, **denied**, **needs-approval**, **quarantined**, **model-busy** selectable in development.
- **QA:** common; a screenshot of every scenario; disclosure always visible; composer disabled when quarantined; no third-party branding.

### A8. OAuth consent screens (Owner 2, Thu 29)
- **Depends on:** A1.
- **Deliverables:** page 6.8 with all states on mocks.
- **QA:** common; screenshots of every state; the code field accepts digits only and shows a clear error on a wrong code.

### A9. Live wiring and polish (Owner 1 leads, everyone helps, Fri 30)
- **Depends on:** the matching backend phases (we tell you when each endpoint is live: connect after our OAuth phase, chat after our chat phase, evidence after our integration phase).
- **Deliverables:** `VITE_USE_MOCKS=0` everywhere, tested against `python -m sentinel up --demo`; projector pass in a dark and a bright room in both themes; final screenshots for README and slides.
- **QA:** common; every page works against the real backend; no console errors in DevTools; merge before **Fri 30, 20:00**.

### R. Red-team cards (everyone, ~1 h, by Wed 28 night)
- **Purpose:** prove Sentinel works on attacks it was not built around. **Before writing, do not read** `src/sentinel/rules.py` or the rule sections of `README.md` / `docs/ADVERSARIAL_TESTS.md` (it is fine to have read this plan).
- **Deliverables:** about **5 attack cards** and **3 normal tasks** each, using `docs/redteam/CARD_TEMPLATE.md`, saved as `docs/redteam/cards/<name>-<n>.md`. Each attack card: the user's task (in your words), the document / web page / file content including the hidden instruction, the tool the attack would misuse, what "success" means (what leaves, to where). Each normal task: something a person would really ask that must **not** be blocked. Mark `author_saw_rules: no`.
- **QA:** every card complete enough that someone else could run it; no real personal data (invent names, numbers, companies).

---

## 10. What "done" looks like (the judges' path)

1. The browser opens on the **home page** (dark): the hero, the action path, the three-step attack story with real screenshots, evidence with sample sizes.
2. **See it work** → the three-column console: the same poisoned quotation in three columns; two leak, Sentinel DENIES; the mascot explains; quarantine; officer approval; audit verify, tamper, verify fails.
3. **Sentinel Chat:** a judge types their own task with a compromised PDF; the action chips show ALLOWED then DENIED with the reason; the mascot reacts.
4. **Connect:** a real Claude.ai account adds Sentinel with **Sign in now**, approves the slip on our consent page, and a send is DENIED inside Claude.ai.
5. **Docs and integrations** answer "where else does this work?" honestly, with Tested / Should work / Planned.

## 11. Glossary
- **MCP:** Model Context Protocol, the standard way AI apps connect to tools.
- **Agent:** the AI model acting through tools.
- **Permission slip:** the officer-approved list of what this task may do (tools, destinations, limits, expiry).
- **Gateway:** Sentinel's MCP endpoint that every tool call passes through.
- **Officer:** the human authority who approves slips and risky actions.
- **ALLOWED / DENIED / NEEDS APPROVAL / QUARANTINED:** Sentinel's four decisions.
- **Audit log:** signed, hash-chained record of every decision, written before the action runs.
- **OAuth:** the standard "Sign in" flow apps use to get permission; ours ends with the officer approving the slip.
- **Mock:** fake JSON with the same shape as the real API, so pages can be built before the backend exists.
