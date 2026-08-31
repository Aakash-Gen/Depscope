"""Generic deterministic auditor: infers band dims from arguments."""
import json, sys
from openpyxl.utils import get_column_letter as gcl
from workbook import Workbook
from verifier import check_row_pattern, check_total, check_col_total

def run(path, truth_path, first_col, last_col, total_col, row_start, row_total):
    wb = Workbook.load(path); values = wb.resolve(); findings=[]
    for r in range(row_start, row_total):
        findings += check_row_pattern(wb, values, r, first_col, last_col)
        f = check_total(wb, values, f"{gcl(total_col)}{r}", r, first_col, last_col)
        if f: findings.append(f)
    for c in range(first_col, total_col+1):
        f = check_col_total(wb, values, f"{gcl(c)}{row_total}", c, row_start, row_total-1)
        if f: findings.append(f)
    found={f.cell for f in findings}
    truth=json.load(open(truth_path)); tc={e["cell"] for e in truth["errors"]}
    tp,fp,fn=found&tc,found-tc,tc-found
    prec=len(tp)/len(found) if found else 0; rec=len(tp)/len(tc) if tc else 0
    f1=2*prec*rec/(prec+rec) if prec+rec else 0
    print("=== AGENT (deterministic) ===")
    print(f"  found: {sorted(found)}")
    print(f"  TP={sorted(tp)} FP={sorted(fp)} FN={sorted(fn)}")
    print(f"  precision={prec:.2f} recall={rec:.2f} F1={f1:.2f}")

if __name__=="__main__":
    # big sheet dims
    run("data/sheets/model_03_big.xlsx","data/truth/model_03_big.json",2,25,26,3,43)
