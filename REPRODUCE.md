# Reproduction guide

Written for someone starting from a clean machine. Everything here is public data:
seven real open-source packages pinned to public commits, plus three trap packages
this repo constructs locally from those same commits. No credentials, no tokens, no
private data, and no network access is needed after the initial clones.

---

## 1. Requirements

| thing | version used | notes |
|---|---|---|
| macOS / Linux | macOS 15 (Darwin 25.6) | Windows untested |
| Python | **3.9.6** (system `python3`) | 3.9+ works; the pinned package versions were chosen for 3.9 compatibility |
| git | 2.50.1 | any modern git |
| `claude` CLI | authenticated, model `claude-sonnet-5` | needed only for the LLM arms (README claim extraction + the reading-only baseline). The Execution Probe, History Miner and Scorer are pure Python and need no LLM. |
| disk | ~600 MB | full clones plus one throwaway virtualenv at a time |

Check your setup:

```bash
python3 --version          # 3.9+
git --version
claude -p --model claude-sonnet-5 <<< "say ok"   # should print ok
python3 -m pytest tests/ -q                      # 26 passed (needs pytest)
```

No `pip install` is required at the top level: DepScope uses only the standard
library and creates its own isolated virtualenv per package.

---

## 2. Get the evaluation corpus

```bash
cd depscope

# 2a. clone the seven real packages (full history -- the History Miner needs it)
mkdir -p repos && cd repos
for spec in \
  "python-slugify:un33k/python-slugify" \
  "humanize:python-humanize/humanize" \
  "tabulate:astanin/python-tabulate" \
  "python-dotenv:theskumar/python-dotenv" \
  "retrying:rholder/retrying" \
  "furl:gruns/furl" \
  "bleach:mozilla/bleach"
do
  n="${spec%%:*}"; p="${spec##*:}"
  [ -d "$n" ] || git clone "https://github.com/$p.git" "$n"
done

# 2b. pin every package to the exact commit that was evaluated
git -C python-slugify checkout -q v6.1.2   # 3f1a0fe
git -C humanize       checkout -q 4.9.0    # 35e2d21
git -C tabulate       checkout -q v0.9.0   # bf58e37
git -C python-dotenv  checkout -q v1.0.1   # d6c0b96
git -C furl           checkout -q v2.1.2   # 10da29f
git -C bleach         checkout -q v5.0.1   # 6cd4d52
git -C retrying       checkout -q v1.3.3   # 3659c70
cd ..

# 2c. build the three constructed trap packages (see traps/TRAPS.md for full disclosure)
python3 traps/build_traps.py
```

Expected: `built trap: swiftslug / tidyurl / fasttable`, and `trap_repos/` now holds
three packages that carry the real git history of their source package plus one
seeded, documented defect each.

> **Note on drift.** The seven real packages are pinned by tag, so their *execution*
> evidence is stable. Maintenance evidence is deliberately read from each project's
> live default branch, so `days_since_last_commit` will grow over time; a package may
> therefore move from ADOPT to CAUTION months from now. That is the tool behaving
> correctly, not a reproduction failure. The numbers in `eval/RESULTS.md` were
> recorded on **2026-08-31**.

---

## 3. Run it

### One package

```bash
python3 depscope/pipeline.py repos/humanize
```

Expected: a markdown scorecard, verdict **ADOPT**, overall ~9.5/10, with every line
citing a file under `artifacts/humanize/`. Runtime ~20–30s.

### The demo — a trap package

```bash
python3 depscope/pipeline.py trap_repos/swiftslug
```

Expected: verdict **AVOID**; the finding `1 of 81 tests FAIL at the pinned commit`;
a *README says vs. reality* table contradicting its "green build" claim; and a list
of struck-through marketing claims the verifier refused to repeat. Runtime ~15s.

### Head-to-head

```bash
python3 depscope/pipeline.py repos/humanize trap_repos/swiftslug repos/retrying
```

Expected: three scorecards followed by a comparison table recommending `humanize`
(ADOPT 9.5) over `retrying` (AVOID — maintenance 0/10) and `swiftslug` (AVOID —
tests 1/10). Runtime ~60s.

---

## 4. Reproduce the headline result

