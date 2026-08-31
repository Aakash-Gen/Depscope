# Agent trajectories

Every run writes a JSONL trajectory here, one file per session, so a reviewer can
follow exactly what the agent did and why. Nothing is summarised after the fact —
these are written as the run happens.

```bash
python3 depscope/pipeline.py trap_repos/swiftslug   # writes assess_swiftslug.jsonl
python3 eval/run_eval.py baseline                   # writes baseline_<pkg>.jsonl
```

## The two agents

| session file | agent | what it may do |
|---|---|---|
| `assess_<pkg>.jsonl` | **DepScope** | executes the package, mines history, extracts README claims, verifies them, scores |
| `baseline_<pkg>.jsonl` | **reading-only baseline** | reads README, tree, metadata and source excerpts; may not execute anything |

## Record types

| `event` | meaning |
|---|---|
| `action` | a deterministic step (probe, history mining, scoring, verification, human checkpoint) |
| `prompt` | a prompt sent to the model, with its length and first 4000 chars |
| `reply` | the model's reply and whether it parsed |
| `retry` | an attempt failed — transport error or unparseable JSON — with the reason |
| `failed` | all attempts exhausted; the caller raises rather than silently returning "no claims" |

## Worked example: catching the `swiftslug` trap

`assess_swiftslug.jsonl`, in order:

```
[action] start             package=swiftslug, use_llm=True
[action] execution_probe   installed=True, tests_passed=80, tests_failed=1,
                           coverage_pct=88.0, assertion_density=1.56
[action] history_miner     days_since_last_commit=235, bus_factor=1, commits_last_year=16
[action] scorer            verdict=AVOID, overall=6.7,
                           findings=[... ['Tests pass', 1, 'critical'] ...]
[prompt] read_claims       model=claude-sonnet-5, chars=1713
[reply ] read_claims       attempt=1, parsed_ok=True
[action] read_claims       claims=9
[action] claim_verifier    claims_examined=9, contradicted_by_evidence=2,
                           rejected_unverifiable=4
[action] human_checkpoint  verdict=AVOID — advisory; a developer signs off
```

Read it as a chain of evidence. The probe **ran the suite** and found one failing
test; that single fact is what makes the verdict `AVOID`, and it is the fact the
reading-only baseline could not obtain (it called this package `CAUTION`). The model
is then asked to do the one job it is trusted with — reading prose — and returns nine
claims from a README boasting "98% coverage, green on every commit". The verifier
checks each against the artifacts: two are **contradicted by measurement**, four are
unverifiable marketing and are struck rather than repeated. The run ends at a human
checkpoint, because DepScope advises and a person decides.

## Retries and failure

`llm.ask_json` retries up to three times, appending a corrective instruction when a
reply cannot be parsed, and logs every attempt. If all attempts fail it raises
`LLMUnavailable`. This is deliberate: an earlier version swallowed the error and
returned "no claims", which silently disarmed the Claim Verifier and made a package
look *cleaner* than the evidence justified. A missing model must be an audible
failure, never a clean bill of health.
