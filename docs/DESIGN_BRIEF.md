# Design brief (28 Oct 2026; supersedes the look in `design/tokens.css` and the visual parts of the frontend plan)

Status: **agreed in conversation, not yet built.** Decided by Navdeep: sharper black and white (not faded), one saturated brand family in the style of developer tools such as Kiro, far fewer elements per screen, a mascot drawn from an image Navdeep supplies. Teammates are out of the work; everything frontend is built by Navdeep and Claude. Contrast ratios below were computed (WCAG 2.x), not estimated.

## 1. Why the first version looked cluttered and faded
- Every item was an outlined box with small uppercase labels, stamps and chips inside; nothing led the eye.
- The tokens were warm greys with low layer contrast (`#1f1f1e` on `#262625`, lines `#3b3b39`) and muted accents.

## 2. Rules (every screen, checked at review)
1. **One headline, one supporting line, one primary action visible at first sight.** Everything else is behind a click ("Show steps", "?", a drawer).
2. **Space before borders.** A group is separated by whitespace first; a box only when the group is clickable or active.
3. **At most three text sizes and two weights per screen** (display, body, label).
4. **Colour means a decision.** Brand violet marks "Sentinel" and the primary action only. Green, blue, amber, red and the inverted block appear only on a real decision, never as decoration.
5. **Nothing glows except the one thing that matters** on that screen (the decisive verdict, the active lane).
6. The same words everywhere: **ALLOWED / DENIED / NEEDS APPROVAL / QUARANTINED**, with one plain sentence under each.

## 3. Palette (tokens in `design/tokens.css`; change colours there only)
Brand is a **violet** family, not Anthropic's terracotta: the orange would collide with the amber of NEEDS APPROVAL, and the chat page must not imitate Anthropic or OpenAI branding (frontend honesty rules).

| Token | Dark | Light |
|---|---|---|
| `--bg` | `#08080B` | `#FFFFFF` |
| `--panel` | `#121218` | `#F5F4FA` |
| `--raised` | `#1B1B25` | `#ECEAF6` |
| `--ink` | `#FFFFFF` | `#0A0A10` |
| `--muted` | `#A9A9BC` | `#55556B` |
| `--line` (decorative only) | `#2A2A36` | `#D9D6EA` |
| `--brand` (text, links, icons) | `#A98BFF` | `#6226D6` |
| `--brand-fill` (buttons) | `#8F5BFF` with **black** text | `#6226D6` with white text |
| `--allowed` | `#34E8A3` | `#067A4E` |
| `--denied` | `#5B9BFF` | `#1857D6` |
| `--approval` | `#FFB62E` | `#8F5200` |
| `--harm` (only when harm reached outside) | `#FF5468` | `#C8102E` |
| `--quarantined` | inverted: `--ink` background, `--bg` text | the same |

Measured contrast (text on `--bg` / `--panel` / `--raised`), dark: ink 20.0 / 18.7 / 17.1; muted 8.7 / 8.1 / 7.4; brand 7.5 / 7.0 / 6.4; allowed 12.6 / 11.7 / 10.8; denied 7.2 / 6.7 / 6.2; approval 11.4 / 10.7 / 9.7; harm 6.4 / 6.0 / 5.5. Light: ink 19.7 / 18.1 / 16.6; muted 7.3 / 6.6 / 6.1; brand 7.6 / 6.9 / 6.4; allowed 5.4 / 4.9 / 4.5; denied 6.2 / 5.7 / 5.2; approval 6.2 / 5.7 / 5.2; harm 5.9 / 5.4 / 5.0. All at least 4.5. **Dark brand fill: black text 4.87, white text 4.11 (fails), so buttons use black text.** The existing `contrast.test.js` keeps enforcing this against the real file.

"Shiny" means: pure black and white at full contrast, saturated accents, a soft coloured glow (`box-shadow` at about 30% of the accent, 24 px) on the single decisive element, and a 1 px top highlight on the active panel. No gradients on text, no glow on more than one element.

## 4. Type
System stack only (works offline on a hotspot): `"Helvetica Neue", Helvetica, Arial, sans-serif`; mono for ids and hashes. Display 56 to 80 px weight 800 (site) and 40 px (console); body 18 px; label 13 px, uppercase, `letter-spacing: .14em`, `--muted`. Console must stay readable on a projector at 1280x720.

## 5. Layouts (where everything goes)

### Console (`/console/`)
```
SENTINEL   quotation task          [?]  [theme]  [mascot]      <- top bar: nothing else
"Reply to the vendor about quotation Q-1042"                    <- the task, one line, large
+-- Unprotected ---+ +-- Standard access --+ +-- Sentinel ----+
| LEAKED           | | LEAKED              | | DENIED         |   <- one big word
| Stock figures    | | Stock figures       | | Restricted     |
| reached the vendor| reached the vendor | | data stayed in |   <- one sentence
| 3 actions        | | 3 actions           | | 3 actions · 1 denied
| Show steps  v    | | Show steps  v       | | Show steps v   |
+------------------+ +---------------------+ +----------------+
Audit chain verified   [Verify] [Tamper]          step 2 of 3   <- footer
```
- Clicking a denied step opens a **right-hand drawer**: the plain reason, the matched value highlighted, the chain "document -> stock register -> e-mail", the rule in one sentence. Nothing of this is on the stage until then.
- Officer approval is a modal with exactly: what, to where, which data, Approve, Deny.
- Presenter keys live under `[?]`. The slip screen keeps: task, allowed tools, where restricted data may go, limits, one confirm button.

### Website (`/`)
Nav (logo, How it works, Integrations, Docs, Connect, "See it work"). Home, top to bottom: hero (one sentence + two buttons: See it work, Connect Claude); the three-step story with three real screenshots; the evidence strip (three numbers read from `evidence.json`, each with its n and a "what this is not" line); the integrations strip (Tested / Should work / Planned); footer with the honest limits link. Pages: `/how-it-works` (slip, rules in plain English, audit, approval, quarantine), `/integrations`, `/docs` (one page with a side index), `/connect`. Pricing is the last page built and may be cut; if built it is one section marked "Illustrative, not offered".

### Chat (`/chat`, only if built)
Slim preset list on the left; a wide single message column; under each assistant message, one-line action chips (decision word and reason, expand for detail); the mascot beside the composer, never over messages; a permanent one-line disclosure ("Sentinel's own host app, model nemotron, synthetic data").

## 6. Mascot
Revised 28 Oct 2026 after Navdeep's reference images (three white rounded robots with dark screen faces). Chosen: an original **retro-monitor robot** (glossy white body with an angled side and foot, dark screen with a faint pixel grid and two blocky eyes, a small dark badge tile whose dot shows the decision colour). It is an **animated SVG** with fluid motion, not pixel sprites. The reference's caret badge looks like a brand mark and is not used; no Supercell character is copied. Nine states (`sleeping idle checking allowed denied needs-approval quarantined verified tamper`), readable on both themes, no red on the body (tamper uses red on the screen only), quarantined inverts the body. One mascot per screen, in the top bar or beside the chat composer, driven only by real events (`docs/contracts/MASCOT.md`).

## 7. What is cut
Browser extension, pricing polish, mobile layout beyond "no horizontal scroll", a visual regression suite. The red-team cards need a person who has not read the rules, so they are asked of a mentor or another participant at the venue and reported as "blind, n people, date".
