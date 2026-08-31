"""Deterministic mutation engine: inject small bugs into target.py, run a test
file against each mutant, report which mutants are KILLED (tests fail) vs SURVIVE.
Mutation score = killed / total. This is the objective quality metric.
"""
import os, re, subprocess, sys, tempfile

PYBIN = "/Users/agen/Micro1/.venv/bin/python"

# ordered so multi-char ops are tried before their prefixes
RULES = [
    (r">=", "<="), (r"<=", ">="), (r"==", "!="), (r"!=", "=="),
    (r">=", ">"),  (r"<=", "<"),
    (r"(?<![<>=!])>(?![=])", ">="), (r"(?<![<>=!])<(?![=])", "<="),
    (r"\band\b", "or"), (r"\bor\b", "and"),
    (r"\bTrue\b", "False"), (r"\bFalse\b", "True"),
    (r"(?<![*/])\*(?![*/])", "/"), (r"(?<![*/])/(?![*/])", "*"),
    (r"(?<![-+\d])\+(?![-+=])", "-"), (r"(?<![-+\d])-(?![-+=])", "+"),
]


def generate_mutants(src: str):
    mutants = []
    lines = src.split("\n")
    in_doc = False
    for li, line in enumerate(lines):
        stripped = line.strip()
        # track triple-quoted docstring/string blocks and skip them
        triples = stripped.count('"""') + stripped.count("'''")
        if in_doc:
            if triples % 2 == 1:
                in_doc = False
            continue
        if triples == 1:
            in_doc = True
            continue
        if stripped.startswith(("#", '"""', "'''", '"', "'")) or triples >= 2:
            continue
        # strip inline comments so hyphens/operators in comments aren't mutated
        code_part = line.split("#", 1)[0]
        line = code_part if code_part.strip() else line
        if not line.strip():
            continue
        for pat, repl in RULES:
            for m in re.finditer(pat, line):
                s, e = m.span()
                new_line = line[:s] + repl + line[e:]
                if new_line == line:
                    continue
                new_lines = lines.copy()
                new_lines[li] = new_line
                desc = f"L{li+1}: '{line.strip()[:40]}' [{m.group(0)}->{repl}]"
                mutants.append((len(mutants), "\n".join(new_lines), desc))
    return mutants


def run_tests(target_src: str, target_path: str, test_path: str) -> bool:
    """Write mutated target, run the test file. Return True if tests PASS.

    Guards against Python's mtime/size-based .pyc cache reusing stale bytecode
    when a same-size mutation (e.g. '>=' -> '<=') is written within the mtime
    resolution: disable bytecode writing AND purge any cached .pyc first.
    """
    d = os.path.dirname(os.path.abspath(target_path))
    with open(target_path, "w") as f:
        f.write(target_src)
    cache = os.path.join(d, "__pycache__")
    if os.path.isdir(cache):
        for fn in os.listdir(cache):
            try: os.remove(os.path.join(cache, fn))
            except OSError: pass
    env = dict(os.environ, PYTHONPATH=d, PYTHONDONTWRITEBYTECODE="1")
    r = subprocess.run([PYBIN, "-B", "-m", "pytest", "-q", "--no-header", "-x",
                        "-p", "no:cacheprovider", test_path],
                       capture_output=True, text=True, env=env, cwd=d)
    return r.returncode == 0


def score(target_path: str, test_path: str, verbose=False):
    orig = open(target_path).read()
    try:
        # sanity: tests must pass on the ORIGINAL code
        if not run_tests(orig, target_path, test_path):
            return {"error": "tests fail on original code"}
        mutants = generate_mutants(orig)
        killed, survivors, survivor_srcs = 0, [], []
        for mid, msrc, desc in mutants:
            passed = run_tests(msrc, target_path, test_path)
            if not passed:
                killed += 1           # tests failed on mutant => caught the bug
            else:
                survivors.append(desc)  # mutant survived => test gap
                survivor_srcs.append((desc, msrc))
        return {"total": len(mutants), "killed": killed,
                "survived": len(survivors), "score": killed / len(mutants) if mutants else 0.0,
                "survivors": survivors, "survivor_mutants": survivor_srcs}
    finally:
        with open(target_path, "w") as f:
            f.write(orig)


if __name__ == "__main__":
    tgt = sys.argv[1] if len(sys.argv) > 1 else "target.py"
    tst = sys.argv[2] if len(sys.argv) > 2 else "tests_naive.py"
    res = score(tgt, tst)
    print(res if "error" in res else
          f"mutation score: {res['killed']}/{res['total']} = {res['score']:.2%}  survived={res['survived']}")
    for s in res.get("survivors", [])[:20]:
        print("  SURVIVED:", s)
