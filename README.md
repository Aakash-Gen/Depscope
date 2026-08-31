# DepScope

**Before you make a library a core dependency, DepScope tells you whether to trust it — with executed evidence instead of vibes.**

It clones a package at a pinned commit, **actually installs it in a clean virtualenv, actually runs its test suite**, measures real coverage, detects assertion-free "coverage theater", mines maintenance risk from git history, and produces an adoption scorecard in which **every single line cites an artifact you can open**.

```bash
python3 depscope/pipeline.py repos/humanize                    # one package
python3 depscope/pipeline.py repos/humanize repos/furl         # head-to-head
python3 depscope/pipeline.py repos/humanize --no-llm           # fully offline
```

In a terminal it prints a colour-coded report; piped to a file it emits markdown
(force either with `--markdown`).

---

## Who has this problem

Every developer choosing a dependency — a decision most teams make monthly, and one that quietly determines how much pain the next two years contain.

## The bottleneck

Real diligence means cloning the package, installing it in a clean environment, running its tests, measuring whether that coverage badge is honest, and reading years of git history for signs of abandonment. That is **30–60 minutes per candidate**, so essentially nobody does it. Instead people skim the README, glance at the star count, check the last commit date, and adopt on vibes.

READMEs are marketing. They are written by the maintainer, they are never re-validated, and they are exactly the surface a struggling project polishes most. The facts that actually predict pain — *does it install today? do the tests pass at this version? do those tests assert anything? is anyone still here?* — are **invisible to reading**. They only exist once you run the thing.

## Why solving it matters

A dependency chosen badly becomes a forced migration, a security exposure, or a 3am outage in a library nobody has maintained since 2016. DepScope compresses the diligence nobody has time for into ~18 seconds per package, and hands you a scorecard you can attach to a PR or an ADR and sign your name to.

---

## Results

Same 10 packages, same rubric, same model (`claude-sonnet-5`). The only difference is that DepScope runs the code.

| metric | reading-only baseline | DepScope | change |
|---|---|---|---|
| **Verdict accuracy (primary)** | **4–7/10 across 4 identical runs** (mean 5.75) | **10/10, every run** | **+42 pts at the mean** |
| Verdict stability on repeat runs | `swiftslug` flipped AVOID ↔ CAUTION | deterministic | — |
| Trap packages caught | 2/3 | **3/3** | +1 |
| Evidence-backed claims | 0 (no artifacts produced) | **60 of 60 (100% cited)** | +60 verifiable |
| README-vs-reality contradictions found | 0 | **5** | +5 |
| Unverifiable marketing claims rejected | 0 (repeated as fact) | **27** | +27 |
| Wall-clock per package | 7s | 19s | +12s |
| Human time for the same diligence | 30–60 min | ~0 (unattended) | **~40 min saved** |

Full per-package table: [eval/RESULTS.md](eval/RESULTS.md). Variance study: [eval/baseline_variance.py](eval/baseline_variance.py).

**Reading a repo is not just inaccurate — it is optimistically biased.** Across every repeated run, the baseline's errors ran in one direction: it said **ADOPT** for `bleach` (42% measured coverage), `tabulate` and `python-slugify` (bus factor 1, dormant) every single time. It never once wrongly rejected a healthy package. A README is written to be reassuring, and it works.

**The failures that matter.** The baseline called `retrying` a CAUTION — a package whose last commit was in **2016, 3,737 days ago**. It called `swiftslug` a CAUTION while that package's own test suite was failing — and on a repeat run of the identical input it called the same package AVOID, so where it did succeed it was partly luck. Reading cannot see either fact; both took DepScope one command.

**Why the baseline is quoted as a range.** It is a stochastic LLM judgement, so we ran it four times and report the spread rather than the flattering single sample. DepScope's verdicts are computed from executed artifacts and are identical on every run given the same commits. This project's own hot-take is *audit your measurement before you believe your result*; it would be indefensible to report a one-sample baseline.

### The trap packages

Three packages in the evaluation are **constructed by us and fully disclosed** ([traps/TRAPS.md](traps/TRAPS.md)). Each is a real package at a pinned commit, with one seeded defect and a deliberately glowing README — including their real git history, so from the outside they look like healthy, actively-maintained projects. They exist to answer one question: *can a reviewer who only reads a repo tell that it is broken?*

| trap | its README claims | execution reveals |
|---|---|---|
| `swiftslug` | "98% coverage, green on every commit" | **1 test fails** |
| `tidyurl` | "94% coverage, comprehensive suite" | **0.12 assertions per test** — the suite runs code and verifies nothing |
| `fasttable` | "install with one command" | **install fails** in a clean virtualenv |

### The challenging case, and what it revealed

