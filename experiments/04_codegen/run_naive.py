import json,re,subprocess,sys
spec=open("spec.txt").read()
raw=subprocess.run(["claude","-p","--model","claude-sonnet-5"],input=spec,
                   capture_output=True,text=True,timeout=240).stdout
m=re.search(r"\{.*\}",raw,re.DOTALL); d=json.loads(m.group(0))
open("solution.py","w").write(d["code"])
print("CLAIM:",d.get("claim","")[:200])
r=subprocess.run([sys.executable,"hidden_tests.py","solution.py"],capture_output=True,text=True)
print(r.stdout)
