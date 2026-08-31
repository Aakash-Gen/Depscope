"""Minimal, deterministic Excel-formula evaluator for the auditor's verifier.

Scope (spike): the subset of Excel needed to verify error classes E1, E3, E7:
  - numeric literals
  - cell references (A1, $A$1, mixed)
  - ranges (A1:A10)
  - SUM(range or args)
  - binary arithmetic:  + - * /
  - parentheses

This is intentionally NOT a full Excel engine. It is a controlled recompute
kernel: given a workbook's raw values/formulas, evaluate a formula string to a
number. The point is determinism -- the same inputs always yield the same
number, so a judge reruns and gets identical results.
"""
from __future__ import annotations

import re
from typing import Dict


CellValues = Dict[str, float]  # "A1" -> numeric value (formulas resolved elsewhere or literal)


class FormulaError(Exception):
    pass


_CELL_RE = re.compile(r"\$?([A-Z]+)\$?(\d+)")
_RANGE_RE = re.compile(r"(\$?[A-Z]+\$?\d+):(\$?[A-Z]+\$?\d+)")


def _col_to_num(col: str) -> int:
    n = 0
    for ch in col:
        n = n * 26 + (ord(ch) - ord("A") + 1)
    return n


def _num_to_col(n: int) -> str:
    s = ""
    while n > 0:
        n, r = divmod(n - 1, 26)
        s = chr(ord("A") + r) + s
    return s


def _norm_ref(ref: str) -> str:
    """Strip $ signs -> canonical 'A1'."""
    m = _CELL_RE.fullmatch(ref)
    if not m:
        raise FormulaError(f"bad cell ref: {ref}")
    return f"{m.group(1)}{m.group(2)}"


def expand_range(rng: str) -> list[str]:
    """'A1:A3' -> ['A1','A2','A3'] (row- then col-major, supports rectangles)."""
    m = _RANGE_RE.fullmatch(rng)
    if not m:
        raise FormulaError(f"bad range: {rng}")
    c1 = _norm_ref(m.group(1))
    c2 = _norm_ref(m.group(2))
    m1 = _CELL_RE.fullmatch(c1)
    m2 = _CELL_RE.fullmatch(c2)
    col1, row1 = _col_to_num(m1.group(1)), int(m1.group(2))
    col2, row2 = _col_to_num(m2.group(1)), int(m2.group(2))
    cells = []
    for c in range(min(col1, col2), max(col1, col2) + 1):
        for r in range(min(row1, row2), max(row1, row2) + 1):
            cells.append(f"{_num_to_col(c)}{r}")
    return cells


def evaluate(formula: str, values: CellValues) -> float:
    """Evaluate a formula string against a dict of resolved cell values.

    `values` must already contain numeric values for every cell the formula
    references (the caller resolves the dependency order).
    """
    f = formula.strip()
    if f.startswith("="):
        f = f[1:]

    # 1) Replace SUM(...) with its numeric result.
    def _sum_repl(match: re.Match) -> str:
        inner = match.group(1)
        total = 0.0
        for part in inner.split(","):
            part = part.strip()
            if _RANGE_RE.fullmatch(part):
                for cell in expand_range(part):
                    total += _lookup(cell, values)
            elif _CELL_RE.fullmatch(part):
                total += _lookup(part, values)
            else:
                total += float(part)
        return repr(total)

    f = re.sub(r"SUM\(([^()]*)\)", _sum_repl, f, flags=re.IGNORECASE)

    # 2) Replace remaining cell refs with their values.
    def _cell_repl(match: re.Match) -> str:
        return repr(_lookup(_norm_ref(match.group(0)), values))

    f = _CELL_RE.sub(_cell_repl, f)

    # 3) Evaluate the now purely-arithmetic expression safely.
    if not re.fullmatch(r"[0-9eE+\-*/(). ]*", f):
        raise FormulaError(f"unsupported tokens after resolution: {f!r}")
    try:
        return float(eval(f, {"__builtins__": {}}, {}))  # noqa: S307 - sanitized above
    except Exception as exc:  # noqa: BLE001
        raise FormulaError(f"eval failed for {formula!r} -> {f!r}: {exc}") from exc


def _lookup(cell: str, values: CellValues) -> float:
    if cell not in values:
        raise FormulaError(f"missing value for {cell}")
    return float(values[cell])
