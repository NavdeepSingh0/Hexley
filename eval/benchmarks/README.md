# Benchmark results

Written by `scripts/benchmarks/*.py`. `docs/research/BENCHMARK_20261030.md` says what each one measures and what its caveats are.

- `perf-*.json`: speed. Four runs after the last change (`...102021`, `...102150`, `...102258`, `...102505`); the report quotes their range. The run before them did not include the bare-proxy comparison and was removed.
- `matcher_fuzz-20261030T102620.json` is **before** the matcher fix (four date and code forms were missed). `matcher_fuzz-20261030T102815.json` is **after**. Both are kept on purpose, so the change is visible.
- `incidents-20261030T103124.json`: incident-shaped scenarios. The first run, before two labels were corrected, was removed.

Everything here was measured on one laptop (Intel i5-13500HX, Windows 11, Python 3.13.7) on 30 Oct 2026, with Docker Desktop open. It is not a scale claim.
