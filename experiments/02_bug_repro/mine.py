"""Mine + validate real bug cases from a target repo.
For each candidate fix commit (touches src+tests): apply the fix's TEST files onto
the buggy parent, run the newly-added tests -> must FAIL; then apply the fix's SRC
files -> must PASS. Validated cases are ground truth for BugProver.
"""
import json, os, re, subprocess, sys

REPO = os.environ["REPO"]
PY = os.environ.get("PYBIN", sys.executable)

def git(*a):
    return subprocess.run(["git","-C",REPO,*a], capture_output=True, text=True)

def changed(commit, path):
    r = git("diff","--name-only",f"{commit}~1",commit,"--",path)
    return [l for l in r.stdout.splitlines() if l.endswith(".py")]

def new_test_funcs(commit, testfile):
    d = git("diff",f"{commit}~1",commit,"--",testfile).stdout
    return re.findall(r"^\+def (test_\w+)", d, re.M)

def run_tests(testfiles, funcs):
    # run specific test funcs across the given files
    ids = []
    for tf in testfiles:
        for fn in funcs:
            ids.append(f"{REPO}/{tf}::{fn}")
    env = dict(os.environ, PYTHONPATH=f"{REPO}/src")
    r = subprocess.run([PY,"-m","pytest","-q",*ids], capture_output=True, text=True, cwd=REPO, env=env)
    return r.returncode, r.stdout[-500:]

def validate(commit):
    src = changed(commit,"src"); tests = changed(commit,"tests")
    if not src or not tests: return None
    funcs=[]; 
    for tf in tests: funcs += new_test_funcs(commit, tf)
    if not funcs: return None
    git("reset","-q","--hard"); git("checkout","-q",f"{commit}~1")
    # bring in the fix's test files (so the new tests exist against buggy src)
    for tf in tests: git("checkout","-q",commit,"--",tf)
    rc_buggy,out_b = run_tests(tests, funcs)
    # now apply src fix
    for sf in src: git("checkout","-q",commit,"--",sf)
    rc_fixed,out_f = run_tests(tests, funcs)
    git("reset","-q","--hard")
    ok = (rc_buggy!=0 and rc_fixed==0)
    return {"commit":commit,"src":src,"tests":tests,"funcs":funcs,
            "buggy_fail":rc_buggy!=0,"fixed_pass":rc_fixed==0,"valid":ok,
            "msg":git("log","-1","--pretty=%s",commit).stdout.strip()}

if __name__=="__main__":
    candidates = sys.argv[1:]
    good=[]
    for c in candidates:
        r=validate(c)
        if r: 
            print(f"{c} valid={r['valid']} buggy_fail={r['buggy_fail']} fixed_pass={r['fixed_pass']} src={len(r['src'])} | {r['msg'][:50]}")
            if r["valid"]: good.append(r)
    json.dump(good, open("cases/validated.json","w"), indent=2)
    print(f"\n{len(good)} validated cases -> cases/validated.json")
