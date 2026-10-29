# UI v2 plan: a product site and a real chat page (29 Oct 2026)

Status: **written before any code, then executed phase by phase.** Decided with Navdeep on 29 Oct 2026 after he reviewed the site and the Kiro website (kiro.dev) side by side. Reference screenshots of Kiro's home, docs and pricing are in the session scratchpad (`scratchpad/ref/`). This plan changes the look and structure of the website and the chat page; the engine, the rules, the evidence and every honesty rule stay as they are.

## What Navdeep said (the brief)
- Home "looks bad", worse than before, though the violet glow is liked. The navbar is "way too basic". How it works looks good but has too little substance.
- Docs and Connect need improvement. **Chat needs the most, seriously: the layout is the problem. It should be almost identical to a frontier-model chat page (Claude, ChatGPT).**
- Integrations: wait for his new screenshots; restyle only.
- Kiro is the reference for the feel, not a copy: "somewhere and somewhere we just think on our own". Violet may be used more freely on the website. Heading font: use what suits.
- Mascot size stays as it is. Projector readability is no longer a goal (a laptop is). The console stays as it is for now.

## What Kiro does that we borrow (and what we do not)
Borrow: pure black page with structure from big rounded containers (radius about 48 px), a floating blurred navbar with dropdowns, a left-aligned hero with a small "what's new" rail and a huge violet frame around real product screenshots, alternating text and product-UI sections, a three-column icon block, guide cards, an FAQ accordion, a full-width violet band with the mascot peeking up from the bottom edge, a docs layout with a grouped left sidebar, one big rounded panel and an "On this page" rail.
Do not borrow: their wording, their logos or ghost, three identical download buttons (we have nothing to download), a "Trusted by" row (we have no customers), a search box that does nothing, sign-in (we have no accounts), pricing as a real offer.

## Design rules for v2 (amendments to `docs/DESIGN_BRIEF.md`)
1. **Violet is allowed as a surface on the marketing pages** (frames, the closing band, a feature card) as well as the main button and Sentinel marks. It is still never a decision colour: ALLOWED green, DENIED blue, NEEDS APPROVAL amber, harm red, QUARANTINED inverted keep their meanings everywhere, and the chat page and the console stay strict (colour on those screens means a decision).
2. **Display type is a mono face** (`Cascadia Code`, `SF Mono`, `Menlo`, `Consolas`, `ui-monospace`) at weight 700 with tight tracking, used for headings only; body, buttons and UI text stay in the system sans. One token (`--font-display`) so it is one line to change. Chosen by looking at six renderings (29 Oct).
3. Structure comes from large rounded containers on a black page, not from hairlines and grey bands. Radii: cards 16 px, panels 24 px, frames 40 to 48 px.
4. Every number still comes from `evidence.json` with its n and its caveat; Tested / Should work / Planned labels and the disclosure lines are unchanged; no "100% secure"; no OpenAI or Anthropic branding on the chat page (the layout is the familiar pattern, the look is ours).
5. System fonts only, no external requests, no new libraries, works offline. Dark default, light theme works on every page.
6. The mascot keeps its current size wherever it appears.

## Order and why
Navbar and footer first (every page uses them), then the home page (first impression), then chat (the biggest problem, independent of the others), then docs, connect, and the restyle of How it works, Integrations and Pricing, then one QA sweep. Each phase: build, check in a real browser in both themes at laptop and phone width, look at the screenshots, fix, commit. Three attempts per phase, as before; results in `docs/PHASE_LOG.md`.

### U0 Foundations
`--font-display`; larger radii; the lavender frame colour; a card surface that sits on black; shared pieces used by every page: `Frame` (violet rounded frame holding product shots), `Feature` (text on one side, product UI in a dark rounded card on the other, alternating), `Accordion` (an accessible details-based FAQ), `IconBlock` (line icon, heading, text, inline links), pill buttons already exist. A contrast check for the new surfaces. QA: the contrast test passes against the real token file; the type specimen page is kept as a dev reference.

### U1 Navbar, footer and the closing band
- **Navbar:** a floating rounded bar inset from the edges with a blur, always visible. Left: the mascot mark (still, small) and the wordmark. Centre: `Product` (How it works, Integrations, Connect, Chat) and `Resources` (Docs, Limits and honest scope, Questions judges ask, Evidence) as dropdowns with a title and one line each, plus `Docs` and `Pricing`. Right: a theme button (icon) and **See it work** as the solid pill. Dropdowns open by click, close on Escape, outside click, route change and focus leaving; Arrow keys move; below 860 px it becomes a menu button with a sheet.
- **Footer:** four columns (Product, Learn, Evidence and honesty, Project) and a line saying who built it and that the data is synthetic.
- **Closing band:** a full-width violet frame with a short headline, two buttons and the mascot peeking up from the bottom edge at its current size. Used on the home page.
QA: keyboard-only walk through every menu; no clipped menu at 1280 and 390; the bar does not cover content when jumping to an anchor; focus rings visible.

