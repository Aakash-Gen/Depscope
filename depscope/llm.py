"""Single entry point for every LLM call, with retries and trajectory capture.

Two problems this solves:

1. **Silent failure.** Previously a failed or unparseable model reply was swallowed
   and treated as "this README makes no claims" -- which quietly disarms the Claim
   Verifier and makes a package look cleaner than it is. An unavailable model must
   be an audible error, never a clean bill of health.

2. **Auditability.** Every prompt, reply, retry and parse outcome is appended to a
   JSONL trajectory so a reviewer can follow exactly what the agent asked, what came
   back, and what was done with it.
"""
from __future__ import annotations

import json
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

TRAJECTORY_DIR = Path(__file__).resolve().parent.parent / "trajectories"
MODEL = "claude-sonnet-5"
MAX_ATTEMPTS = 3


class LLMUnavailable(RuntimeError):
    """Raised when the model could not be reached or produced nothing usable."""


@dataclass
class LLMResult:
    text: str
    parsed: dict | None
    attempts: int


def _log(session: str, record: dict) -> None:
    TRAJECTORY_DIR.mkdir(parents=True, exist_ok=True)
    record["ts"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    with (TRAJECTORY_DIR / f"{session}.jsonl").open("a") as fh:
        fh.write(json.dumps(record) + "\n")


def _extract_json(text: str) -> dict | None:
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def ask_json(prompt: str, *, session: str, step: str,
             timeout: int = 300, attempts: int = MAX_ATTEMPTS) -> LLMResult:
    """Call the model and require a parseable JSON object back.

    Retries on transport failure or unparseable output, then raises. Every attempt
    is written to the session trajectory.
    """
    _log(session, {"step": step, "event": "prompt", "model": MODEL,
                   "chars": len(prompt), "prompt": prompt[:4000]})
    last_err = ""
    for attempt in range(1, attempts + 1):
        try:
            proc = subprocess.run(["claude", "-p", "--model", MODEL], input=prompt,
                                  capture_output=True, text=True, timeout=timeout)
            out, err, code = proc.stdout, proc.stderr, proc.returncode
        except Exception as exc:  # noqa: BLE001
            out, err, code = "", str(exc), -1

        if code != 0:
            last_err = f"cli exit {code}: {err[:200]}"
            _log(session, {"step": step, "event": "retry", "attempt": attempt,
                           "reason": last_err})
            continue

        parsed = _extract_json(out)
        _log(session, {"step": step, "event": "reply", "attempt": attempt,
                       "parsed_ok": parsed is not None, "reply": out[:4000]})
        if parsed is not None:
            return LLMResult(out, parsed, attempt)

        last_err = "reply contained no parseable JSON object"
        _log(session, {"step": step, "event": "retry", "attempt": attempt,
                       "reason": last_err})
        prompt += ("\n\nYour previous reply could not be parsed. "
                   "Reply with ONLY a single JSON object and nothing else.")

    _log(session, {"step": step, "event": "failed", "attempts": attempts,
                   "reason": last_err})
    raise LLMUnavailable(f"{step}: giving up after {attempts} attempts ({last_err})")


def note(session: str, step: str, **fields) -> None:
    """Record a non-LLM step (execution, verification, human checkpoint) in the trajectory."""
    _log(session, {"step": step, "event": "action", **fields})