The hardest case is **`swiftslug`** — and it is hardest for a reason worth stating.
Its seeded defect is a one-character change deep inside a regex substitution, in a
package of 81 tests with a 98%-coverage badge and a flawless README. Nothing about
the repository *reads* as broken. The other two traps leave a visible fingerprint if
you look hard enough: `fasttable`'s bogus dependency is sitting in `pyproject.toml`,
and `tidyurl`'s assertion-free tests are visible in the test file itself. The
reading-only baseline caught both of those. It could not catch this one, because
there is nothing to see — only something to *run*.

What it revealed was more interesting than a miss. Across four identical runs the
baseline called `swiftslug` **AVOID once and CAUTION three times**. It was the only
package whose verdict changed on unchanged input. So the reading-only approach is not
merely less accurate here — where it happens to succeed, it partly succeeds by
**luck**, and a diligence process you cannot repeat is not a process. That single
observation is why the results table reports the baseline as a range across repeated
runs rather than a single flattering number, and why the metric we care about most is
not just accuracy but *stability*: DepScope returns the same verdict from the same
commits every time, because it is reading a test log rather than forming an opinion.

---

## How it works

```
INPUT: package @ pinned commit
  │
  ├─ [Execution Probe]   fresh venv → install → run tests → measure coverage → assertion density
  ├─ [History Miner]     bus factor, commit cadence, release rhythm, abandonment  (deterministic)
  ├─ [Signal Reader]     LLM extracts the README's factual claims                 (prose only)
  │
  ├─ [Claim Verifier]    ← THE GATE: every claim checked against measured artifacts
  │                         unsupported claim → dropped;  contradicted → flagged
  │
  └─ [Scorer/Reporter]   scorecard + README-vs-reality table + head-to-head verdict
                                        │
                                   HUMAN SIGNS OFF
```

**The one rule the whole design serves: _evidence or it didn't happen._** The LLM is used only where language models are genuinely best — reading prose and extracting claims. It is never permitted to assert a fact. Scores are derived deterministically from artifacts; anything the artifacts cannot support is struck from the report rather than printed as fact. That is why the output is trustworthy enough to sign.

---

## Improvement changelog

Ten experiments, of which nine were failures worth more than the successes. Every result below is reproducible from this repo or the archived probes.

| Stage | What we tried and why | Evidence | Decision / learning |
|---|---|---|---|
| **Baseline** | Reading-only assessment: one prompt, given README + file tree + metadata + real source/test excerpts, asked for the same verdict with the same rubric | **4–7/10 (mean 5.75)**, 2/3 traps caught, 0 verifiable citations | Established the starting point — and it is *not* a strawman; it is deliberately generous |
| **Iter 1** | Added the **Execution Probe** (clean venv → install → pytest → coverage). Reading cannot know whether code runs | `swiftslug` 1 failing test, `fasttable` install failure surfaced immediately | **Kept.** This is the structural gap: execution facts are unknowable by reading |
| **Iter 2** | Added the **History Miner** (bus factor, cadence, abandonment) — repo-scale facts that do not fit in a prompt | `retrying`: 3,737 days since last commit, 0 commits/yr, 80% by one author | **Kept.** Turned the baseline's biggest miss into a one-line fact |
| **Iter 3** | Added **assertion-density** analysis after realising high coverage can be meaningless | `tidyurl`: 67% coverage but **0.12** assertions/test | **Kept.** Coverage theater is invisible to both reading *and* naive coverage tooling |
| **Iter 4** | Let the LLM write scores and narrative directly from the evidence | Confident, fluent, occasionally unsupported statements; marketing claims echoed as fact | **Removed.** The model is a superb writer and an unreliable witness |
| **Iter 5** | Replaced it with the **Claim Verifier gate**: scores derived deterministically, every LLM claim checked against artifacts | 60/60 report lines cited; **27** unverifiable claims struck; **5** README contradictions surfaced | **Kept.** This is the contribution — Iter 4's failure is what made it necessary |
| **Iter 6** | Hardened the harness after three of *our own* measurement bugs faked results (see below) | `python-dotenv` went from "6 failing tests" to **152 passing** once the venv's `bin/` was on `PATH` | **Kept.** Most of our early "findings" were harness bugs |
| **Iter 7** | Wrote DepScope's own test suite — a tool that judges test quality should be judged the same way | 26 tests; the suite immediately found a real gap (bytecode cache never purged) | **Kept.** Regression tests now pin both harness bugs that once faked results |
| **Iter 8** | Ran the baseline 4× instead of once, suspecting our own headline number | Baseline swings **4–7/10**; `swiftslug` flips verdict on identical input | **Kept.** A single-sample baseline would have overstated *and* misdescribed the gap |
| **Final** | Full pipeline + head-to-head + trajectories | **10/10 every run**, 3/3 traps, ~19s/package | Main contribution: the gap comes from *acquiring evidence*, not from reasoning harder |

### Experiments we removed, and what they taught us

