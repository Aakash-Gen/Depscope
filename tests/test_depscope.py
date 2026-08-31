"""Tests for DepScope itself.

A tool that judges other projects' test quality has no business shipping without
its own suite. These tests deliberately concentrate on the logic that produced
wrong answers during development -- the verdict rule, the claim verifier, the
coverage-theater detector, and the mutation-style pitfalls we hit -- because those
are the places where a bug becomes a confident false statement about someone
else's package.

Run:  python3 -m pytest tests/ -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "depscope"))

from scorer import build_scorecard, verify_claims  # noqa: E402
import probe as probe_mod                          # noqa: E402


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def make_probe(**over) -> dict:
    """A healthy probe result; override fields to describe an unhealthy package."""
    base = dict(repo="pkg", commit="abc123", installed=True, tests_ran=True,
                tests_passed=100, tests_failed=0, tests_errored=0,
                coverage_pct=95.0, assertion_density=2.0, notes=[], artifacts=[])
    base.update(over)
    return base


def make_history(**over) -> dict:
    base = dict(repo="pkg", total_commits=500, contributors=40, bus_factor=3,
                top_author_share=0.3, last_commit_date="2026-08-01",
                days_since_last_commit=10, commits_last_year=120,
                releases=20, last_release="v2.0", days_since_last_release=30)
    base.update(over)
    return base


def dims(sc) -> dict:
    return {f.dimension: f for f in sc.findings}


# --------------------------------------------------------------------------
# verdict rule -- must implement the PUBLISHED rubric exactly
# --------------------------------------------------------------------------

def test_healthy_package_is_adopt():
    sc = build_scorecard(make_probe(), make_history())
    assert sc.verdict == "ADOPT"


def test_failing_tests_force_avoid():
    sc = build_scorecard(make_probe(tests_passed=99, tests_failed=1), make_history())
    assert sc.verdict == "AVOID"
    assert dims(sc)["Tests pass"].severity == "critical"


def test_failed_install_forces_avoid():
    sc = build_scorecard(make_probe(installed=False), make_history())
    assert sc.verdict == "AVOID"


def test_abandoned_project_forces_avoid():
    sc = build_scorecard(make_probe(), make_history(days_since_last_commit=3737,
                                                   commits_last_year=0))
    assert sc.verdict == "AVOID"


def test_coverage_theater_forces_avoid():
    """The tidyurl trap: tests run and pass but assert almost nothing."""
    sc = build_scorecard(make_probe(assertion_density=0.12), make_history())
    assert sc.verdict == "AVOID"
    assert dims(sc)["Test strength"].severity == "critical"


def test_high_average_must_not_wash_out_a_real_risk():
    """Regression: a bus factor of 1 was once hidden by a strong overall average."""
    sc = build_scorecard(make_probe(), make_history(bus_factor=1, top_author_share=0.8))
    assert sc.verdict == "CAUTION"
    assert sc.overall >= 8.0          # the average really is high...
    assert dims(sc)["Bus factor"].severity == "warn"   # ...and the risk still surfaces


def test_low_coverage_is_caution_not_adopt():
    sc = build_scorecard(make_probe(coverage_pct=42.0), make_history())
    assert sc.verdict == "CAUTION"


def test_dormant_project_is_caution():
    sc = build_scorecard(make_probe(), make_history(days_since_last_commit=235,
                                                   commits_last_year=16))
    assert sc.verdict == "CAUTION"


# --------------------------------------------------------------------------
# every reported line must cite an artifact ("evidence or it didn't happen")
# --------------------------------------------------------------------------

def test_every_finding_cites_an_artifact():
    sc = build_scorecard(make_probe(), make_history())
    assert sc.findings
    for f in sc.findings:
        assert f.citation.startswith("artifacts/"), f
        assert f.citation.endswith(".log"), f


def test_no_test_suite_is_critical():
    sc = build_scorecard(make_probe(tests_ran=False, tests_passed=None), make_history())
    assert dims(sc)["Tests execute"].severity == "critical"
    assert sc.verdict == "AVOID"


# --------------------------------------------------------------------------
# claim verifier -- the gate between marketing copy and the report
# --------------------------------------------------------------------------

def test_inflated_coverage_claim_is_contradicted():
    claims = [{"kind": "coverage", "value": 98, "text": "98% test coverage"}]
    mism, _ = verify_claims(claims, make_probe(coverage_pct=88.0), make_history())
    assert len(mism) == 1
    assert "88" in mism[0]["measured"]


def test_accurate_coverage_claim_is_not_flagged():
    claims = [{"kind": "coverage", "value": 96, "text": "96% test coverage"}]
    mism, _ = verify_claims(claims, make_probe(coverage_pct=95.0), make_history())
    assert mism == []


def test_green_build_claim_contradicted_by_failures():
    claims = [{"kind": "tests_green", "value": None, "text": "green on every commit"}]
    mism, _ = verify_claims(claims, make_probe(tests_failed=1), make_history())
    assert len(mism) == 1


def test_maintained_claim_contradicted_by_abandonment():
    claims = [{"kind": "maintained", "value": None, "text": "actively maintained"}]
    mism, _ = verify_claims(claims, make_probe(), make_history(days_since_last_commit=3737))
    assert len(mism) == 1


def test_unverifiable_marketing_claims_are_rejected_not_repeated():
    claims = [{"kind": "other", "value": None, "text": "2.1M downloads/month"}]
    mism, rejected = verify_claims(claims, make_probe(), make_history())
    assert mism == []
    assert len(rejected) == 1


def test_duplicate_contradictions_are_reported_once():
    """A README repeats boasts in a badge and in prose; the table must not."""
    claims = [{"kind": "tests_green", "value": None, "text": "build passing"},
              {"kind": "tests_green", "value": None, "text": "green on every commit"}]
    mism, _ = verify_claims(claims, make_probe(tests_failed=2), make_history())
    assert len(mism) == 1


# --------------------------------------------------------------------------
# probe internals: the bugs that once faked our results
# --------------------------------------------------------------------------

def test_assertion_density_counts_helper_style_assertions(tmp_path):
    """Regression: 'assert_equal(...)' suites once looked like coverage theater."""
    (tmp_path / "test_x.py").write_text(
        "def test_a():\n    assert_equal(1, 1)\n    assert_equal(2, 2)\n"
        "def test_b():\n    assert_equal(3, 3)\n    assert_equal(4, 4)\n")
    assert probe_mod._assertion_density(tmp_path) == 2.0


def test_assertion_density_detects_real_theater(tmp_path):
    (tmp_path / "test_x.py").write_text(
        "def test_a():\n    thing()\ndef test_b():\n    other()\n"
        "def test_c():\n    more()\ndef test_d():\n    assert True\n")
    d = probe_mod._assertion_density(tmp_path)
    assert d is not None and d < 0.5


def test_test_discovery_finds_nonstandard_layouts(tmp_path):
    """python-slugify keeps its suite in a bare test.py; pytest ignores it by default."""
    (tmp_path / "test.py").write_text("def test_a():\n    assert True\n")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_b.py").write_text("def test_b():\n    assert True\n")
    names = {p.name for p in probe_mod._test_files(tmp_path)}
    assert names == {"test.py", "test_b.py"}


def test_test_discovery_ignores_the_probes_own_virtualenv(tmp_path):
    venv = tmp_path / ".depscope_venv" / "lib"
    venv.mkdir(parents=True)
    (venv / "test_vendored.py").write_text("def test_x():\n    assert True\n")
    (tmp_path / "test_real.py").write_text("def test_y():\n    assert True\n")
    assert {p.name for p in probe_mod._test_files(tmp_path)} == {"test_real.py"}


@pytest.mark.parametrize("summary,expected", [
    ("1 failed, 80 passed in 0.30s", (80, 1, 0)),
    ("527 passed in 2.10s", (527, 0, 0)),
    ("1 error in 0.05s", (0, 0, 1)),
    ("no tests ran in 0.01s", (None, None, None)),
])
def test_pytest_summary_parsing(summary, expected):
    assert probe_mod._parse_pytest(summary) == expected


def test_probe_disables_bytecode_cache():
    """Regression: a stale .pyc once made mutated code run as the original,
    which faked an entire experimental result. Never again."""
    src = (ROOT / "depscope" / "probe.py").read_text()
    assert "PYTHONDONTWRITEBYTECODE" in src
    assert "__pycache__" in src


def test_probe_puts_venv_bin_on_path():
    """Regression: python-dotenv showed 6 phantom failures because its own
    console script was not on PATH inside the probe's virtualenv."""
    src = (ROOT / "depscope" / "probe.py").read_text()
    assert "PATH=" in src and "venv / 'bin'" in src
