# The nine experiments that failed first

DepScope's design is the residue of nine attempts to build something else. Each
attempt tried to make an **engineered agent out-reason a single frontier-model
prompt** on a task that fits in its context window. All nine failed. The code is
kept here because the project's central claim rests on them, and a claim without
its evidence is exactly what this tool exists to catch.

Every experiment used the same model as the baseline it was tested against
(`claude-sonnet-5`), and in each case the naive one-prompt baseline **matched or beat**
the engineered agent.

| # | Directory | The task | Result |
|---|---|---|---|
| 1–4 | `01_spreadsheet/` | Detect seeded formula errors in spreadsheets — across four regimes: an easy sheet, subtle errors, a ~1,000-cell sheet, and values-only arithmetic | Naive prompt scored **F1 = 1.00 in all four**. A deterministic dependency-graph verifier could only tie it. |
| 5 | `02_bug_repro/` | Reproduce-then-fix real GitHub bugs (`pallets/click`), verified against the real fix commits | Ground-truth harness worked (test fails on the buggy parent, passes on the fix), but no gap appeared: terse issues under-specify intent, which defeats both arms equally. |
| 6 | `03_trajectory_audit/` | Audit an agent's final report against its own execution trace — catching claims the trace contradicts | Naive prompt caught **19/20** contradictions even on a **236k-token** trace. Scale did not create the gap we predicted. |
| 7 | `04_codegen/` | Implement a multi-requirement spec with deliberate edge-case traps, checked by a hidden suite | Naive prompt passed **18/18** and reported its own work honestly. |
| 8 | `05_mutation_tests/` | Write tests that kill injected mutants; close the gaps an LLM leaves behind | After fixing *our own* harness bug, naive tests already sat at the true ceiling (100% of killable mutants). All apparent survivors were **equivalent mutants**. |
| 9 | `06_grading/` | Grade essays consistently — the hypothesis being that a memoryless per-essay grader would drift | No drift. Independent per-essay grading was **more** self-consistent (0.25 pts/10) than grading everything in one prompt (0.5). |

## The two results that were lies

Twice we believed we had finally found a gap. Both times the cause was a defect in
our own measurement, not a virtue of our architecture:

- **A stale `.pyc` bytecode cache.** Python keys compiled bytecode on `(mtime, size)`.
  A mutation like `>=` → `<=` changes neither, so within the timestamp resolution the
  interpreter silently re-ran the *original* code. Mutants that had in fact been killed
  were reported as survivors, manufacturing a gap that did not exist.
- **A missing `PATH` entry.** A package's own console script was absent from the probe's
  virtualenv, producing six phantom test failures on a perfectly healthy library.

Both are now pinned by regression tests in `../tests/test_depscope.py`, and both are
why DepScope's scorecards cite a raw log for every number they print.

## What it adds up to

> In 2026 you cannot beat a frontier model on reasoning quality for any task whose
> input fits in its context window. The durable advantage is **evidence acquisition** —
> running the code, measuring the artifact, mining the history — not thinking harder.
>
> And when an engineered agent *appears* to beat a naive baseline, audit the harness
> before believing the architecture. Most apparent wins are measurement bugs.

That conclusion is DepScope's entire design brief: it wins not by out-thinking the
model about a package, but by knowing things about that package the model cannot know.

## Running them

These are preserved research probes, not maintained code. They expect a `claude` CLI on
`PATH` and were run from their original directories; paths inside them are not rewritten
for this folder. They are included as evidence, not as a supported entry point — the
supported project is DepScope itself (`../README.md`).
