## Phase
<!-- e.g. A2 Home. One phase per pull request. -->
Phase:
QA attempt (1, 2 or 3):

## What changed

## Common QA checklist (docs/plans/FRONTEND_PLAN.md §5.6)
- [ ] Dark and light themes both look right
- [ ] 1280×720 and 1920×1080: nothing clipped; 390 px wide: no horizontal scroll
- [ ] Keyboard: everything reachable with Tab, focus visible
- [ ] Contrast WCAG AA (Lighthouse or axe): no failures
- [ ] No external network requests (DevTools → Network shows only localhost)
- [ ] Honesty rules §5.5 and vocabulary §5.4 followed
- [ ] `npm run build --prefix site` succeeds

## Phase-specific QA
<!-- Copy the QA items for this phase from the plan and tick them. -->

## Screenshots
<!-- Both themes at 1280×720, plus anything the phase asks for. -->

## If this is attempt 3 and something still fails
<!-- What fails, why, and the options (cut scope / change approach / move later / drop). Stop and talk to Navdeep. -->
