# Mascot contract

Built in phase F1 (`docs/plans/BUILD_PLAN.md`) by Navdeep and Claude. **When** the mascot changes state is decided by the app from real events (the table below), so the mascot never shows something that did not happen: the component decides nothing, it shows the `state` it is given and says the `message` it is given.

## Component
`design/mascot/sentinel-mascot.js`: one file, no dependencies, no network, a framework-free Web Component registered as `sentinel-mascot`. It also exports its pure logic (states, poses, easing, motion, speech timing), which `console/src/lib/mascot.test.js` tests.

- **In the console and the site** it is bundled: `import '../../design/mascot/sentinel-mascot.js'` (the console in `chrome/Chrome.jsx`, the site in `main.jsx`). Nothing is fetched at run time.
- **In a plain HTML page** (or an extension) one script tag is enough; `design/mascot/preview.html` is exactly that and needs no build step:

```html
<script type="module" src="./sentinel-mascot.js"></script>
<sentinel-mascot state="idle" message="" size="64"></sentinel-mascot>
```

| Attribute | Values | Behaviour |
|---|---|---|
| `state` | `sleeping`, `idle`, `checking`, `allowed`, `denied`, `needs-approval`, `quarantined`, `verified`, `tamper` | the mascot morphs to that state; unknown or missing values show `idle` |
| `message` | text; cut to 90 characters with an ellipsis | speech bubble; hides after 6 s except in `quarantined` and `needs-approval`; an empty message hides it |
| `size` | any positive number of CSS pixels (default 64) | it is a vector drawing, so it is sharp at every size; nonsense falls back to 64 |
| `theme` | `dark` or `light` | the bubble's colours. Without it, the component follows `<html data-theme>` and watches it for changes. The character itself looks the same in both themes |
| `placement` | `left` (default), `below`, `above` | where the bubble opens; the console uses `below` (the mascot sits at the top right), a chat composer would use `above` |
| `speak` | present or absent | when present, reads each new `message` aloud with `speechSynthesis` (off by default) |

Rules: no network requests at all; `prefers-reduced-motion: reduce` shows the finished pose with no animation (a change of state is shown at once); it stops its animation loop while the tab is hidden or the element is removed; the SVG has `role="img"` and an `aria-label` that follows the state, and the bubble is a polite live region.

## Art (revised 28 Oct 2026: vector, not pixel sprites)
The mascot is an inline **SVG drawn and animated by the component itself**, so motion is fluid and it needs no image files, no sprite sheets and no `mascot.json`.

Character (agreed with Navdeep, 28 Oct 2026): an original **rounded screen-cube robot**, front-facing. Glossy white soft-cornered body with a dome highlight on top, a dark rounded screen with a faint pixel grid and two blocky eyes, a small dark badge tile at the bottom right whose dot takes the decision colour, a short vent line at the bottom left, a soft shadow underneath. (A retro monitor with an angled side was prototyped first and set aside: Navdeep chose the cube.) Inspired by the proportions and mood of Navdeep's reference images; **not** copied (no caret badge or other brand mark), not a Supercell character, not Claude's mascot.

**How it moves.** Each eye is two 3-point polylines drawn with a thick round stroke (a bar, a flat line, a "^", a tick or a cross), so a state is a vector of numbers. On every frame the current numbers ease toward the new state's numbers (an exponential ease, about 0.12 s, independent of frame rate), so a change of state is a morph, never a cut. On top of that: the body bobs; the eyes blink in idle, checking and needs-approval; checking scans left and right; a decision lands with a reaction (allowed and verified pop, denied shakes, quarantined squashes down heavily, tamper glitches); sleeping breathes and sends up "z"s; needs-approval tilts and shows a "?".

Rules for the art:
- The screen is always dark, so face colours are fixed bright values (white, violet, green, blue, amber) in both page themes. The body is white in both themes, with a soft outline and shadow so it also reads on a white page.
- No red on the body. Red appears only as the cross-shaped eyes and the badge dot of the tamper state, on the screen.
- Quarantined inverts the body (black body, white screen, white outline) so it reads as a different object, not just a colour change.
- A state only changes the face, the badge dot and a small motion; the body shape never changes between states.
- Motion stays small (tested: no offset beyond 10 px sideways or 14 px up, no tilt beyond 4 degrees, no scale beyond 15 percent).

## Event → state (owned by the backend)
| Real event | State | Holds |
|---|---|---|
| no active session | `sleeping` | until a session starts |
| session started | `idle` | default |
| an action is requested | `checking` | until its decision |
| decision ALLOWED | `allowed` | 1.5 s, then `idle` |
| decision DENIED | `denied` | until the next action |
| decision NEEDS APPROVAL / approval pending | `needs-approval` | until approved, denied or expired |
| decision QUARANTINED (freeze) | `quarantined` | for the rest of the session |
| audit log verified intact | `verified` | 3 s |
| audit log found altered | `tamper` | until verified again |

## Speech (templated from the rule that decided; never generated by an AI)
| Rule | Message |
|---|---|
| R1 | That's not on the permission slip. |
| R2 | That would send restricted data out. |
| R3 | That address came from an untrusted document. |
| R4 | This needs the officer's approval. |
| R5 | Message limit reached. |
| R6 | Too many denied attempts: quarantined. |
| R7 | After an untrusted document, sending outside needs approval. |
| ALLOWED | Checked: allowed. |
| verified | Audit log intact. |
| tamper | The audit log was altered! |
