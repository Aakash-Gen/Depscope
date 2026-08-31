"""Baseline: a single general-purpose LLM prompt over the sheet text.

Represents today's approach -- paste the spreadsheet into a chatbot and ask it
to find the errors. One pass, no tools, no code verification. Same scoring as
the agent solution so the comparison is fair.

LLM is invoked via the authenticated `claude` CLI in print mode (no API key
needed in this environment). Model/temperature pinned for reproducibility.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys

from sheet_to_text import dump

PROMPT = """You are auditing a spreadsheet financial model for errors.
Below is every non-empty cell as `cell | formula | value`.

Find cells that contain an error: broken/short SUM ranges, hardcoded values that
should be formulas, formulas inconsistent with their row/column peers, wrong cell
references, or totals that don't match their components.

Respond with ONLY a JSON array of objects, no prose:
[{{"cell": "A1", "reason": "..."}}]

SHEET:
{sheet}
"""


def call_llm(prompt: str) -> str:
    proc = subprocess.run(
        ["claude", "-p", "--model", "claude-sonnet-5"],
        input=prompt, capture_output=True, text=True, timeout=180,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"claude CLI failed: {proc.stderr[:500]}")
    return proc.stdout


def parse_cells(raw: str) -> list[dict]:
    m = re.search(r"\[.*\]", raw, re.DOTALL)
    if not m:
        return []
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return []


def run(xlsx_path: str, truth_path: str) -> dict:
    sheet_text = dump(xlsx_path)
    raw = call_llm(PROMPT.format(sheet=sheet_text))
    flagged = parse_cells(raw)
    found = {f.get("cell", "").upper() for f in flagged if f.get("cell")}

    truth = json.load(open(truth_path))
    truth_cells = {e["cell"] for e in truth["errors"]}

    tp = found & truth_cells
    fp = found - truth_cells
    fn = truth_cells - found
    prec = len(tp) / len(found) if found else 0.0
    rec = len(tp) / len(truth_cells) if truth_cells else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0

    print("=== BASELINE (single prompt) ===")
    for f in flagged:
        print(f"  flagged {f.get('cell')}: {f.get('reason','')[:80]}")
    print(f"\n  truth:  {sorted(truth_cells)}")
    print(f"  found:  {sorted(found)}")
    print(f"  TP={sorted(tp)}  FP={sorted(fp)}  FN={sorted(fn)}")
    print(f"  precision={prec:.2f}  recall={rec:.2f}  F1={f1:.2f}")
    return {"precision": prec, "recall": rec, "f1": f1,
            "tp": sorted(tp), "fp": sorted(fp), "fn": sorted(fn)}


if __name__ == "__main__":
    xlsx = sys.argv[1] if len(sys.argv) > 1 else "data/sheets/model_01.xlsx"
    truth = sys.argv[2] if len(sys.argv) > 2 else "data/truth/model_01.json"
    run(xlsx, truth)
