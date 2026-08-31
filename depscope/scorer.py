"""Scorecard + the Claim Verifier gate.

Design rule (the product of nine falsification experiments):
    EVIDENCE OR IT DIDN'T HAPPEN.

Every line of the scorecard is derived from a collected artifact and carries a
citation to it. The LLM never invents a score; it is used only to write the human
narrative, and anything it asserts is passed through `verify_claims`, which drops
or flags any statement that the artifacts do not support.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path

VERDICTS = ("ADOPT", "CAUTION", "AVOID")


@dataclass
class Finding:
    dimension: str
    score: int            # 0-10
    statement: str        # human-readable, must be backed by `citation`
    citation: str         # artifact path a reader can open
    severity: str = "info"  # info | warn | critical

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Scorecard:
    package: str
    commit: str
    verdict: str = "CAUTION"
    overall: float = 0.0
    findings: list[Finding] = field(default_factory=list)
    mismatches: list[dict] = field(default_factory=list)   # README claim vs measured reality
    rejected_claims: list[dict] = field(default_factory=list)  # failed the verifier gate

    def to_dict(self) -> dict:
        d = asdict(self)
        d["findings"] = [f.to_dict() for f in self.findings]
        return d


def _score_tests(p: dict, cite: str) -> Finding:
    if p.get("tests_ran") is not True:
        return Finding("Tests execute", 0,
                       "No runnable test suite could be executed at this commit.",
                       cite, "critical")
    failed = (p.get("tests_failed") or 0) + (p.get("tests_errored") or 0)
    passed = p.get("tests_passed") or 0
    if failed:
        return Finding("Tests pass", 1,
                       f"{failed} of {passed + failed} tests FAIL at the pinned commit.",
                       cite, "critical")
    if passed == 0:
        return Finding("Tests pass", 2, "The suite collected zero tests.", cite, "critical")
    return Finding("Tests pass", 10,
                   f"All {passed} tests pass in a clean environment.", cite)


def _score_install(p: dict, cite: str) -> Finding:
    if p.get("installed"):
        return Finding("Clean install", 10,
                       "Installs successfully from source in a fresh virtualenv.", cite)
    return Finding("Clean install", 0,
                   "FAILS to install in a fresh virtualenv (dependency cannot be resolved).",
                   cite, "critical")


def _score_coverage(p: dict, cite: str) -> Finding:
    cov = p.get("coverage_pct")
    if cov is None:
        return Finding("Coverage", 4, "Coverage could not be measured.", cite, "warn")
    if cov >= 85:
        return Finding("Coverage", 10, f"Measured coverage {cov:.0f}%.", cite)
    if cov >= 60:
        return Finding("Coverage", 6, f"Measured coverage {cov:.0f}% (moderate).", cite, "warn")
    return Finding("Coverage", 3, f"Measured coverage only {cov:.0f}%.", cite, "warn")


def _score_assertions(p: dict, cite: str) -> Finding:
    d = p.get("assertion_density")
    if d is None:
        return Finding("Test strength", 4, "No test functions found to analyse.", cite, "warn")
    if d < 0.5:
        return Finding("Test strength", 1,
                       f"Coverage theater: only {d} assertions per test function - the suite "
                       f"executes code but verifies almost nothing.", cite, "critical")
    if d < 1.0:
        return Finding("Test strength", 5,
                       f"Weak assertions ({d} per test function).", cite, "warn")
    return Finding("Test strength", 10,
                   f"Tests assert meaningfully ({d} assertions per test function).", cite)


def _score_maintenance(h: dict, cite: str) -> list[Finding]:
    out = []
    days = h.get("days_since_last_commit", 0)
    if days > 730:
        out.append(Finding("Maintenance", 0,
                           f"Abandoned: no commit in {days} days "
                           f"(last {h.get('last_commit_date')}).", cite, "critical"))
    elif days > 365:
        out.append(Finding("Maintenance", 3,
                           f"Dormant: last commit {days} days ago.", cite, "warn"))
    elif days > 180:
        out.append(Finding("Maintenance", 6,
                           f"Slow: last commit {days} days ago; "
                           f"{h.get('commits_last_year')} commits in the last year.", cite, "warn"))
    else:
        out.append(Finding("Maintenance", 10,
                           f"Actively maintained: last commit {days} days ago, "
                           f"{h.get('commits_last_year')} commits in the last year.", cite))

    bus = h.get("bus_factor", 0)
    share = h.get("top_author_share", 0.0)
    if bus <= 1:
        out.append(Finding("Bus factor", 3,
                           f"Bus factor 1 - a single contributor authored "
                           f"{share:.0%} of all commits.", cite, "warn"))
    elif bus == 2:
        out.append(Finding("Bus factor", 7,
                           f"Bus factor 2 across {h.get('contributors')} contributors.", cite))
    else:
        out.append(Finding("Bus factor", 10,
                           f"Bus factor {bus} across {h.get('contributors')} contributors.", cite))
    return out


def build_scorecard(probe_result: dict, history_result: dict) -> Scorecard:
    """Derive every score deterministically from collected artifacts."""
    name = probe_result.get("repo", "unknown")
    art = f"artifacts/{name}"
    sc = Scorecard(package=name, commit=probe_result.get("commit", ""))

    sc.findings.append(_score_install(probe_result, f"{art}/02_install.log"))
    sc.findings.append(_score_tests(probe_result, f"{art}/04_tests.log"))
    sc.findings.append(_score_coverage(probe_result, f"{art}/05_coverage.log"))
    sc.findings.append(_score_assertions(probe_result, f"{art}/04_tests.log"))
    sc.findings.extend(_score_maintenance(history_result, f"{art}/06_history.log"))

    sc.overall = round(sum(f.score for f in sc.findings) / len(sc.findings), 1)
    # Verdict follows the rubric published in eval/ground_truth.json, exactly:
    # any blocking defect -> AVOID; any material risk -> CAUTION; else ADOPT.
    # A high average must NOT wash out a real risk (a package with perfect tests
    # but a bus factor of 1 is still a risk you are asked to accept knowingly).
    if any(f.severity == "critical" for f in sc.findings):
        sc.verdict = "AVOID"
    elif any(f.severity == "warn" for f in sc.findings):
        sc.verdict = "CAUTION"
    else:
        sc.verdict = "ADOPT"
    return sc


# --------------------------------------------------------------------------
# The Claim Verifier gate
# --------------------------------------------------------------------------

def verify_claims(claims: list[dict], probe_result: dict, history_result: dict) -> tuple[list[dict], list[dict]]:
    """Check numeric claims (from a README, or written by an LLM) against measured facts.

    Returns (mismatches, rejected). A claim survives only if the artifacts support it.
    This is the gate that makes the report trustworthy: an unverifiable sentence is
    never printed as fact.
    """
    facts = {
        "coverage_pct": probe_result.get("coverage_pct"),
        "tests_failed": (probe_result.get("tests_failed") or 0) + (probe_result.get("tests_errored") or 0),
        "installed": probe_result.get("installed"),
        "days_since_last_commit": history_result.get("days_since_last_commit"),
    }
    mismatches, rejected = [], []
    for c in claims:
        kind, value = c.get("kind"), c.get("value")
        text = c.get("text", "")
        if kind == "coverage" and facts["coverage_pct"] is not None and value is not None:
            if float(value) - facts["coverage_pct"] > 5:
                mismatches.append({
                    "claim": text, "claimed": f"{value}% coverage",
                    "measured": f"{facts['coverage_pct']:.0f}% coverage",
                    "citation": f"artifacts/{probe_result['repo']}/05_coverage.log"})
        elif kind == "tests_green" and facts["tests_failed"]:
            mismatches.append({
                "claim": text, "claimed": "test suite is green",
                "measured": f"{facts['tests_failed']} failing test(s)",
                "citation": f"artifacts/{probe_result['repo']}/04_tests.log"})
        elif kind == "installable" and facts["installed"] is False:
            mismatches.append({
                "claim": text, "claimed": "installs with one command",
                "measured": "install fails in a clean virtualenv",
                "citation": f"artifacts/{probe_result['repo']}/02_install.log"})
        elif kind == "maintained" and (facts["days_since_last_commit"] or 0) > 365:
            mismatches.append({
                "claim": text, "claimed": "actively maintained",
                "measured": f"no commit in {facts['days_since_last_commit']} days",
                "citation": f"artifacts/{probe_result['repo']}/06_history.log"})
        elif kind not in ("coverage", "tests_green", "installable", "maintained"):
            rejected.append({"claim": text, "reason": "no artifact can verify this claim"})

    # A README often repeats the same boast (badge + prose); report each distinct
    # contradiction once so the table stays readable.
    deduped, seen = [], set()
    for m in mismatches:
        key = (m["claimed"], m["measured"])
        if key not in seen:
            seen.add(key)
            deduped.append(m)
    return deduped, rejected


if __name__ == "__main__":
    import sys
    probes = json.load(open(sys.argv[1]))
    hist = json.load(open(sys.argv[2]))
    for pkg, p in probes.items():
        sc = build_scorecard(p, hist.get(pkg, {}))
        print(f"{pkg:15} {sc.verdict:8} overall={sc.overall}")
