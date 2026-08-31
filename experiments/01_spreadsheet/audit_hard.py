"""Run the deterministic verifier on the HARD model and score vs truth."""
from __future__ import annotations

import json

from workbook import Workbook
from verifier import check_row_pattern, check_total, check_col_total

FIRST_COL, LAST_COL, TOTAL_COL = 2, 13, 14
ROW_START, N_ITEMS = 3, 15
ROW_TOTAL = ROW_START + N_ITEMS  # 18


def run(path="data/sheets/model_02_hard.xlsx", truth_path="data/truth/model_02_hard.json"):
    wb = Workbook.load(path)
    values = wb.resolve()
    findings = []

    # line-item rows: horizontal pattern + row totals
    for r in range(ROW_START, ROW_TOTAL):
        findings += check_row_pattern(wb, values, r, FIRST_COL, LAST_COL)
        f = check_total(wb, values, f"N{r}", r, FIRST_COL, LAST_COL)
        if f:
            findings.append(f)

    # grand-total row: vertical column totals across every column B..N
    for c in range(FIRST_COL, TOTAL_COL + 1):
        from openpyxl.utils import get_column_letter
        cell = f"{get_column_letter(c)}{ROW_TOTAL}"
        f = check_col_total(wb, values, cell, c, ROW_START, ROW_TOTAL - 1)
        if f:
            findings.append(f)

    found = {f.cell for f in findings}
    truth = json.load(open(truth_path))
    truth_cells = {e["cell"] for e in truth["errors"]}

    print("=== AGENT (deterministic verifier) on HARD ===")
    for f in findings:
        print(f"  {f.cell} [{f.error_class}] actual={f.actual:g} expected={f.expected:g}")

    tp, fp, fn = found & truth_cells, found - truth_cells, truth_cells - found
    prec = len(tp) / len(found) if found else 0.0
    rec = len(tp) / len(truth_cells) if truth_cells else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    print(f"\n  truth: {sorted(truth_cells)}")
    print(f"  found: {sorted(found)}")
    print(f"  TP={sorted(tp)} FP={sorted(fp)} FN={sorted(fn)}")
    print(f"  precision={prec:.2f} recall={rec:.2f} F1={f1:.2f}")
    return {"precision": prec, "recall": rec, "f1": f1}


if __name__ == "__main__":
    run()
