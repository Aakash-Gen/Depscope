import re, subprocess, shutil
import mutate
src=open("target.py").read()
shutil.copy("tests_naive.py","tests_agent.py")
open("tests_agent.py","a").write("\n\nimport target\n")  # ensure module-qualified access works

def claude(p):
    return subprocess.run(["claude","-p","--model","claude-sonnet-5"],input=p,
                          capture_output=True,text=True,timeout=200).stdout

for rnd in range(3):
    res=mutate.score("target.py","tests_agent.py")
    print(f"round {rnd}: score {res['killed']}/{res['total']} = {res['score']:.2%} survived={res['survived']}")
    if res["survived"]==0: break
    cur=open("tests_agent.py").read()
    prompt=f"""These mutation-testing SURVIVORS mean the test suite fails to catch these bugs.
Add pytest tests (that pass on the correct code) which would FAIL if each mutation were applied.
Module is imported as `target`.

SURVIVORS:
{chr(10).join('- '+s for s in res['survivors'])}

MODULE:
{src}

Use `target.FUNC(...)` to call functions. Output ONLY new test functions to APPEND (no fences)."""
    add=claude(prompt); add=re.sub(r"```\w*","",add)
    with open("tests_agent.py","a") as f: f.write("\n\n# --- mutation-targeted tests ---\n"+add+"\n")

final=mutate.score("target.py","tests_agent.py")
print(f"\nFINAL agent score: {final['killed']}/{final['total']} = {final['score']:.2%}")
for s in final.get("survivors",[]): print("  still survived:",s)
