"""DepScope pipeline: acquire -> execute -> mine -> read claims -> verify -> report.

Run one package:      python3 depscope/pipeline.py repos/humanize
Run a head-to-head:   python3 depscope/pipeline.py repos/furl repos/humanize
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import llm                                  # noqa: E402
from probe import probe                     # noqa: E402
from history import mine                    # noqa: E402
from scorer import build_scorecard, verify_claims, Scorecard  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
MODEL = "claude-sonnet-5"

CLAIM_PROMPT = """You are reading a package README to extract its factual CLAIMS.
Extract only claims that could be checked by running the code or inspecting history.

Return ONLY JSON:
{"claims":[{"kind":"coverage|tests_green|installable|maintained|other","value":<number or null>,"text":"<the claim, quoted briefly>"}]}

kind meanings:
- coverage    : a stated test-coverage percentage (put the number in "value")
- tests_green : asserts the test suite passes / build is green
- installable : asserts it installs easily / works out of the box
- maintained  : asserts active maintenance or responsiveness
- other       : any other marketing claim

README:
{readme}
"""


def read_readme(repo: Path) -> str:
    for n in ("README.md", "README.rst", "README.txt", "README"):
        p = repo / n
        if p.exists():
            return p.read_text(errors="ignore")[:6000]
    return ""


def extract_claims(readme: str, session: str) -> list[dict]:
    """LLM used ONLY to read prose. Nothing it says is trusted as fact -- every
    claim it returns is checked against measured artifacts by verify_claims()."""
    if not readme.strip():
        llm.note(session, "read_claims", result="no README found", claims=0)
        return []
    res = llm.ask_json(CLAIM_PROMPT.replace("{readme}", readme),
                       session=session, step="read_claims")
    claims = res.parsed.get("claims", [])
    llm.note(session, "read_claims", claims=len(claims), attempts=res.attempts)
    return claims


def assess(repo_dir: str, use_llm: bool = True) -> Scorecard:
    repo = Path(repo_dir)
    name = repo.name
    session = f"assess_{name}"

    llm.note(session, "start", package=name, path=str(repo), use_llm=use_llm)

    p = probe(str(repo), name).to_dict()
    llm.note(session, "execution_probe", installed=p.get("installed"),
             tests_passed=p.get("tests_passed"),
             tests_failed=(p.get("tests_failed") or 0) + (p.get("tests_errored") or 0),
             coverage_pct=p.get("coverage_pct"),
             assertion_density=p.get("assertion_density"),
             artifacts=[a["name"] for a in p.get("artifacts", [])])

    h = mine(str(repo), name).to_dict()
    llm.note(session, "history_miner", days_since_last_commit=h.get("days_since_last_commit"),
             bus_factor=h.get("bus_factor"), commits_last_year=h.get("commits_last_year"))

    sc = build_scorecard(p, h)
    llm.note(session, "scorer", verdict=sc.verdict, overall=sc.overall,
             findings=[(f.dimension, f.score, f.severity) for f in sc.findings])

    if use_llm:
        claims = extract_claims(read_readme(repo), session)
        sc.mismatches, sc.rejected_claims = verify_claims(claims, p, h)
        llm.note(session, "claim_verifier",
                 claims_examined=len(claims),
                 contradicted_by_evidence=len(sc.mismatches),
                 rejected_unverifiable=len(sc.rejected_claims),
                 rule="a claim is printed only if an artifact supports it")

    (ROOT / "artifacts" / name / "scorecard.json").write_text(
        json.dumps(sc.to_dict(), indent=2))
    llm.note(session, "human_checkpoint", verdict=sc.verdict,
             note="scorecard is advisory; a developer signs off before adoption")
    return sc


def render(sc: Scorecard) -> str:
    icon = {"ADOPT": "ADOPT", "CAUTION": "CAUTION", "AVOID": "AVOID"}[sc.verdict]
    lines = [f"# Adoption scorecard: {sc.package}",
             f"commit `{sc.commit}` | overall **{sc.overall}/10** | verdict: **{icon}**", "",
             "| dimension | score | evidence-backed finding | artifact |",
             "|---|---|---|---|"]
    for f in sorted(sc.findings, key=lambda x: x.score):
        flag = {"critical": "**!**", "warn": "*~*", "info": ""}[f.severity]
        lines.append(f"| {f.dimension} | {f.score}/10 {flag} | {f.statement} | `{f.citation}` |")
    if sc.mismatches:
        lines += ["", "## README says vs. reality", "",
                  "| the README claims | measurement says | proof |", "|---|---|---|"]
        for m in sc.mismatches:
            lines.append(f"| {m['claimed']} | **{m['measured']}** | `{m['citation']}` |")
    if sc.rejected_claims:
        lines += ["", "## Claims dropped by the verifier (no artifact could confirm them)", ""]
        for r in sc.rejected_claims[:6]:
            lines.append(f"- ~~{r['claim']}~~ - {r['reason']}")
    return "\n".join(lines)


def head_to_head(cards: list[Scorecard]) -> str:
    lines = ["# Head-to-head", "",
             "| package | verdict | overall | installs | tests | coverage | test strength | maintenance |",
             "|---|---|---|---|---|---|---|---|"]
    for sc in sorted(cards, key=lambda c: -c.overall):
        g = {f.dimension: f for f in sc.findings}
        def s(d):
            return f"{g[d].score}/10" if d in g else "-"
        lines.append(f"| **{sc.package}** | {sc.verdict} | {sc.overall} | {s('Clean install')} | "
                     f"{s('Tests pass')} | {s('Coverage')} | {s('Test strength')} | {s('Maintenance')} |")
    best = max(cards, key=lambda c: c.overall)
    lines += ["", f"**Recommendation:** adopt `{best.package}` "
                  f"(highest evidence-backed score, verdict {best.verdict})."]
    return "\n".join(lines)


USAGE = """DepScope - evidence-based dependency due-diligence

  python3 depscope/pipeline.py <repo> [<repo> ...] [--no-llm]

  <repo>     path to a checked-out package (see REPRODUCE.md for the corpus)
  --no-llm   skip README claim extraction; runs fully offline with no model calls
             (the probe, history miner and scorer are deterministic and need no LLM)

Two or more repos produce a head-to-head comparison table.
"""

if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    use_llm = "--no-llm" not in sys.argv
    if not args:
        print(USAGE)
        sys.exit(1)
    cards = [assess(t, use_llm=use_llm) for t in args]
    for sc in cards:
        print(render(sc), "\n")
    if len(cards) > 1:
        print(head_to_head(cards))