```bash
python3 eval/run_eval.py            # both arms, then writes eval/RESULTS.md
# or run the arms separately:
python3 eval/run_eval.py baseline   # reading-only arm  (~2 min, LLM)
python3 eval/run_eval.py depscope   # execution arm     (~4 min)
```

Expected output (`eval/RESULTS.md`):

| metric | reading-only baseline | DepScope |
|---|---|---|
| Verdict accuracy | **4-7/10 across runs** (mean 5.75) | **10/10, every run** |
| Trap packages caught | 2/3 | 3/3 |
| Evidence-backed claims | 0 | 60 of 60 |

The baseline is a stochastic LLM judgement, so quote it as a range. To reproduce the
spread yourself (about 5 minutes, 30 LLM calls):

```bash
python3 eval/baseline_variance.py 3     # writes eval/baseline_variance.json
```

Expect roughly 6-7/10 per run, and at least one package whose verdict changes between
identical runs. DepScope's verdicts are deterministic given the same commits.

Ground truth and the rubric that defines it: [`eval/ground_truth.json`](eval/ground_truth.json).
The rubric is fixed in advance and applied to objectively checkable facts; both arms
are given the same rubric and the same packages.

**Honest note on the 10/10.** DepScope's scorer applies that published rubric to facts
it *measures*, so once the measurements are right the verdicts follow — the interesting
result is not that DepScope scores 100%, it is that the reading-only arm, given the same
rubric and a generous view of the repository, **gets three to six of the ten wrong on any
given run** because it has to guess the facts. Every ground-truth fact is independently checkable in `artifacts/`.

---

## 5. What each arm may and may not do

Both arms use the same model (`claude-sonnet-5`) and the same rubric.

- **Reading-only baseline** receives the README, the file tree, packaging metadata, and
  real source and test excerpts — everything a careful human sees while skimming a repo.
  It may not execute anything.
- **DepScope** additionally runs the package: clean-venv install, the test suite,
  coverage measurement, and git-history analysis.

This is the only difference, and it is the experiment.

---

## 6. Runtime and cost

| step | wall clock | LLM cost |
|---|---|---|
| Clone + pin the corpus | 2–4 min (network) | $0 |
| Build traps | < 5 s | $0 |
| One package (full pipeline) | 12–30 s | ~1 LLM call (README claim extraction) |
| Reading-only arm, 10 packages | ~1.5 min | 10 LLM calls |
| DepScope arm, 10 packages | ~3 min | 10 LLM calls |
| **Full evaluation** | **~5 min** | **~20 short LLM calls (well under $1)** |
| Baseline variance study (3 repeats) | ~5 min | 30 LLM calls |
| DepScope's own test suite | < 1 s | $0 |

The Execution Probe, History Miner, Scorer and Claim Verifier make **no LLM calls at
all** — they are deterministic and free. The LLM is used only to read prose.

---

## 7. Output you should expect

```
artifacts/<package>/
  01_venv.log        virtualenv creation
  02_install.log     clean-env install (the "does it install" evidence)
  03*.log            test-dependency installation
  04_tests.log       the test run (the "do tests pass" evidence)
  05_coverage.log    measured coverage (not the badge)
  06_history.log     bus factor, cadence, abandonment
  result.json        structured probe facts
  history.json       structured history facts
  scorecard.json     the scored verdict with citations
eval/RESULTS.md      the headline comparison table
```

Every claim in a scorecard points at one of these files. If you doubt a verdict, open
the artifact it cites — that is the entire design.

---

## 8. Troubleshooting

- **A package reports failing tests you believe are healthy.** Check `04_tests.log`
  first. Environment-sensitive suites exist; this bit us with `python-dotenv`, whose
  tests invoke its own console script and failed until the probe put the venv's `bin/`
  on `PATH`. The artifact always shows the real reason.
- **Coverage is `None`.** The package likely uses a layout the probe could not map to
  an importable module name; `05_coverage.log` will say `No data to report`.
- **`claude: command not found`.** Only the two LLM-dependent steps need it. The probe,
  miner and scorer run without it -- pass `--no-llm`:
  `python3 depscope/pipeline.py repos/retrying --no-llm`.
- **Different `days_since_last_commit` than the recorded run.** Expected — see the drift
  note in section 2.
