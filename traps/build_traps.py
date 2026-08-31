"""Build the TRAP packages for DepScope's evaluation.

HONESTY NOTE (brief ground rule #2 -- declare what you added): these three
packages are CONSTRUCTED by this script. Each starts as a copy of a real, healthy
open-source package at a pinned commit; we then seed a specific, documented defect
AND rewrite the README to look excellent. They exist to test one question:

    can a reviewer who only READS the repo tell it is broken?

A human skimming GitHub -- or an LLM given the README, file tree and sampled
source -- sees a polished, confident project. Only executing the code reveals the
truth. Every seeded defect is listed in traps/TRAPS.md and in the manifest below.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPOS = ROOT.parent / "repos"
OUT = ROOT.parent / "trap_repos"

GLOWING_README = """# {name}

[![build](https://img.shields.io/badge/build-passing-brightgreen)]()
[![coverage](https://img.shields.io/badge/coverage-{cov}%25-brightgreen)]()
[![downloads](https://img.shields.io/badge/downloads-2.1M%2Fmonth-blue)]()

**{tagline}**

{name} is a small, dependency-light library used in production by teams that care
about correctness. It is fully type-annotated, {cov}% test-covered, and battle-tested
across Python 3.8-3.12.

## Why {name}?

- **Reliable** - comprehensive test suite, {cov}% coverage, green on every commit
- **Fast** - zero-overhead pure-Python implementation
- **Maintained** - actively developed with a responsive maintainer team
- **Simple** - one obvious way to do it, no configuration required

## Install

```bash
pip install {name}
```

## Quick start

```python
import {module}
```

## Stability

{name} follows semantic versioning strictly. The public API has been stable since
1.0 and we run the full suite against every supported Python version before release.

## License

MIT
"""


def _copy(src: Path, dst: Path) -> None:
    """Copy the package INCLUDING its real git history.

    Keeping the genuine history is the whole point: on every signal a reader can
    see from the outside -- healthy commit cadence, many contributors, real
    releases -- a trap looks like a well-run project. Only executing it reveals
    the defect. Seeded changes are committed on top so the tree is clean.
    """
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns(
        ".depscope_venv", "__pycache__", "*.pyc", ".tox"))


def trap_failing_tests() -> dict:
    """TRAP 1: README claims a green build; the test suite actually fails."""
    name, src = "swiftslug", REPOS / "python-slugify"
    dst = OUT / name
    _copy(src, dst)
    # Seed a real regression in the library code: mishandle the separator argument.
    f = dst / "slugify" / "slugify.py"
    code = f.read_text()
    code = code.replace("QUOTE_PATTERN.sub('', text)", "QUOTE_PATTERN.sub(' ', text)", 1)
    f.write_text(code)
    (dst / "README.md").write_text(GLOWING_README.format(
        name=name, module="slugify", cov=98,
        tagline="Bulletproof unicode slugification for URLs and filenames."))
    return {"package": name, "source": "python-slugify @ v6.1.2",
            "defect": "seeded regression in slugify.py (quote handling) -> real test failures",
            "readme_claim": "98% coverage, green on every commit",
            "detectable_by_reading": False, "truth": "AVOID"}


def trap_coverage_theater() -> dict:
    """TRAP 2: tests run and pass, but assert almost nothing (coverage theater)."""
    name, src = "tidyurl", REPOS / "furl"
    dst = OUT / name
    _copy(src, dst)
    # Replace the real suite with one that executes code but verifies almost nothing:
    # high line coverage, near-zero assertion density, catches no bugs.
    for p in list(dst.rglob("test_*.py")) + list(dst.rglob("tests.py")):
        p.unlink()
    (dst / "test_tidyurl.py").write_text('''"""Test suite for tidyurl."""
import furl


def test_parse_basic():
    f = furl.furl("http://example.com/path?a=1")
    str(f)


def test_parse_query():
    f = furl.furl("http://example.com/?x=1&y=2")
    dict(f.args)
    str(f.query)


def test_path_operations():
    f = furl.furl("http://example.com")
    f.path = "/a/b/c"
    str(f.path)
    f.path.segments


def test_url_join():
    f = furl.furl("http://example.com/a/")
    f.join("b")
    str(f)


def test_scheme_and_host():
    f = furl.furl("https://user:pass@example.com:8080/p")
    f.scheme, f.host, f.port, f.username
    str(f)


def test_copy_and_modify():
    f = furl.furl("http://example.com/x?q=1")
    g = f.copy()
    g.args["q"] = "2"
    str(g)
    assert g is not None


def test_remove_args():
    f = furl.furl("http://example.com/?a=1&b=2")
    f.remove(args=["a"])
    str(f)


def test_fragment():
    f = furl.furl("http://example.com/#frag")
    str(f.fragment)
    f.fragment.path
''')
    (dst / "README.md").write_text(GLOWING_README.format(
        name=name, module="furl", cov=94,
        tagline="Ergonomic URL parsing and manipulation, thoroughly tested."))
    return {"package": name, "source": "furl @ v2.1.2",
            "defect": "coverage theater: tests execute code but assert ~nothing",
            "readme_claim": "94% coverage, comprehensive test suite",
            "detectable_by_reading": False, "truth": "CAUTION"}


def trap_broken_install() -> dict:
    """TRAP 3: polished README, but the package will not install in a clean env."""
    name, src = "fasttable", REPOS / "tabulate"
    dst = OUT / name
    _copy(src, dst)
    # Seed a dependency that cannot resolve -- invisible unless you actually install.
    pyproject = dst / "pyproject.toml"
    if pyproject.exists():
        txt = pyproject.read_text()
        txt = txt.replace("dependencies = [",
                          'dependencies = [\n  "tabulate-core-runtime>=9.9.9",', 1)
        if "tabulate-core-runtime" not in txt:      # fallback if shape differs
            txt = txt.replace("[project]",
                              '[project]\ndependencies = ["tabulate-core-runtime>=9.9.9"]', 1)
        pyproject.write_text(txt)
    (dst / "README.md").write_text(GLOWING_README.format(
        name=name, module="tabulate", cov=91,
        tagline="Pretty-print tabular data with zero friction."))
    return {"package": name, "source": "tabulate @ v0.9.0",
            "defect": "unresolvable pinned dependency -> clean-env install fails",
            "readme_claim": "install with one command, works everywhere",
            "detectable_by_reading": False, "truth": "AVOID"}


def _commit_seed(dst: Path, message: str) -> None:
    """Commit the seeded defect on top of the preserved real history."""
    subprocess.run(["git", "add", "-A"], cwd=dst, capture_output=True)
    subprocess.run(["git", "-c", "user.email=traps@depscope", "-c", "user.name=DepScope Traps",
                    "commit", "-qm", message], cwd=dst, capture_output=True)


def main() -> None:
    OUT.mkdir(exist_ok=True)
    manifest = [trap_failing_tests(), trap_coverage_theater(), trap_broken_install()]
    for m in manifest:
        _commit_seed(OUT / m["package"],
                     f"constructed trap: {m['defect']} (see traps/TRAPS.md)")
    (ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2))
    lines = ["# Constructed trap packages (full disclosure)", "",
             "These three packages were BUILT BY US for evaluation. Each is a copy of a real",
             "package at a pinned commit, with one documented defect seeded and a deliberately",
             "glowing README. They test whether a reviewer who only reads a repo can tell it is",
             "broken. Nothing here is presented as an authentic third-party package.", ""]
    for m in manifest:
        lines += [f"## {m['package']}", f"- built from: {m['source']}",
                  f"- seeded defect: {m['defect']}",
                  f"- README claims: {m['readme_claim']}",
                  f"- correct verdict: **{m['truth']}**", ""]
    (ROOT / "TRAPS.md").write_text("\n".join(lines))
    for m in manifest:
        print(f"built trap: {m['package']:12} <- {m['source']:24} ({m['truth']})")


if __name__ == "__main__":
    main()
