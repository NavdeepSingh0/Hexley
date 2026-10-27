# Phase log

One line per QA attempt, for both plans (`docs/plans/FRONTEND_PLAN.md` phases A*, `docs/plans/CORE_PLAN.md` phases B*). Each phase gets **3 attempts**; after a third FAIL, stop that phase and add an escalation note below the table before doing more on it.

| Phase | Attempt | Date-time (IST) | Result | What failed / note | Commit or PR |
|---|---|---|---|---|---|
| B0 | 1 | 2026-10-27 | PASS (with one item open) | Fresh clone of `7f72926`: `uv sync`, `npm ci` console + site, 27 console tests, site build, 310 Python tests all pass; site dev server renders the shell in the deck style on mocks. **Open:** teammates have not yet confirmed they can clone, because the private repo does not exist yet (needs Navdeep's repo URL) | 7f72926 |

| B1 | pre-QA | 2026-10-27 | (dev loop) | Three corrections to my own test assertions, none a product defect: the token endpoint answers a wrong PKCE verifier with 401 not 400; an empty `Bearer ` header is illegal HTTP; a same-second refresh yields a byte-identical token | |
| B1 | 1 | 2026-10-27 | PASS | 26 OAuth tests, 3 new mutation checks caught (13 of 13 overall), full suite green, **live**: free Claude.ai account signed in with "Sign in now", officer code approved the slip, send denied by R2, 0 messages delivered, audit chain intact. Live check also found a stray "Â·" in the consent page (caused by my own mutation test rewriting the file in the wrong encoding): fixed, regression test added | (this commit) |

**Unexplained one-off, B1 gate (27 Oct):** one full-suite run showed 3 failures in `tests/test_eval.py` (the scripted-corpus counts; some corpus cases evidently errored and were excluded). It did not recur: the same tests passed alone (13/13), in suite order after the modules before them (108/108), and in two further full runs (336/336). The failed run was the fastest of the three, so "slow machine" is not the explanation. Nothing in B1 touches that path with OAuth off. Action taken: the eval test fixture now fails immediately and prints the first recorded errors, so a recurrence will name its cause. Treat as open until it is explained or does not return.

## Escalations
*(none yet)*
