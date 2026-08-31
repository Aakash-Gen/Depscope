"""Run the reading-only baseline N times to quantify its run-to-run variance.

Our own hot-take is "audit your measurement before you believe your result", so it
would be indefensible to report the baseline from a single sample. The baseline is a
stochastic LLM judgement; DepScope's verdicts are computed from executed artifacts and
are deterministic given the same commits. This script measures both claims.

    python3 eval/baseline_variance.py 3
"""
from __future__ import annotations

import json
import statistics
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "depscope"))
sys.path.insert(0, str(ROOT / "eval"))

from baseline import assess_by_reading   # noqa: E402
from run_eval import TARGETS, GT         # noqa: E402


def main(n: int = 3) -> None:
    runs: list[dict] = []
    for i in range(n):
        verdicts = {}
        for name, path in TARGETS:
            verdicts[name] = (assess_by_reading(str(path)) or {}).get("verdict")
        correct = sum(verdicts[k] == GT[k]["verdict"] for k in GT)
        runs.append({"run": i + 1, "correct": correct, "verdicts": verdicts})
        print(f"run {i+1}: {correct}/{len(GT)} correct", flush=True)

    scores = [r["correct"] for r in runs]
    flips = {k: sorted({r["verdicts"][k] for r in runs}) for k in GT}
    unstable = {k: v for k, v in flips.items() if len(v) > 1}

    summary = {
        "runs": n,
        "scores": scores,
        "mean": round(statistics.mean(scores), 2),
        "min": min(scores), "max": max(scores),
        "stdev": round(statistics.stdev(scores), 2) if n > 1 else 0.0,
        "unstable_packages": unstable,
        "per_run": runs,
    }
    (ROOT / "eval" / "baseline_variance.json").write_text(json.dumps(summary, indent=2))

    print(f"\nbaseline accuracy over {n} runs: {scores} "
          f"(mean {summary['mean']}/{len(GT)}, range {summary['min']}-{summary['max']})")
    if unstable:
        print("packages whose verdict CHANGED between identical runs:")
        for k, v in unstable.items():
            print(f"  {k}: {' / '.join(v)}")
    else:
        print("no verdict changed between runs")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 3)
