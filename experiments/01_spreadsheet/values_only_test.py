"""Pivotal test: can a single LLM prompt verify totals from VALUES alone?
No formulas given. Some column totals are subtly wrong (off by small amounts).
Code recompute catches all; question is whether the LLM's mental arithmetic does."""
import json, random, subprocess, re
random.seed(3)

# Build 8 columns, each 30 numbers + a stated total. Some totals subtly wrong.
cols=[]; truth={}
for k in range(8):
    nums=[round(random.uniform(100,900),2) for _ in range(30)]
    real=round(sum(nums),2)
    if k in (2,5,6):   # 3 wrong totals, off by small amounts
        shown=round(real + random.choice([-1,1])*random.uniform(3,12),2)
        truth[f"C{k}"]="WRONG"
    else:
        shown=real; truth[f"C{k}"]="OK"
    cols.append((nums,shown))

lines=["Each column lists 30 values then a stated TOTAL. Some totals are wrong.",""]
for k,(nums,shown) in enumerate(cols):
    lines.append(f"Column C{k}: "+", ".join(f"{n}" for n in nums))
    lines.append(f"Column C{k} STATED TOTAL: {shown}")
    lines.append("")
prompt="\n".join(lines)+"""
Which columns have an INCORRECT stated total? Reply ONLY as JSON:
{"wrong": ["C0","C3", ...]}  (list only the incorrect ones)"""

proc=subprocess.run(["claude","-p","--model","claude-sonnet-5"],input=prompt,
                    capture_output=True,text=True,timeout=180)
raw=proc.stdout
m=re.search(r'\{.*\}', raw, re.DOTALL)
pred=set(json.loads(m.group(0))["wrong"]) if m else set()
actual_wrong={k for k,v in truth.items() if v=="WRONG"}
tp=pred&actual_wrong; fp=pred-actual_wrong; fn=actual_wrong-pred
prec=len(tp)/len(pred) if pred else 0; rec=len(tp)/len(actual_wrong) if actual_wrong else 0
f1=2*prec*rec/(prec+rec) if prec+rec else 0
print("BASELINE (LLM mental arithmetic on values):")
print(f"  actual wrong: {sorted(actual_wrong)}")
print(f"  LLM said:     {sorted(pred)}")
print(f"  TP={sorted(tp)} FP={sorted(fp)} FN={sorted(fn)}")
print(f"  precision={prec:.2f} recall={rec:.2f} F1={f1:.2f}")
print("\nCODE recompute would be exact: precision=1.00 recall=1.00 F1=1.00")