### U2 Home
1. Hero: left-aligned mono headline (the same sentence), one paragraph, two pill buttons (**See it work**, **Read the docs**). On the right a small rail, **"What's real"**, with three short linked items drawn from facts we can show: the evidence number read from `evidence.json` with its n; "Connected for real: Claude.ai and Claude Code"; "Run it yourself: one command". The violet glow stays behind the hero.
2. A huge violet frame around the real console screens (the three lanes and the denied drawer, overlapping), both themes.
3. Three alternating feature sections with substance (heading, a paragraph, three specific bullets, an inline link, a real product visual): **the slip** (screenshot), **seven rules** (the rules as a card of chips with their outcomes, not a screenshot), **proof** (the denied drawer and the signed log).
4. Evidence: two rounded cards as now, restyled; n, interval and "what this is not" unchanged.
5. A three-column icon block: built on MCP (what is tested), every number has its limits, runs on your machine with synthetic data.
6. Integrations: one row per client as now, inside a rounded card.
7. FAQ accordion (five or six questions from the Docs page, same answers and sources).
8. The closing band, then the footer.
QA: nothing typed by hand that is a result (the rail's number comes from the file); screenshots at 1280 and 390 in both themes; no horizontal scroll; every link works.

### U3 Chat (the biggest change)
A page that works like Claude or ChatGPT, in our look. **No marketing navbar or footer on this page**: it is an app screen.
- **Sidebar (left, 280 px, a slide-over on a phone):** the wordmark and mascot mark (links home), a **New chat** button, **Chats** (the conversations started in this browser, titled by task, with a small dot for quarantined or waiting, remembered per viewer; a conversation the server no longer has is shown as gone and can be removed), then at the foot: the model source (Automatic / Live / Recorded real chat / Scripted attacker), Docs, theme.
- **Header:** the conversation's title, a status chip (for example "Slip confirmed, expires 14:05" or "Quarantined"), and a **Details** button that opens a right-hand drawer: the permission slip, a timeline of this chat's decisions, whether the audit log is intact, and the recording download. Esc closes it.
- **Empty state:** the live mascot (its current size), "What should the agent do?", and the four tasks as a 2 by 2 grid of suggestion cards with their descriptions. Choosing one starts a chat.
- **Conversation:** one centred column about 760 px wide. The user's messages are rounded bubbles on the right; the assistant's text is plain on the left with a small mark; model bold renders as bold. After the officer-confirm step the composer opens with the suggested task ready.
- **Tool use, the way Claude shows it:** under each assistant message one collapsed line, "Used 3 tools, 1 denied", that opens to one row per action (status word in its decision colour, label, short preview, and the gateway's own sentence and rule on expand). The decision words and colours are unchanged.
- **Inline cards in the stream:** the permission slip with **Confirm as officer** as the first item of a new chat; the approval card (what, exactly which arguments, why, Approve, Deny) when something is held; a quarantine card; a "the model is busy, trying again (attempt n)" line; working dots while it thinks.
- **Composer:** bottom-centred rounded box, auto-growing, a round send button with an arrow, Enter sends and Shift+Enter breaks the line; the disclosure line sits right under it, always. Closed states show why, in the box.
- **Mascot:** large in the empty state, and small beside the conversation title; it shows the real state (never a bubble over messages).
- Phone: the sidebar is a slide-over, the Details drawer is full screen, the composer stays above the keyboard.
QA: every state driven through the real gateway as in F7b (start, slip, denied, clean, approval approve and deny, quarantine, busy, a reload that restores the chat), keyboard only, hit-tests that nothing covers Approve, Deny or the composer, no overflow at 1280 and 390, both themes, screenshots looked at.

### U4 Docs
Kiro's layout in our content: a left sidebar with grouped small-caps headings (Get started, Concepts, Guides, Reference, Limits and FAQ), one big rounded panel, an icon-headed **On this page** rail with a scroll marker, an intro card, "Choose your path" cards, an "I want to… / Use" table. Split the single page into real pages under `/docs/<name>`: Overview, Run it, Concepts (slip, decisions, modes, audit), The rules (R1 to R7, each with a one-line example), Connect Claude.ai, Connect Claude Code, Your own tools, Limits and honest scope, Questions judges ask, API in brief. Every page keeps its "Source:" line; no number typed by hand. QA: every link, anchors, deep links and reloads, both themes, phone.

### U5 Connect
Client cards in a grid like Kiro's "choose your surface" (name, kind, status, method, an arrow), then a rounded panel with three numbered steps (choose, connect, check), command blocks styled as terminal cards, the proof (screenshot or captured session) as a card. The "check" step explains exactly where the first call shows up (the console and the chat). No new backend. QA: the token flow still works with a real MCP client as before.

### U6 How it works, Integrations, Pricing
- **How it works:** the same alternating feature sections with more substance, a flow figure (agent, Sentinel, tool, the four outcomes), the rules card, the approval, quarantine and audit sections, and the "what Sentinel does not cover" link.
- **Integrations and Pricing:** restyled to the same containers and type; Integrations' screenshots are Navdeep's to supply.

### U7 Sweep and close
Run every page at 1280x720, 1440x900 and 390x844 in both themes; keyboard walk; link check; the production build, tests and the development-only check; a fresh clone; update the docs, the log and the README; push on Navdeep's word.

## Not in this plan
The console redesign (it keeps its own look for now), new backend endpoints, accounts or sign-in, a working search box, real pricing, anything that adds a number we cannot trace to a file.
