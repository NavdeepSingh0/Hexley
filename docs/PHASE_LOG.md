# Phase log

One line per QA attempt, for both plans (`docs/plans/FRONTEND_PLAN.md` phases A*, `docs/plans/CORE_PLAN.md` phases B*). Each phase gets **3 attempts**; after a third FAIL, stop that phase and add an escalation note below the table before doing more on it.

| Phase | Attempt | Date-time (IST) | Result | What failed / note | Commit or PR |
|---|---|---|---|---|---|
| B0 | 1 | 2026-10-27 | PASS (with one item open) | Fresh clone of `7f72926`: `uv sync`, `npm ci` console + site, 27 console tests, site build, 310 Python tests all pass; site dev server renders the shell in the deck style on mocks. **Open:** teammates have not yet confirmed they can clone, because the private repo does not exist yet (needs Navdeep's repo URL) | 7f72926 |

## Escalations
*(none yet)*
