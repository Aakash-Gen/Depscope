import re, subprocess
src=open("target.py").read()
prompt=f"""Write a thorough pytest test suite for this module. Import from `target`.
Cover all functions and edge cases. Output ONLY the test file code (no fences).

{src}"""
raw=subprocess.run(["claude","-p","--model","claude-sonnet-5"],input=prompt,
                   capture_output=True,text=True,timeout=200).stdout
code=re.sub(r"^```\w*\n|\n```$","",raw.strip())
code=re.sub(r"```","",code)
open("tests_naive.py","w").write(code)
print("wrote tests_naive.py", len(code),"chars")