Before DepScope, we spent this project trying to build an agent that **out-reasons** a frontier model. We failed **nine times**, on purpose and in public: spreadsheet auditing (4 regimes), README/dependency diagnosis, bug reproduce-then-fix, agent-trajectory claim auditing (even at 236k tokens), multi-requirement code generation, mutation-guided test generation, and rubric-grading consistency. In every single case, one naive prompt to `claude-sonnet-5` **matched or beat** the engineered agent. All nine probes, with their results and the full account of what each one taught us, are in [`experiments/`](experiments/).

Twice we believed we had finally found a gap. Both times we were wrong, and both times the cause was the same: **a bug in our own evaluation harness.** A stale `.pyc` bytecode cache made same-length mutations silently run the original code. A missing `PATH` entry made a healthy package's own CLI unavailable, producing six phantom test failures. The agent never actually won those rounds; our measurement lied to us.

---

## Main failure mode

**DepScope is only as honest as its harness.** Its verdicts are trustworthy exactly because they come from execution — which means a defect in *how* we execute becomes a false fact delivered with total confidence, and confident wrong facts are worse than admitted ignorance. We hit this three separate times (`.pyc` caching, missing `PATH`, `src/`-layout coverage returning nothing). Two mitigations are baked in: every number is traceable to a raw log a human can open in one click, and every fact is re-derivable on a clean machine. A second known limit: `AVOID` on a failing test suite can punish a package whose tests are simply environment-sensitive, so the artifact — not the verdict — is the deliverable.

## Hot take

> **Agents don't win by thinking harder. They win by knowing things the model cannot know.**

In 2026, a single frontier-model prompt is an extraordinarily strong baseline. We proved to ourselves nine times over that you cannot beat it on reasoning quality for any task whose input fits in its context window — and each time we thought we had, the "win" evaporated under a correct harness. The durable advantage is **evidence acquisition**: running the code, measuring the artifact, mining the history. Reading a README is a *belief*; running the test suite is a *fact*, and a package abandoned for 3,737 days does not care how confident your model sounds.

The corollary we paid for twice: **when your engineered agent appears to beat a naive baseline, audit your evaluation harness before you believe your architecture.** Most apparent agent wins are measurement bugs.

---

## What existed before, and what was built for this hackathon

**Built from scratch during the competition:** every line in `depscope/`, `tests/`,
`traps/`, `eval/`, and `experiments/` — the Execution Probe, History Miner, Scorer,
Claim Verifier, reading-only baseline, orchestrator, trap generator, evaluation
harness, and the nine prior probes. No pre-existing project was extended.

**Not ours, and used as-is:** the seven evaluated packages (`humanize`, `bleach`,
`tabulate`, `furl`, `python-dotenv`, `python-slugify`, `retrying`) are third-party
open source, cloned at pinned public commits and never modified. The three trap
packages are *derived* from three of them, with defects we injected — fully disclosed
with upstream credit in [traps/TRAPS.md](traps/TRAPS.md), and deliberately not
published. Standard tooling used unmodified: Python's standard library, `pytest`,
`coverage`, `git`, and the `claude` CLI for the two prose-reading steps.

## Repository layout

```
depscope/
  depscope/probe.py      Execution Probe   — venv, install, pytest, coverage, assertion density
  depscope/history.py    History Miner     — bus factor, cadence, abandonment (deterministic)
  depscope/scorer.py     Scorecard + Claim Verifier gate
  depscope/baseline.py   Reading-only baseline (the fair comparison arm)
  depscope/llm.py        Every model call: retries + trajectory capture
  depscope/pipeline.py   Orchestrator + report rendering + head-to-head
  tests/                 DepScope's own test suite (26 tests)
  experiments/           The nine failed experiments this design is built on
  traps/                 Trap-package generator + full disclosure (TRAPS.md)
  eval/                  Ground truth, evaluation harness, RESULTS.md
  trajectories/          Per-run JSONL agent trajectories (see trajectories/README.md)
  artifacts/<pkg>/       Raw evidence every report line cites
```

## What is scored, and what isn't

Six dimensions, each derived from a collected artifact: **clean install**, **tests
pass**, **measured coverage**, **test strength** (assertion density), **maintenance**,
**bus factor** — plus the README-vs-reality mismatch table. Issue responsiveness and
breaking-change mining are deliberately *not* implemented: the first needs a GitHub
token, which would put credentials in the submission and break offline reproduction.

## Running the tests

```bash
python3 -m pytest tests/ -q     # 26 passed
```

A tool that judges other projects' test quality should be willing to be judged the
same way. The suite concentrates on the logic that produced wrong answers during
development — the verdict rule, the claim verifier, the coverage-theater detector —
and carries explicit regression tests for the two harness bugs that once faked
results (bytecode caching and the missing `PATH` entry). It found a real gap the
first time it ran: `probe.py` disabled bytecode writing but never purged stale
`__pycache__` directories.

Setup, exact commands, versions, runtime and cost: **[REPRODUCE.md](REPRODUCE.md)**.
