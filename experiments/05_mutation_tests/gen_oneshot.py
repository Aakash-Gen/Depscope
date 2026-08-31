import re, subprocess, sys
mod=sys.argv[1]; out=sys.argv[2]
src=open(mod).read()
prompt=f"""Write a thorough pytest test suite for this module. Import it as `import {mod[:-3]}`.
Cover every function, all branches, and edge cases carefully. Output ONLY the test code (no fences)."""+"\n\n"+src
raw=subprocess.run(["claude","-p","--model","claude-sonnet-5"],input=prompt,capture_output=True,text=True,timeout=200).stdout
code=re.sub(r"```\w*","",raw).strip()
open(out,"w").write(code)
print("wrote",out,len(code),"chars")
