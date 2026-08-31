"""DepScope pipeline: acquire -> execute -> mine -> read claims -> verify -> report.

Run one package:      python3 depscope/pipeline.py repos/humanize
Run a head-to-head:   python3 depscope/pipeline.py repos/furl repos/humanize
"""
from __future__ import annotations

import json
import re
import shutil
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


# --------------------------------------------------------------------------
# Terminal rendering
# --------------------------------------------------------------------------

class C:
    """ANSI codes, blanked automatically when output is piped to a file."""
    on = sys.stdout.isatty()
    def __class_getitem__(cls, code: str) -> str:
        return code if cls.on else ""


R = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
STRIKE = "\033[9m"
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
GREY = "\033[90m"
WHITE = "\033[97m"

VERDICT_STYLE = {"ADOPT": (GREEN, "ADOPT"),
                 "CAUTION": (YELLOW, "CAUTION"),
                 "AVOID": (RED, "AVOID")}
SEV_STYLE = {"critical": (RED, "x"), "warn": (YELLOW, "!"), "info": (GREEN, "v")}


def _c(s: str) -> str:
    """Strip colour when not a TTY so piped output stays clean."""
    return s if C.on else re.sub(r"\033\[[0-9;]*m", "", s)


def _bar(score: int, width: int = 10) -> str:
    filled = round(score / 10 * width)
    colour = RED if score <= 3 else YELLOW if score <= 6 else GREEN
    return f"{colour}{'#' * filled}{GREY}{'.' * (width - filled)}{R}"


def _wrap(text: str, width: int, indent: str) -> str:
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    lines.append(cur)
    return f"\n{indent}".join(lines)


def render_terminal(sc: Scorecard) -> str:
    width = min(shutil.get_terminal_size((100, 24)).columns, 100)
    colour, label = VERDICT_STYLE[sc.verdict]
    out: list[str] = []

    rule = "-" * width
    out.append(f"{BOLD}{CYAN}DepScope{R}  {BOLD}{WHITE}{sc.package}{R}"
               f"{GREY}   commit {sc.commit}{R}")
    out.append(f"{GREY}{rule}{R}")
    out.append(f"  {colour}{BOLD}VERDICT: {label}{R}"
               f"{GREY}{'overall ' + str(sc.overall) + '/10':>{max(0, width - 22 - len(label))}}{R}")
    out.append("")

    out.append(f"  {BOLD}EVIDENCE{R} {GREY}(every line cites a log you can open){R}")
    for f in sorted(sc.findings, key=lambda x: x.score):
        sev_colour, mark = SEV_STYLE[f.severity]
        # visible width of the header: 2 + 1 + 1 + 15 + 10 + 1 + 5 + 2
        pad = 37
        head = (f"  {sev_colour}{mark}{R} {BOLD}{f.dimension:<15}{R}"
                f"{_bar(f.score)} {f.score:>2}/10  ")
        out.append(head + _wrap(f.statement, max(24, width - pad), " " * pad))
        out.append(f"{GREY}{' ' * pad}-> {f.citation}{R}")
    out.append("")

    if sc.mismatches:
        out.append(f"  {BOLD}{RED}README SAYS  vs  REALITY{R}")
        for m in sc.mismatches:
            out.append(f"    {GREY}claims{R}  {m['claimed']}")
            out.append(f"    {RED}{BOLD}truth {R}  {RED}{m['measured']}{R}"
                       f"   {GREY}({m['citation']}){R}")
            out.append("")

    if sc.rejected_claims:
        out.append(f"  {BOLD}CLAIMS DROPPED{R} {GREY}- no artifact could confirm these{R}")
        for r in sc.rejected_claims[:6]:
            out.append(f"    {GREY}{STRIKE}{r['claim']}{R}")
        out.append("")

    out.append(f"{GREY}{rule}{R}")
    out.append(f"{GREY}  Advisory only - a developer signs off before adoption.{R}")
    return _c("\n".join(out))


def head_to_head_terminal(cards: list[Scorecard]) -> str:
    width = min(shutil.get_terminal_size((100, 24)).columns, 100)
    dims = ["Clean install", "Tests pass", "Coverage", "Test strength", "Maintenance"]
    short = {"Clean install": "install", "Tests pass": "tests", "Coverage": "cover",
             "Test strength": "strength", "Maintenance": "maint"}
    out = ["", f"{BOLD}{CYAN}HEAD-TO-HEAD{R}", f"{GREY}{'-' * width}{R}"]
    hdr = f"  {'package':<14}{'verdict':<10}{'score':<8}" + "".join(
        f"{short[d]:<10}" for d in dims)
    out.append(f"{BOLD}{hdr}{R}")
    for sc in sorted(cards, key=lambda c: -c.overall):
        g = {f.dimension: f for f in sc.findings}
        colour, label = VERDICT_STYLE[sc.verdict]
        row = f"  {BOLD}{sc.package:<14}{R}{colour}{label:<10}{R}{sc.overall:<8}"
        for d in dims:
            f = g.get(d)
            if not f:
                row += f"{GREY}{'-':<10}{R}"
            else:
                sc_col = RED if f.score <= 3 else YELLOW if f.score <= 6 else GREEN
                row += f"{sc_col}{str(f.score) + '/10':<10}{R}"
        out.append(row)
    best = max(cards, key=lambda c: c.overall)
    out += ["", f"  {GREEN}{BOLD}Recommended: {best.package}{R}"
                f"{GREY}  (highest evidence-backed score, verdict {best.verdict}){R}", ""]
    return _c("\n".join(out))


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

  python3 depscope/pipeline.py <repo> [<repo> ...] [--no-llm] [--markdown]

  <repo>      path to a checked-out package (see REPRODUCE.md for the corpus)
  --no-llm    skip README claim extraction; runs fully offline with no model calls
              (the probe, history miner and scorer are deterministic and need no LLM)
  --markdown  emit the markdown report instead of the formatted terminal view
              (also the default when output is piped to a file)

Two or more repos produce a head-to-head comparison.
"""

if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    use_llm = "--no-llm" not in sys.argv
    as_md = "--markdown" in sys.argv or not sys.stdout.isatty()
    if not args:
        print(USAGE)
        sys.exit(1)
    cards = [assess(t, use_llm=use_llm) for t in args]
    for sc in cards:
        print(render(sc) if as_md else render_terminal(sc), "\n")
    if len(cards) > 1:
        print(head_to_head(cards) if as_md else head_to_head_terminal(cards))
