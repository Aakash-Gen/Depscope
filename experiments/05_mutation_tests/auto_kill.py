"""Engineered killer: for each surviving mutant, auto-find a distinguishing input
(run original vs mutant), then synthesize a guaranteed-killing test. Deterministic,
no LLM guessing. Proves the achievable ceiling."""
import random, re, types, shutil
import mutate
random.seed(0)
orig=open("target.py").read()

def load(src):
    m=types.ModuleType("m"); exec(compile(src,"m","exec"),m.__dict__); return m

def funcs(src): return re.findall(r"^def (\w+)\(([^)]*)\)", src, re.M)

def sample(param):
    p=param.strip()
    if p in ("is_member","express","banned"): return random.choice([True,False])
    if p in ("unit_price","weight","amount"): return round(random.uniform(0,50),1)
    return random.randint(-5,200)  # qty, age, score, days_late

def find_distinguishing(fn, params, mo, mm):
    for _ in range(2000):
        args=[sample(p) for p in params]
        try:
            a=getattr(mo,fn)(*args); b=getattr(mm,fn)(*args)
        except Exception: continue
        if a!=b: return args,a
    return None,None

def main():
    shutil.copy("tests_naive.py","tests_auto.py"); open("tests_auto.py","a").write("\n\nimport target\n")
    res=mutate.score("target.py","tests_auto.py")
    print(f"start: {res['killed']}/{res['total']} = {res['score']:.2%} survivors={res['survived']}")
    mo=load(orig); added=[]
    for i,(desc,msrc) in enumerate(res["survivor_mutants"]):
        mm=load(msrc)
        # find which function the changed line is in
        chline=[lo for lo,lm in zip(orig.split("\n"),msrc.split("\n")) if lo!=lm][0]
        # try all functions, pick one that distinguishes
        killed=False
        for fn,params in funcs(orig):
            plist=[p for p in params.split(",") if p.strip()]
            args,expected=find_distinguishing(fn,plist,mo,mm)
            if args is not None:
                added.append(f"def test_auto_kill_{i}():\n    assert target.{fn}({', '.join(map(repr,args))}) == {expected!r}")
                print(f"  KILLED {desc}  via {fn}{tuple(args)} == {expected}")
                killed=True; break
        if not killed: print(f"  EQUIVALENT (no distinguishing input): {desc}")
    open("tests_auto.py","a").write("\n\n# --- auto distinguishing-input tests ---\n"+"\n\n".join(added)+"\n")
    final=mutate.score("target.py","tests_auto.py")
    print(f"\nFINAL engineered score: {final['killed']}/{final['total']} = {final['score']:.2%} survivors={final['survived']}")
main()
