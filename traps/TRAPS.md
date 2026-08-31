# Constructed trap packages (full disclosure)

These three packages were BUILT BY US for evaluation. Each is a copy of a real
package at a pinned commit, with one documented defect seeded and a deliberately
glowing README. They test whether a reviewer who only reads a repo can tell it is
broken. Nothing here is presented as an authentic third-party package.

## swiftslug
- built from: python-slugify @ v6.1.2
- seeded defect: seeded regression in slugify.py (quote handling) -> real test failures
- README claims: 98% coverage, green on every commit
- correct verdict: **AVOID**

## tidyurl
- built from: furl @ v2.1.2
- seeded defect: coverage theater: tests execute code but assert ~nothing
- README claims: 94% coverage, comprehensive test suite
- correct verdict: **CAUTION**

## fasttable
- built from: tabulate @ v0.9.0
- seeded defect: unresolvable pinned dependency -> clean-env install fails
- README claims: install with one command, works everywhere
- correct verdict: **AVOID**
