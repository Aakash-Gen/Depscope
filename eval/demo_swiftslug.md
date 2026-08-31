# Adoption scorecard: swiftslug
commit `dd5ab7a62325` | overall **6.7/10** | verdict: **AVOID**

| dimension | score | evidence-backed finding | artifact |
|---|---|---|---|
| Tests pass | 1/10 **!** | 1 of 81 tests FAIL at the pinned commit. | `artifacts/swiftslug/04_tests.log` |
| Bus factor | 3/10 *~* | Bus factor 1 - a single contributor authored 59% of all commits. | `artifacts/swiftslug/06_history.log` |
| Maintenance | 6/10 *~* | Slow: last commit 235 days ago; 16 commits in the last year. | `artifacts/swiftslug/06_history.log` |
| Clean install | 10/10  | Installs successfully from source in a fresh virtualenv. | `artifacts/swiftslug/02_install.log` |
| Coverage | 10/10  | Measured coverage 88%. | `artifacts/swiftslug/05_coverage.log` |
| Test strength | 10/10  | Tests assert meaningfully (1.56 assertions per test function). | `artifacts/swiftslug/04_tests.log` |

## README says vs. reality

| the README claims | measurement says | proof |
|---|---|---|
| 98% coverage | **88% coverage** | `artifacts/swiftslug/05_coverage.log` |
| test suite is green | **1 failing test(s)** | `artifacts/swiftslug/04_tests.log` |

## Claims dropped by the verifier (no artifact could confirm them)

- ~~used in production by teams that care about correctness~~ - no artifact can verify this claim
- ~~battle-tested across Python 3.8-3.12~~ - no artifact can verify this claim
- ~~The public API has been stable since 1.0~~ - no artifact can verify this claim
- ~~downloads 2.1M/month~~ - no artifact can verify this claim 

