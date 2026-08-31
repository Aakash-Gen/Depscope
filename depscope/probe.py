"""Execution Probe: the evidence-acquisition core of DepScope.

Everything a README cannot tell you: does this package actually install in a fresh
environment? Do its tests actually pass at this commit? Is its coverage real?

Every function here returns structured evidence AND writes a raw artifact (log file)
that any claim in the final report must cite. No LLM is involved at this layer --
these are facts, deterministically re-derivable by a judge on a clean machine.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path

ARTIFACT_ROOT = Path(__file__).resolve().parent.parent / "artifacts"
DEFAULT_TIMEOUT = 300


@dataclass
class Artifact:
    """A saved piece of raw evidence a report line can cite."""
    name: str
    path: str
    exit_code: int | None = None
    duration_s: float = 0.0

    @property
    def citation(self) -> str:
        return f"artifacts/{Path(self.path).parent.name}/{Path(self.path).name}"


@dataclass
class ProbeResult:
    repo: str
    commit: str
    installed: bool | None = None
    tests_ran: bool | None = None
    tests_passed: int | None = None
    tests_failed: int | None = None
    tests_errored: int | None = None
    coverage_pct: float | None = None
    assertion_density: float | None = None   # asserts per test function
    notes: list[str] = field(default_factory=list)
    artifacts: list[Artifact] = field(default_factory=list)

    def cite(self, name: str) -> str:
        for a in self.artifacts:
            if a.name == name:
                return a.citation
        return "(no artifact)"

    def to_dict(self) -> dict:
        d = asdict(self)
        d["artifacts"] = [asdict(a) for a in self.artifacts]
        return d


def _run(cmd: list[str], cwd: str, log_path: Path, timeout: int = DEFAULT_TIMEOUT,
         env: dict | None = None) -> Artifact:
    """Run a command, tee everything to a log artifact, never raise."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    started = time.time()
    header = f"$ {' '.join(cmd)}\n(cwd={cwd})\n{'-'*70}\n"
    try:
        proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                              timeout=timeout, env=env)
        body, code = proc.stdout + proc.stderr, proc.returncode
    except subprocess.TimeoutExpired:
        body, code = f"<TIMEOUT after {timeout}s>", None
    except Exception as exc:  # noqa: BLE001
        body, code = f"<LAUNCH FAILURE: {exc}>", None
    dur = time.time() - started
    log_path.write_text(header + body + f"\n{'-'*70}\nexit={code} duration={dur:.1f}s\n")
    return Artifact(log_path.stem, str(log_path), code, dur)


def _parse_pytest(text: str) -> tuple[int | None, int | None, int | None]:
    """Extract passed/failed/errored counts from a pytest summary line."""
    passed = failed = errored = None
    for kind, pat in (("p", r"(\d+) passed"), ("f", r"(\d+) failed"), ("e", r"(\d+) error")):
        m = re.findall(pat, text)
        if m:
            val = int(m[-1])
            if kind == "p": passed = val
            elif kind == "f": failed = val
            else: errored = val
    if passed is None and failed is None and errored is None:
        return None, None, None
    return passed or 0, failed or 0, errored or 0


def _test_files(repo_dir: Path) -> list[Path]:
    """Locate test files, tolerating non-standard layouts (e.g. a bare test.py)."""
    seen, out = set(), []
    patterns = ("test_*.py", "*_test.py", "test.py", "tests.py")
    for pat in patterns:
        for p in repo_dir.rglob(pat):
            if any(x in p.parts for x in (".depscope_venv", ".venv", "site-packages", "build")):
                continue
            if p not in seen:
                seen.add(p)
                out.append(p)
    return out


def _assertion_density(repo_dir: Path) -> float | None:
    """Cheap 'coverage theater' signal: assertions per test function.

    A suite that executes a lot of code but asserts almost nothing inflates the
    coverage number while catching nothing. Reading a README can never reveal this.
    Counts bare asserts, unittest helpers, pytest.raises, and helper-style
    assert_equal(...) calls used by many older suites.
    """
    tests, asserts = 0, 0
    for p in _test_files(repo_dir):
        try:
            src = p.read_text(errors="ignore")
        except OSError:
            continue
        tests += len(re.findall(r"^\s*def test\w*", src, re.M))
        asserts += len(re.findall(r"(?<![\w.])assert\s", src))          # bare assert
        asserts += len(re.findall(r"(?:self\.)?assert\w+\s*\(", src))   # unittest + helpers
        asserts += len(re.findall(r"pytest\.raises|nose\.tools", src))
    if tests == 0:
        return None
    return round(asserts / tests, 2)


TEST_REQ_FILES = (
    "test-requirements.txt", "requirements-test.txt", "requirements_test.txt",
    "dev-requirements.txt", "requirements-dev.txt", "requirements_dev.txt",
    "requirements.txt",
)


