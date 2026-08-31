"""Classify each surviving mutant as KILLABLE (a real test gap) or EQUIVALENT
(unkillable) by searching for a distinguishing input. Reports the true gap."""
import random, re, types, sys
import mutate
random.seed(0)
MOD=sys.argv[1] if len(sys.argv)>1 else "billing.py"
TST=sys.argv[2] if len(sys.argv)>2 else "tests_billing_oneshot.py"
orig=open(MOD).read()
def load(src): m=types.ModuleType("m"); exec(compile(src,"m","exec"),m.__dict__); return m
def funcs(src): return re.findall(r"^def (\w+)\(([^)]*)\)", src, re.M)
def sample(p):
    p=p.strip()
    if p in ("exempt",): return random.choice([True,False])
    if p in ("amount","balance","monthly_spend","unit_price","credit","base","used","included"): return round(random.uniform(0,2000),2)
    if p in ("rate","tax_rate","overage_rate"): return round(random.uniform(0,0.3),3)
    return random.randint(-2,400)  # days/units etc.
def distinguishes(fn,params,mo,mm):
    for _ in range(3000):
        args=[sample(p) for p in params]
        try:
            a=getattr(mo,fn)(*args); b=getattr(mm,fn)(*args)
        except Exception: continue
        if a!=b: return args,a
    return None,None
res=mutate.score(MOD,TST)
print(f"one-shot mutation score: {res['killed']}/{res['total']} = {res['score']:.2%}  survivors={res['survived']}")
mo=load(orig); killable=0; equiv=0
fmap=funcs(orig)
for desc,msrc in res["survivor_mutants"]:
    mm=load(msrc); found=False
    for fn,params in fmap:
        pl=[p for p in params.split(",") if p.strip()]
        args,exp=distinguishes(fn,pl,mo,mm)
        if args is not None:
            print(f"  KILLABLE  {desc[:45]:45}  via {fn}{tuple(args)}")
            killable+=1; found=True; break
    if not found:
        print(f"  equivalent {desc[:45]}")
        equiv+=1
real_total=res['total']-equiv
print(f"\nTRUE gap: {killable} killable survivors the one-shot LLM MISSED")
print(f"one-shot TRUE mutation score (excl. equivalents): {res['killed']}/{real_total} = {res['killed']/real_total:.2%}")
print(f"ceiling reachable: {(res['killed']+killable)}/{real_total} = 100.00%")
