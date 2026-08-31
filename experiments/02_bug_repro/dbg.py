import json, runner
case=[c for c in json.load(open("cases/prepared.json")) if c["commit"]=="e003331"][0]
raw = runner.claude(runner.ask_solution.__wrapped__ if hasattr(runner.ask_solution,'__wrapped__') else "")
# call the real prompt path:
from runner import SRC_BLOCK, claude, extract_json
prompt_preview_keys = list(case["buggy_src"].keys())
print("real src paths:", prompt_preview_keys)
sol = runner.ask_solution(case)
print("parsed?", sol is not None)
if sol:
    print("keys:", list(sol.keys()))
    print("patched_files keys:", list(sol.get("patched_files",{}).keys()))
    print("test snippet:", (sol.get("test","")[:120]))
