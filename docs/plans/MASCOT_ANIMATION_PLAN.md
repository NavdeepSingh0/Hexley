# Mascot animation plan

For the teammate who owns the mascot's animation during the finale build (Fri 30 Oct to Sat 31 Oct 2026). You have creative freedom: give the mascot more life in the direction you think is right. This page tells you what exists, how to run it, what you may change freely, and the few rules that keep it honest.

**Deadlines.** First pull request by **Fri 20:00**. Last one by **Sat 07:00**. Code freeze is Sat 10:00 and judging is Sat 14:00, so anything later is not merged.

---

## 1. What exists
- **One file:** `design/mascot/sentinel-mascot.js` (about 430 lines). It's a Web Component, `<sentinel-mascot>`, that draws and animates an SVG itself. It has no dependencies, no images and no network access.
- **The contract:** `docs/contracts/MASCOT.md`. Read it first; it is short.
- **The character:** a rounded white screen-cube robot with a dark screen, two blocky eyes and a small badge dot.
- **Nine states:** `sleeping`, `idle`, `checking`, `allowed`, `denied`, `needs-approval`, `quarantined`, `verified`, `tamper`.
- **How it moves:** each eye is a set of numbers, and on every frame they ease toward the next state's numbers. A change of state is therefore a morph, not a cut. On top of that it bobs, blinks, pops on allowed, shakes on denied, squashes on quarantined and glitches on tamper.
- **Boosters:** `liftoff()` plays a one-off launch with thrusters and flames. The home page fires it once on the first visit.
- **Where it appears:**
  - the home page (with liftoff);
  - Sentinel Chat, beside the composer;
  - the console, top right;
  - soon, the browser extension (`docs/plans/EXTENSION_PLAN.md`).

  It must look right in all of them.

## 2. Run it
```
git clone https://github.com/NavdeepSingh0/Sentinel.git
cd Sentinel
npm --prefix site ci
npm --prefix site run dev          # then open http://localhost:5174/mascot-lab
npm --prefix console ci
npm --prefix console test          # the mascot's tests live in console/src/lib/mascot.test.js
```
- **The mascot lab (`/mascot-lab`, development only)** shows every state. It has slow-motion `speed` (0 to 4), a `still` toggle, sizes, themes and a liftoff replay. Use it for all your review.
- **The plain page** `design/mascot/preview.html` must keep working with no build step:
  ```
  python -m http.server 8765 --directory design/mascot
  ```
  Then open `http://localhost:8765/preview.html`.
- **What you don't need:** the Python backend. If you want to see the mascot react to real decisions, ask Navdeep for a running server link.

## 3. What you may change freely
- **Idle personality.** It could look around, react with micro-expressions, glance toward the bubble, stretch after a long idle, or blink irregularly.
- **Transitions.** For example anticipation before a reaction, overshoot and settle, a different morph curve per pair of states.
- **The reaction of each state.**
  - `checking` could feel more like scanning.
  - `allowed` could feel more relieved.
  - `denied` could be firmer without being alarming.
  - `quarantined` could feel heavier.
  - `verified` could feel proud.
  - `tamper` could feel more alarmed.
- **Sleeping and waking.** Breathing, the z's, and a wake-up animation when a session starts.
- **The speech bubble.** How it opens and closes, and typing-in of the text.
- **The boosters.** More flair in `liftoff()`, within the same 4.2 seconds or close to it.
- **New one-off decorations as methods**, like `liftoff()`: for example `wave()` or `hello()`. These must not be states and must claim no decision. Nothing in the product calls them until Navdeep decides where.
- **Timing and easing constants, and the shading and gloss of the body.**

## 4. Rules (these keep the product honest; please don't break them)
1. **The app decides the state, and the mascot only shows it.**
   - Don't add, rename or remove states. The nine names are tested.
   - Don't make the mascot react to anything except the `state` and `message` it is given. A mascot that looks worried when nothing happened would be a false signal to the officer.
   - Hovering may do something playful, but it must never look like a decision.
2. **The size doesn't change.** That's Navdeep's rule. Keep the drawing's footprint and the default `size` as they are; animate inside them.
3. **The motion bounds are tested:**
   - no offset beyond 10 px sideways or 14 px up;
   - no tilt beyond 4 degrees;
   - no scale beyond 15 percent.

   If an idea really needs more, say why in the pull request. If Navdeep agrees, change the test and `MASCOT.md` in the same pull request.
4. **Colour meanings are fixed.**
   - Violet is the brand.
   - Green is allowed or verified.
   - Blue is denied.
   - Amber is needs approval.
   - Red appears only in tamper, on the screen, never on the body.
   - Quarantined inverts the body (black body, white screen).
5. **Reduced motion.** With `prefers-reduced-motion: reduce` or the `still` attribute, show the finished pose with no animation, and liftoff does nothing.
6. **Keep it one file:** no dependencies, no image files, no network, no fonts.
   - It stops animating while the tab is hidden or the element is removed.
   - It keeps one animation loop.
   - The SVG keeps `role="img"` and an `aria-label` that follows the state.
   - The bubble stays a polite live region.
7. **The character stays original.** It is not Claude's mascot and not any game character. Inspiration is fine; copying is not.
8. **The exported pure functions keep working and stay tested.** New motion curves should be exported pure functions with a bounds test, like `liftoffAt`.

## 5. Phases
Each phase is one pull request, from a branch named `mascot/m<n>-<short-name>`, using the repository's pull request template. You get three tries per phase. If a phase still fails after the third, stop and talk to Navdeep.

| Phase | What | Done when |
|---|---|---|
| M1 Direction | A short note or a screen recording of a quick prototype: what you want to change and why, as 3 to 6 ideas | Navdeep picks which ideas go ahead (talk, no merge needed) |
| M2 Idle and transitions | Idle personality, sleeping and waking, transition polish | QA list below passes |
| M3 State reactions | The reaction for each of the nine states | QA list below passes; each state recorded in slow motion |
| M4 Decorations (optional) | New one-off methods, booster flair | QA list; documented in `MASCOT.md` |
| M5 Final polish | Performance, every size, both themes, docs updated | QA list; by Sat 07:00 |

## 6. QA for every pull request
- [ ] `npm --prefix console test` passes, including any new bounds tests.
- [ ] `npm --prefix site run build` and `npm --prefix console run build` both pass.
- [ ] In `/mascot-lab`, every state looks right at speed 1 and at 0.25, at sizes 32, 64 and 128, in the dark and light themes.
- [ ] Every change between states morphs smoothly, with no jump. Try idle to denied, denied to allowed, anything to quarantined, and tamper to verified.
- [ ] Reduced motion is respected: DevTools → Rendering → emulate `prefers-reduced-motion: reduce`. You see still poses and no liftoff.
- [ ] Switching to another tab stops the animation. Check the Performance panel, or that CPU drops to zero.
- [ ] DevTools → Network shows no request made by the mascot.
- [ ] `design/mascot/preview.html` still works with no build step.
- [ ] The home page (liftoff on first visit), Sentinel Chat and the console all still look right. Run `python -m sentinel up --demo`, or ask Navdeep.
- [ ] The pull request has a short screen recording of the states and before-and-after notes.
- [ ] If you changed behaviour that `MASCOT.md` describes, `MASCOT.md` is updated.

## 7. Who to ask
Navdeep decides direction and merges. Claude (with Navdeep) owns the backend that chooses the state. If you think the mascot needs a new state, write down which real event it would show. That's a backend change, so we decide it together.
