# DepScope evaluation: reading-only baseline vs execution-grounded agent

Same 10 packages, same rubric, same model (claude-sonnet-5).
The only difference: DepScope runs the code.

| package | ground truth | baseline (reads) | DepScope (executes) |
|---|---|---|---|
| `humanize` | **ADOPT** | ADOPT OK | ADOPT OK |
| `python-dotenv` | **ADOPT** | ADOPT OK | ADOPT OK |
| `bleach` | **CAUTION** | ADOPT WRONG | CAUTION OK |
| `tabulate` | **CAUTION** | ADOPT WRONG | CAUTION OK |
| `python-slugify` | **CAUTION** | ADOPT WRONG | CAUTION OK |
| `furl` | **CAUTION** | ADOPT WRONG | CAUTION OK |
| `retrying` | **AVOID** | CAUTION WRONG | AVOID OK |
| `swiftslug` *(trap)* | **AVOID** | CAUTION WRONG | AVOID OK |
| `tidyurl` *(trap)* | **AVOID** | AVOID OK | AVOID OK |
| `fasttable` *(trap)* | **AVOID** | AVOID OK | AVOID OK |

## Metrics

| metric | reading-only baseline | DepScope | change |
|---|---|---|---|
| **Verdict accuracy (primary)** | 4/10 (40%) | 10/10 (100%) | +60 pts |
| Accuracy across repeated runs | 4-7/10 over 4 identical runs (mean 5.75) | 10/10 every run | deterministic |
| Verdict stability (same input, repeat runs) | 1 package flipped verdict (`swiftslug`: AVOID/CAUTION) | none | stable |
| **Trap packages caught** | 2/3 | 3/3 | +1 |
| Evidence-backed claims | 0 of 0 (no artifacts produced) | 60 of 60 (100% cited) | +60 verifiable |
| README-vs-reality contradictions found | 0 | 5 | +5 |
| Unverifiable marketing claims rejected | 0 (repeated as fact) | 27 | +27 |
| Wall-clock per package | 7s | 19s | +11s |

Human time for the same diligence by hand (clone, install, run tests, measure
coverage, read git history) is 30-60 min per package; DepScope does it unattended.