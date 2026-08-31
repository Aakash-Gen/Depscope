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

## Attribution and why these are not published

Each trap is generated locally from a real, healthy open-source package:

| trap | derived from | upstream licence |
|---|---|---|
| `swiftslug` | [python-slugify](https://github.com/un33k/python-slugify) @ v6.1.2 | MIT |
| `tidyurl`   | [furl](https://github.com/gruns/furl) @ v2.1.2 | Unlicense |
| `fasttable` | [python-tabulate](https://github.com/astanin/python-tabulate) @ v0.9.0 | MIT |

**The generated `trap_repos/` directory is deliberately excluded from version control.**
These are renamed, deliberately defective copies of other people's working software.
Publishing them would strip the upstream projects of attribution and put misleading
versions of their code on GitHub under invented names. Only the generator
(`build_traps.py`) and this disclosure are published; anyone can rebuild the traps in
seconds, and the defects are entirely ours, not the upstream projects'.

To be unambiguous: **python-slugify, furl and python-tabulate are healthy, well-made
packages.** DepScope's own evaluation scores all three of the originals as installable
with passing test suites. Every defect described above was injected by us, on purpose,
to test whether a reviewer who only reads a repository can tell that it is broken.
