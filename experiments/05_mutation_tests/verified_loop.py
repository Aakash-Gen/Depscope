"""Verified mutation-killing loop (core of the product).
For each surviving mutant, ask the LLM for a test, then VERIFY it kills the mutant
(passes on original, FAILS on the mutant). Only keep verified-killing tests; retry
with the diff as feedback. This is what a single prompt cannot do."""
import re, subprocess, shutil, os
import mutate

TARGET = "target.py"
PYBIN = mutate.PYBIN
orig = open(TARGET).read()


def claude(p):
    return subprocess.run(["claude", "-p", "--model", "claude-sonnet-5"], input=p,
                          capture_output=True, text=True, timeout=200).stdout


def run_file_against(src, testcode):
    """Return True if pytest PASSES on given target src with the given standalone test code."""
    with open(TARGET, "w") as f: f.write(src)
    with open("_probe_test.py", "w") as f: f.write("import target\n" + testcode)
    env = dict(os.environ, PYTHONPATH=os.getcwd())
    r = subprocess.run([PYBIN, "-m", "pytest", "-q", "--no-header", "_probe_test.py"],
                       capture_output=True, text=True, env=env, cwd=os.getcwd())
    return r.returncode == 0, r.stdout[-400:]


def diff(a, b):
    for la, lb in zip(a.split("\n"), b.split("\n")):
        if la != lb: return f"original: {la.strip()}\nmutant:   {lb.strip()}"
    return ""


def main():
    shutil.copy("tests_naive.py", "tests_verified.py")
    open("tests_verified.py", "a").write("\n\nimport target\n")
    res = mutate.score(TARGET, "tests_verified.py")
    print(f"start: {res['killed']}/{res['total']} = {res['score']:.2%}  survivors={res['survived']}")
    added = []
    for desc, msrc in res["survivor_mutants"]:
        feedback = ""
        for attempt in range(3):
            prompt = f"""Write ONE pytest test function (name it uniquely) that distinguishes
correct code from a buggy mutant. It must PASS on correct code and FAIL on the mutant.
Call functions as `target.FUNC(...)`.

The mutation ({desc}):
{diff(orig, msrc)}

MODULE:
{orig}
{feedback}
Output ONLY the single test function, no fences."""
            test = re.sub(r"```\w*", "", claude(prompt)).strip()
            ok_orig, _ = run_file_against(orig, test)
            ok_mut, out = run_file_against(msrc, test)
            if ok_orig and not ok_mut:
                added.append(test); print(f"  KILLED {desc}  (attempt {attempt+1})"); break
            feedback = (f"\nYour test did not work: pass_on_correct={ok_orig}, "
                        f"pass_on_mutant={ok_mut} (must be True then False). Fix it.\n")
        else:
            print(f"  UNKILLED (maybe equivalent): {desc}")
    with open(TARGET, "w") as f: f.write(orig)
    if os.path.exists("_probe_test.py"): os.remove("_probe_test.py")
    with open("tests_verified.py", "a") as f:
        f.write("\n\n# --- verified mutation-killing tests ---\n" + "\n\n".join(added) + "\n")
    final = mutate.score(TARGET, "tests_verified.py")
    print(f"\nFINAL verified score: {final['killed']}/{final['total']} = {final['score']:.2%}  survivors={final['survived']}")
    for s in final.get("survivors", []): print("  still survived:", s)


if __name__ == "__main__":
    main()
