"""Spike driver: run the deterministic verifier on model_01 and score vs truth."""
from __future__ import annotations

import json

from workbook import Workbook
from verifier import check_row_pattern, check_total

FIRST_COL, LAST_COL, TOTAL_COL = 2, 13, 14  # B..M, N
DATA_ROWS = [3, 5, 7, 8]  # cumulative, revenue, cost, profit (rows with formulas)
TOTAL_ROWS = [5, 7, 8]    # revenue, cost, profit have FY totals


def run(path: str, truth_path: str) -> None:
    wb = Workbook.load(path)
    values = wb.resolve()

    findings = []
    for row in DATA_ROWS:
        findings += check_row_pattern(wb, values, row, FIRST_COL, LAST_COL)
    for row in TOTAL_ROWS:
        f = check_total(wb, values, f"N{row}", row, FIRST_COL, LAST_COL)
        if f:
            findings.append(f)

    found_cells = {f.cell for f in findings}
    truth = json.load(open(truth_path))
    truth_cells = {e["cell"] for e in truth["errors"]}

    print("=== FINDINGS ===")
    for f in findings:
        print(f"  {f.cell} [{f.error_class}] actual={f.actual:g} expected={f.expected:g}")
        print(f"      {f.detail}")

    tp = found_cells & truth_cells
    fp = found_cells - truth_cells
    fn = truth_cells - found_cells
    prec = len(tp) / len(found_cells) if found_cells else 0.0
    rec = len(tp) / len(truth_cells) if truth_cells else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0

    print("\n=== SCORE vs TRUTH ===")
    print(f"  truth cells:  {sorted(truth_cells)}")
    print(f"  found cells:  {sorted(found_cells)}")
    print(f"  TP={sorted(tp)}  FP={sorted(fp)}  FN={sorted(fn)}")
    print(f"  precision={prec:.2f}  recall={rec:.2f}  F1={f1:.2f}")


if __name__ == "__main__":
    run("data/sheets/model_01.xlsx", "data/truth/model_01.json")
