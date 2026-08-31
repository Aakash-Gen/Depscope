import json, runner
case=[c for c in json.load(open("cases/prepared.json")) if c["commit"]=="e003331"][0]
sol=runner.ask_solution(case)
ok,out=runner.score_patch(case, sol["patched_files"])
print("GOLD ids:", runner.gold_ids(case))
print("resolved:", ok)
print("---- pytest output ----")
print(out[-800:])
# show the model's fix region
pf=sol["patched_files"]["src/click/types.py"]
import re
m=re.search(r"def to_info_dict.*?(?=\n    def )", pf, re.S)
print("---- model to_info_dict ----")
print(m.group(0)[:500] if m else "not found")
