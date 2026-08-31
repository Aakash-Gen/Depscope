# Adoption scorecard: humanize
commit `35e2d21b4b30` | overall **9.5/10** | verdict: **ADOPT**

| dimension | score | evidence-backed finding | artifact |
|---|---|---|---|
| Bus factor | 7/10  | Bus factor 2 across 131 contributors. | `artifacts/humanize/06_history.log` |
| Clean install | 10/10  | Installs successfully from source in a fresh virtualenv. | `artifacts/humanize/02_install.log` |
| Tests pass | 10/10  | All 527 tests pass in a clean environment. | `artifacts/humanize/04_tests.log` |
| Coverage | 10/10  | Measured coverage 98%. | `artifacts/humanize/05_coverage.log` |
| Test strength | 10/10  | Tests assert meaningfully (1.85 assertions per test function). | `artifacts/humanize/04_tests.log` |
| Maintenance | 10/10  | Actively maintained: last commit 1 days ago, 86 commits in the last year. | `artifacts/humanize/06_history.log` | 

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

- ~~battle-tested across Python 3.8-3.12~~ - no artifact can verify this claim
- ~~used in production by teams that care about correctness~~ - no artifact can verify this claim
- ~~The public API has been stable since 1.0~~ - no artifact can verify this claim
- ~~swiftslug follows semantic versioning strictly~~ - no artifact can verify this claim 

# Adoption scorecard: retrying
commit `3659c70b1f0d` | overall **7.2/10** | verdict: **AVOID**

| dimension | score | evidence-backed finding | artifact |
|---|---|---|---|
| Maintenance | 0/10 **!** | Abandoned: no commit in 3737 days (last 2016-06-06). | `artifacts/retrying/06_history.log` |
| Bus factor | 3/10 *~* | Bus factor 1 - a single contributor authored 80% of all commits. | `artifacts/retrying/06_history.log` |
| Clean install | 10/10  | Installs successfully from source in a fresh virtualenv. | `artifacts/retrying/02_install.log` |
| Tests pass | 10/10  | All 21 tests pass in a clean environment. | `artifacts/retrying/04_tests.log` |
| Coverage | 10/10  | Measured coverage 92%. | `artifacts/retrying/05_coverage.log` |
| Test strength | 10/10  | Tests assert meaningfully (4.14 assertions per test function). | `artifacts/retrying/04_tests.log` |

## Claims dropped by the verifier (no artifact could confirm them)

- ~~Retrying is an Apache 2.0 licensed general-purpose retrying library, written in Python, to simplify the task of adding retry behavior to just about anything.~~ - no artifact can verify this claim 

# Head-to-head

| package | verdict | overall | installs | tests | coverage | test strength | maintenance |
|---|---|---|---|---|---|---|---|
| **humanize** | ADOPT | 9.5 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 |
| **retrying** | AVOID | 7.2 | 10/10 | 10/10 | 10/10 | 10/10 | 0/10 |
| **swiftslug** | AVOID | 6.7 | 10/10 | 1/10 | 10/10 | 10/10 | 6/10 |

**Recommendation:** adopt `humanize` (highest evidence-backed score, verdict ADOPT).
