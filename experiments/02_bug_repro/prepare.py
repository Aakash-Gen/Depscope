"""Enrich validated cases with issue text + buggy source file contents (at parent)."""
import json, os, subprocess
REPO=os.environ["REPO"]
def git(*a): return subprocess.run(["git","-C",REPO,*a],capture_output=True,text=True)
cases=json.load(open("cases/validated.json"))
git("reset","-q","--hard")
out=[]
for c in cases:
    commit=c["commit"]
    git("checkout","-q",f"{commit}~1")
    buggy={}
    for sf in c["src"]:
        p=os.path.join(REPO,sf)
        buggy[sf]=open(p).read()
    # gold test source (from fix) for reference/scoring
    git("checkout","-q",commit,"--",*c["tests"])
    gold_tests={tf:open(os.path.join(REPO,tf)).read() for tf in c["tests"]}
    git("reset","-q","--hard")
    out.append({**c,"issue":c["msg"],"buggy_src":buggy,"gold_tests":gold_tests})
json.dump(out,open("cases/prepared.json","w"),indent=2)
print(f"prepared {len(out)} cases; src sizes:",
      {c['commit']:sum(len(v) for v in c['buggy_src'].values()) for c in out})
