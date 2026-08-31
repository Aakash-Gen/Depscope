"""Render a workbook as a readable text grid (formula + computed value per cell).

This is the representation a person would paste into a chatbot today: every
non-empty cell with its formula (if any) and its resolved value.
"""
from __future__ import annotations

import openpyxl

from workbook import Workbook


def dump(path: str, sheet: str | None = None) -> str:
    wb_raw = openpyxl.load_workbook(path, data_only=False)
    ws = wb_raw[sheet] if sheet else wb_raw.active

    wb = Workbook.load(path, sheet)
    values = wb.resolve()

    lines = [f"# Sheet: {ws.title}", "", "cell | formula | value"]
    for row in ws.iter_rows():
        for c in row:
            if c.value is None:
                continue
            coord = c.coordinate
            if isinstance(c.value, str) and c.value.startswith("="):
                val = values.get(coord, "")
                val_s = f"{val:g}" if isinstance(val, (int, float)) else ""
                lines.append(f"{coord} | {c.value} | {val_s}")
            elif isinstance(c.value, (int, float)):
                lines.append(f"{coord} | (literal) | {c.value:g}")
            else:
                lines.append(f"{coord} | (label) | {c.value}")
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    print(dump(sys.argv[1] if len(sys.argv) > 1 else "data/sheets/model_01.xlsx"))
