"""History Miner: maintenance-risk evidence from git history.

Deterministic (no LLM). These are repo-scale facts -- thousands of commits across
years -- that do not fit in a prompt and cannot be inferred from a README. They
answer the questions that actually predict adoption pain: is anyone still working
on this, and how many people would have to disappear for it to die?
"""
from __future__ import annotations

import json
import subprocess
from collections import Counter
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path

ARTIFACT_ROOT = Path(__file__).resolve().parent.parent / "artifacts"


@dataclass
class HistoryResult:
    repo: str
    total_commits: int = 0
    contributors: int = 0
    bus_factor: int = 0             # devs responsible for >=50% of commits
    top_author_share: float = 0.0   # fraction by the single busiest author
    last_commit_date: str = ""
    days_since_last_commit: int = 0
    commits_last_year: int = 0
    releases: int = 0
    last_release: str = ""
    days_since_last_release: int | None = None
    artifacts: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _git(repo: str, *args: str) -> str:
    return subprocess.run(["git", "-C", repo, *args],
                          capture_output=True, text=True).stdout


def _default_ref(repo: str) -> str:
    """Resolve the project's live default branch.

    Execution evidence is gathered at the PINNED commit (the version you would
    install), but maintenance evidence must describe the project as it stands
    TODAY -- otherwise a package abandoned after the pinned tag still looks alive.
    """
    head = _git(repo, "symbolic-ref", "--quiet", "refs/remotes/origin/HEAD").strip()
    if head:
        return head.replace("refs/remotes/", "")
    for cand in ("origin/main", "origin/master"):
        if _git(repo, "rev-parse", "--verify", "--quiet", cand).strip():
            return cand
    return "HEAD"


def mine(repo_dir: str, name: str | None = None) -> HistoryResult:
    repo = str(Path(repo_dir).resolve())
    name = name or Path(repo).name
    ref = _default_ref(repo)
    art_dir = ARTIFACT_ROOT / name
    art_dir.mkdir(parents=True, exist_ok=True)
    res = HistoryResult(repo=name)

    # Authorship distribution -> bus factor.
    authors = [l for l in _git(repo, "log", ref, "--format=%an").splitlines() if l.strip()]
    res.total_commits = len(authors)
    counts = Counter(authors)
    res.contributors = len(counts)
    if res.total_commits:
        ranked = counts.most_common()
        res.top_author_share = round(ranked[0][1] / res.total_commits, 3)
        cum, bus = 0, 0
        for _, c in ranked:                     # how few people own half the work?
            cum += c
            bus += 1
            if cum >= res.total_commits * 0.5:
                break
        res.bus_factor = bus

    # Recency / activity.
    last = _git(repo, "log", ref, "-1", "--format=%aI").strip()
    if last:
        res.last_commit_date = last[:10]
        dt = datetime.fromisoformat(last.replace("Z", "+00:00"))
        res.days_since_last_commit = (datetime.now(timezone.utc) - dt).days
    res.commits_last_year = len(
        [l for l in _git(repo, "log", ref, "--since=1.year", "--format=%h").splitlines() if l.strip()])

    # Release cadence from tags.
    tags = [l for l in _git(repo, "tag").splitlines() if l.strip()]
    res.releases = len(tags)
    tag_dates = _git(repo, "for-each-ref", "--sort=-creatordate", "--format=%(refname:short)|%(creatordate:short)",
                     "refs/tags").splitlines()
    if tag_dates and "|" in tag_dates[0]:
        tag, date = tag_dates[0].split("|", 1)
        res.last_release = f"{tag.strip()} ({date.strip()})"
        try:
            d = datetime.strptime(date.strip(), "%Y-%m-%d").replace(tzinfo=timezone.utc)
            res.days_since_last_release = (datetime.now(timezone.utc) - d).days
        except ValueError:
            pass

    # Save the raw evidence a report line can cite.
    log_path = art_dir / "06_history.log"
    log_path.write_text(
        f"$ git log/tag analysis for {name}\n{'-'*70}\n"
        f"total_commits={res.total_commits}\ncontributors={res.contributors}\n"
        f"bus_factor={res.bus_factor} (devs owning >=50% of commits)\n"
        f"top_author_share={res.top_author_share}\n"
        f"last_commit={res.last_commit_date} ({res.days_since_last_commit} days ago)\n"
        f"commits_last_year={res.commits_last_year}\n"
        f"releases={res.releases}\nlast_release={res.last_release}\n"
        f"days_since_last_release={res.days_since_last_release}\n\n"
        f"top authors:\n" + "\n".join(f"  {a}: {c}" for a, c in counts.most_common(8)) + "\n")
    res.artifacts = [{"name": "06_history", "path": str(log_path)}]
    (art_dir / "history.json").write_text(json.dumps(res.to_dict(), indent=2))
    return res


if __name__ == "__main__":
    import sys
    print(json.dumps(mine(sys.argv[1]).to_dict(), indent=2))
