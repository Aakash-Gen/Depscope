"""Load an .xlsx into a structured model and resolve every cell to a number.

The resolver computes each formula cell using formula_engine, in dependency
order, so downstream code can compare 'the value the sheet shows' against
'the value we independently recompute'.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, Optional

import openpyxl

from formula_engine import evaluate, _CELL_RE, _RANGE_RE, expand_range, _norm_ref


@dataclass
class Cell:
    coord: str
    formula: Optional[str]   # e.g. "=B5*C5"  (None if literal)
    literal: Optional[float] # numeric literal (None if formula)
    precedents: list[str] = field(default_factory=list)


class Workbook:
    def __init__(self, cells: Dict[str, Cell]):
        self.cells = cells
        self._resolved: Dict[str, float] = {}

    @classmethod
    def load(cls, path: str, sheet: Optional[str] = None) -> "Workbook":
        wb = openpyxl.load_workbook(path, data_only=False)
        ws = wb[sheet] if sheet else wb.active
        cells: Dict[str, Cell] = {}
        for row in ws.iter_rows():
            for c in row:
                if c.value is None:
                    continue
                coord = c.coordinate
                if isinstance(c.value, str) and c.value.startswith("="):
                    formula = c.value
                    cells[coord] = Cell(coord, formula, None, _extract_refs(formula))
                elif isinstance(c.value, (int, float)):
                    cells[coord] = Cell(coord, None, float(c.value), [])
                # non-numeric text (labels) are ignored for recompute
        return cls(cells)

    def resolve(self) -> Dict[str, float]:
        """Return coord -> recomputed numeric value for every numeric/formula cell."""
        self._resolved = {}
        for coord in self.cells:
            self._resolve_cell(coord, set())
        return self._resolved

    def _resolve_cell(self, coord: str, stack: set) -> float:
        if coord in self._resolved:
            return self._resolved[coord]
        cell = self.cells.get(coord)
        if cell is None:
            raise KeyError(f"referenced empty/label cell: {coord}")
        if coord in stack:
            raise ValueError(f"circular reference at {coord}")
        stack.add(coord)
        if cell.formula is None:
            val = float(cell.literal)
        else:
            for p in cell.precedents:
                self._resolve_cell(p, stack)
            val = evaluate(cell.formula, self._resolved)
        stack.discard(coord)
        self._resolved[coord] = val
        return val


def _extract_refs(formula: str) -> list[str]:
    """All single-cell precedents of a formula (ranges expanded)."""
    refs: list[str] = []
    # ranges first
    for m in _RANGE_RE.finditer(formula):
        refs.extend(expand_range(m.group(0)))
    # remove ranges then grab lone cells
    stripped = _RANGE_RE.sub("", formula)
    for m in _CELL_RE.finditer(stripped):
        refs.append(_norm_ref(m.group(0)))
    # de-dup, drop function-name false-positives handled by regex boundaries
    seen = []
    for r in refs:
        if r not in seen:
            seen.append(r)
    return seen