def probe(repo_dir: str, name: str | None = None, timeout: int = DEFAULT_TIMEOUT) -> ProbeResult:
    """Full execution probe of one repository checkout."""
    repo_path = Path(repo_dir).resolve()
    name = name or repo_path.name
    art_dir = ARTIFACT_ROOT / name
    if art_dir.exists():
        shutil.rmtree(art_dir)
    art_dir.mkdir(parents=True, exist_ok=True)

    commit = subprocess.run(["git", "-C", str(repo_path), "rev-parse", "HEAD"],
                            capture_output=True, text=True).stdout.strip()[:12]
    res = ProbeResult(repo=name, commit=commit)

    # 1. fresh virtual environment (isolation: no host packages leak in)
    venv = repo_path / ".depscope_venv"
    if venv.exists():
        shutil.rmtree(venv)
    a = _run([sys.executable, "-m", "venv", str(venv)], str(repo_path), art_dir / "01_venv.log", timeout)
    res.artifacts.append(a)
    py = str(venv / "bin" / "python")
    if a.exit_code != 0 or not Path(py).exists():
        res.notes.append("virtualenv creation failed")
        res.installed = False
        return res

    # 2. install the package itself from source (the real 'does it install' test)
    a = _run([py, "-m", "pip", "install", "--quiet", "--disable-pip-version-check", "."],
             str(repo_path), art_dir / "02_install.log", timeout)
    res.artifacts.append(a)
    res.installed = (a.exit_code == 0)
    if not res.installed:
        res.notes.append("package failed to install from source in a clean env")

    # 3. install test tooling
    a = _run([py, "-m", "pip", "install", "--quiet", "--disable-pip-version-check",
              "pytest", "coverage"], str(repo_path), art_dir / "03_testdeps.log", timeout)
    res.artifacts.append(a)

    # 3b. project-declared test dependencies: extras first, then requirement files.
    # A project that cannot get its own test deps installed is itself a signal.
    # NOTE: pip exits 0 for an UNKNOWN extra (it only warns), so "first success"
    # is not evidence the extra existed. Try every common name.
    declared = set(re.findall(r"^\s*(\w+)\s*=\s*\[",
                              (repo_path / "pyproject.toml").read_text(errors="ignore")
                              if (repo_path / "pyproject.toml").exists() else "", re.M))
    for extra in {"test", "tests", "dev", "testing"} | {d for d in declared
                                                        if "test" in d or "dev" in d}:
        a2 = _run([py, "-m", "pip", "install", "--quiet", "--disable-pip-version-check",
                   f".[{extra}]"], str(repo_path),
                  art_dir / f"03b_extra_{extra}.log", timeout)
        if a2.exit_code == 0 and "does not provide the extra" not in Path(a2.path).read_text():
            res.artifacts.append(a2)
            res.notes.append(f"installed test extra '[{extra}]'")
    for rf in TEST_REQ_FILES:
        if (repo_path / rf).exists():
            a3 = _run([py, "-m", "pip", "install", "--quiet", "--disable-pip-version-check",
                       "-r", rf], str(repo_path), art_dir / f"03c_{rf}.log", timeout)
            res.artifacts.append(a3)
            if a3.exit_code == 0:
                res.notes.append(f"installed {rf}")

    # 4. run the test suite under coverage.
    # Scope coverage to the package source, not the whole tree (test files and the
    # venv would otherwise distort the number).
    # Purge any stale bytecode before running. We check out different commits into
    # the same tree, and Python's .pyc cache keys on (mtime, size) -- a same-size
    # edit written within the timestamp resolution can silently execute the OLD
    # code. That exact failure once faked a whole experimental result for us, so
    # the cache is cleared here AND bytecode writing is disabled below.
    for cache in repo_path.rglob("__pycache__"):
        if ".depscope_venv" not in cache.parts:
            shutil.rmtree(cache, ignore_errors=True)

    # The venv's bin/ MUST be on PATH: packages that install console scripts test
    # them by invoking the command. Without this their own CLI is missing and a
    # healthy package looks broken (this bit us on python-dotenv).
    env = dict(os.environ,
               PYTHONDONTWRITEBYTECODE="1",
               VIRTUAL_ENV=str(venv),
               PATH=f"{venv / 'bin'}{os.pathsep}{os.environ.get('PATH', '')}")
    # Identify the importable package name(s), supporting both flat and src/ layouts.
    # We pass NAMES (not paths) to coverage so it measures the package as imported,
    # whether that resolves to the source tree or to site-packages.
    search_dirs = [repo_path] + ([repo_path / "src"] if (repo_path / "src").is_dir() else [])
    pkg_names = [d.name for base in search_dirs for d in base.iterdir()
                 if d.is_dir() and (d / "__init__.py").exists()
                 and d.name not in ("tests", "test", "docs")]
    src_arg = ",".join(dict.fromkeys(pkg_names)) if pkg_names else "."
    test_targets = [str(p.relative_to(repo_path)) for p in _test_files(repo_path)]
    a = _run([py, "-m", "coverage", "run", "--source", src_arg, "-m", "pytest", "-q",
              "--no-header", "-p", "no:cacheprovider", *test_targets],
             str(repo_path), art_dir / "04_tests.log", timeout, env)
    res.artifacts.append(a)
    text = Path(a.path).read_text()
    p, f, e = _parse_pytest(text)
    res.tests_passed, res.tests_failed, res.tests_errored = p, f, e
    res.tests_ran = p is not None
    if not res.tests_ran:
        res.notes.append("no runnable pytest suite detected (or collection failed)")

    # 5. measured coverage (not the README's claim)
    a = _run([py, "-m", "coverage", "report"], str(repo_path), art_dir / "05_coverage.log", timeout, env)
    res.artifacts.append(a)
    m = re.search(r"^TOTAL\s+\d+\s+\d+\s+(\d+)%", Path(a.path).read_text(), re.M)
    if m:
        res.coverage_pct = float(m.group(1))

    # 6. assertion density (coverage-theater detector)
    res.assertion_density = _assertion_density(repo_path)

    # cleanup the venv (keep artifacts, drop bulk)
    shutil.rmtree(venv, ignore_errors=True)
    (art_dir / "result.json").write_text(json.dumps(res.to_dict(), indent=2))
    return res


if __name__ == "__main__":
    r = probe(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
    print(json.dumps({k: v for k, v in r.to_dict().items() if k != "artifacts"}, indent=2))
