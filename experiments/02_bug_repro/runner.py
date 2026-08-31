"""Milestone-1 gap test: baseline (one-shot, no execution) vs agent
(execution-in-the-loop). Everything else held equal -- both get the issue text
and the buggy source file(s). The ONLY difference is whether the solver sees test
results and iterates. Scored by the GOLD test (real fix commit) = ground truth.
"""
import json, os, re, subprocess, sys, tempfile

REPO = os.environ["REPO"]
PYBIN = os.environ.get("PYBIN", "/Users/agen/Micro1/.venv/bin/python")
MODEL = os.environ.get("MODEL", "claude-sonnet-5")
AGENT_TEST = os.path.join(REPO, "tests", "_agent_probe_test.py")


def git(*a): return subprocess.run(["git", "-C", REPO, *a], capture_output=True, text=True)


def reset_to_parent(case):
    git("reset", "-q", "--hard")
    git("checkout", "-q", f"{case['commit']}~1")


def overlay(files: dict):
    for path, content in files.items():
        with open(os.path.join(REPO, path), "w") as f:
            f.write(content)


def run_pytest(ids):
    env = dict(os.environ, PYTHONPATH=f"{REPO}/src")
    r = subprocess.run([PYBIN, "-m", "pytest", "-q", "--no-header", *ids],
                       capture_output=True, text=True, cwd=REPO, env=env)
    return r.returncode, (r.stdout + r.stderr)[-1500:]


def claude(prompt):
    r = subprocess.run(["claude", "-p", "--model", MODEL], input=prompt,
                       capture_output=True, text=True, timeout=240)
    return r.stdout


def extract_json(raw):
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if not m: return None
    try: return json.loads(m.group(0))
    except json.JSONDecodeError:
        # tolerate ```json fences already stripped by regex; try last-ditch
        return None


def gold_ids(case):
    return [f"{REPO}/{tf}::{fn}" for tf in case["tests"] for fn in case["funcs"]]


def score_patch(case, patched_files):
    """Apply model's patched src onto buggy state WITH gold tests present; run gold."""
    reset_to_parent(case)
    git("checkout", "-q", case["commit"], "--", *case["tests"])  # gold tests present
    overlay(patched_files)
    rc, out = run_pytest(gold_ids(case))
    return rc == 0, out


SRC_BLOCK = lambda case: "\n\n".join(
    f"=== FILE: {p} ===\n{c}" for p, c in case["buggy_src"].items())


def ask_solution(case, feedback=""):
    prompt = f"""You are fixing a bug in the `click` library.

ISSUE: {case['issue']}

The buggy source file(s) are below. Produce:
1. a pytest test function that REPRODUCES the bug (fails now, passes once fixed)
2. the FULL corrected content of each source file you change.

{feedback}

Respond ONLY as JSON:
{{"test": "def test_bug():\\n    ...", "patched_files": {{"src/click/xxx.py": "<full file>"}}}}

{SRC_BLOCK(case)}
"""
    return extract_json(claude(prompt))


def run_baseline(case):
    sol = ask_solution(case)
    if not sol or "patched_files" not in sol:
        return {"resolved": False, "note": "no parseable solution"}
    ok, _ = score_patch(case, sol["patched_files"])
    return {"resolved": ok}


def run_agent(case, max_iter=3):
    """Execution-in-the-loop: write test, RUN it (must fail on buggy), then fix,
    RUN gold+own test, iterate on failure."""
    feedback = ""
    last = None
    for it in range(max_iter):
        sol = ask_solution(case, feedback)
        if not sol or "patched_files" not in sol or "test" not in sol:
            feedback = "Previous reply was not valid JSON. Return exactly the JSON schema."
            continue
        last = sol
        # 1) verify the test is DISCRIMINATING: fails on buggy src
        reset_to_parent(case)
        with open(AGENT_TEST, "w") as f:
            f.write("import click\nimport pytest\n" + sol["test"] + "\n")
        rc_buggy, out_buggy = run_pytest([AGENT_TEST])
        # 2) apply fix, rerun own test
        overlay(sol["patched_files"])
        rc_fixed, out_fixed = run_pytest([AGENT_TEST])
        discriminating = (rc_buggy != 0 and rc_fixed == 0)
        if discriminating:
            break
        feedback = (f"Your test/fix did not work. On BUGGY code the test should FAIL "
                    f"but pytest rc={rc_buggy}:\n{out_buggy[-600:]}\n"
                    f"After your fix the test should PASS but rc={rc_fixed}:\n{out_fixed[-600:]}\n"
                    f"Fix the test so it reproduces the bug, and correct the patch.")
    if os.path.exists(AGENT_TEST): os.remove(AGENT_TEST)
    if not last or "patched_files" not in last:
        return {"resolved": False, "iters": max_iter}
    ok, _ = score_patch(case, last["patched_files"])
    return {"resolved": ok}


if __name__ == "__main__":
    cases = json.load(open("cases/prepared.json"))
    pick = sys.argv[1:] or [c["commit"] for c in cases]
    cases = [c for c in cases if c["commit"] in pick]
    rows = []
    for c in cases:
        b = run_baseline(c)
        a = run_agent(c)
        git("reset", "-q", "--hard"); git("checkout", "-q", "8.1.7")
        rows.append((c["commit"], b["resolved"], a["resolved"], c["issue"][:45]))
        print(f"{c['commit']} | baseline={b['resolved']!s:5} | agent={a['resolved']!s:5} | {c['issue'][:45]}")
    bw = sum(r[1] for r in rows); aw = sum(r[2] for r in rows)
    print(f"\nRESOLVE RATE  baseline={bw}/{len(rows)}  agent={aw}/{len(rows)}")
    json.dump(rows, open("cases/m1_results.json", "w"), indent=2)
