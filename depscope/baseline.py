"""Reading-only baseline: what you get WITHOUT executing anything.

This is the fair comparison point and it is deliberately generous. The baseline
receives everything a careful human reviewer would see while skimming a repository
on GitHub -- the full README, the file tree, package metadata, and real source and
test excerpts -- and is asked for exactly the same verdict, using the same rubric,
from the same frontier model DepScope itself uses.

The ONLY thing it cannot do is run the code. That is the whole experiment.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import llm  # noqa: E402

MODEL = "claude-sonnet-5"
MAX_FILE_CHARS = 2500
MAX_FILES = 8

PROMPT = """You are assessing whether a team should ADOPT this Python package as a
dependency. Judge it on: clean install, tests passing, coverage, test strength
(do the tests actually assert things?), maintenance activity, and bus factor.

Give your verdict:
- ADOPT   : healthy, safe to depend on
- CAUTION : usable but with real risks
- AVOID   : do not adopt

Return ONLY JSON:
{{"verdict":"ADOPT|CAUTION|AVOID","overall":<0-10>,"reasons":["...","..."]}}

REPOSITORY: {name}

=== FILE TREE ===
{tree}

=== PACKAGE METADATA ===
{meta}

=== README ===
{readme}

=== SOURCE AND TEST EXCERPTS ===
{excerpts}
"""


def _tree(repo: Path, limit: int = 60) -> str:
    out = []
    for p in sorted(repo.rglob("*")):
        if any(x in p.parts for x in (".git", ".depscope_venv", "__pycache__", ".tox")):
            continue
        rel = p.relative_to(repo)
        if len(rel.parts) > 3:
            continue
        out.append(("  " * (len(rel.parts) - 1)) + rel.name + ("/" if p.is_dir() else ""))
        if len(out) >= limit:
            out.append("... (truncated)")
            break
    return "\n".join(out)


def _read(p: Path, n: int = MAX_FILE_CHARS) -> str:
    try:
        return p.read_text(errors="ignore")[:n]
    except OSError:
        return ""


def _excerpts(repo: Path) -> str:
    """Real source + test excerpts -- the same sampling a human skim would do."""
    picks: list[Path] = []
    for pat in ("setup.py", "pyproject.toml"):
        picks += list(repo.glob(pat))
    pkg_files = [p for p in repo.rglob("*.py")
                 if not any(x in p.parts for x in (".git", ".depscope_venv", "__pycache__", ".tox"))]
    src = [p for p in pkg_files if "test" not in p.name]
    tests = [p for p in pkg_files if "test" in p.name]
    picks += sorted(src, key=lambda p: -p.stat().st_size)[:4]
    picks += sorted(tests, key=lambda p: -p.stat().st_size)[:3]
    chunks = []
    for p in picks[:MAX_FILES]:
        chunks.append(f"--- {p.relative_to(repo)} ---\n{_read(p)}")
    return "\n\n".join(chunks)


def _meta(repo: Path) -> str:
    bits = []
    for n in ("pyproject.toml", "setup.py", "setup.cfg", "requirements.txt", "tox.ini"):
        p = repo / n
        if p.exists():
            bits.append(f"--- {n} ---\n{_read(p, 1200)}")
    return "\n".join(bits) or "(none found)"


def _readme(repo: Path) -> str:
    for n in ("README.md", "README.rst", "README.txt", "README"):
        p = repo / n
        if p.exists():
            return _read(p, 6000)
    return "(no README)"


def assess_by_reading(repo_dir: str) -> dict:
    repo = Path(repo_dir)
    session = f"baseline_{repo.name}"
    prompt = PROMPT.format(name=repo.name, tree=_tree(repo), meta=_meta(repo),
                           readme=_readme(repo), excerpts=_excerpts(repo))
    llm.note(session, "start", package=repo.name,
             note="reading-only arm: same rubric and model, but may not execute anything",
             prompt_chars=len(prompt))
    try:
        res = llm.ask_json(prompt, session=session, step="assess_by_reading")
        d = dict(res.parsed)
        d["attempts"] = res.attempts
    except llm.LLMUnavailable as exc:
        d = {"error": str(exc)}
    d["package"] = repo.name
    llm.note(session, "verdict", verdict=d.get("verdict"), overall=d.get("overall"))
    return d


if __name__ == "__main__":
    for t in sys.argv[1:]:
        r = assess_by_reading(t)
        print(f"{r.get('package'):14} {r.get('verdict','?'):8} overall={r.get('overall','?')}")
