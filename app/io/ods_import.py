"""Odczyt arkuszy OpenDocument (.ods) — formatu LibreOffice i OpenOffice."""
from __future__ import annotations

from pathlib import Path

# Bezpieczniki na wypadek arkuszy z ogromną liczbą pustych, powtórzonych komórek.
MAX_REPEAT_COLS = 64
MAX_REPEAT_ROWS = 16
MAX_COLS = 80
MAX_ROWS = 200


def read_ods_sheets(path: str | Path) -> list:
    """Zwraca listę arkuszy w tej samej postaci co czytnik plików .xlsx."""
    from odf.opendocument import load
    from odf.table import Table, TableRow, TableCell
    from odf.text import P

    from app.io.xlsx_import import SheetGrid

    doc = load(str(path))
    grids = []
    for table in doc.spreadsheet.getElementsByType(Table):
        rows: list[list[str]] = []
        for row in table.getElementsByType(TableRow):
            repeat_rows = _repeat(row.getAttribute("numberrowsrepeated"), MAX_REPEAT_ROWS)
            cells: list[str] = []
            for cell in row.getElementsByType(TableCell):
                repeat = _repeat(
                    cell.getAttribute("numbercolumnsrepeated"), MAX_REPEAT_COLS
                )
                text = "\n".join(str(p) for p in cell.getElementsByType(P)).strip()
                cells.extend([text] * repeat)
                if len(cells) >= MAX_COLS:
                    break
            _trim(cells)
            for _ in range(repeat_rows):
                rows.append(list(cells))
                if len(rows) >= MAX_ROWS:
                    break
            if len(rows) >= MAX_ROWS:
                break
        while rows and not any(rows[-1]):
            rows.pop()
        grids.append(SheetGrid(name=table.getAttribute("name") or "Arkusz", cells=rows))
    return grids


def _repeat(value, cap: int) -> int:
    """Puste obszary arkusza zapisane są jako jedna komórka powtórzona tysiące
    razy — powtórzenia ponad limit traktujemy jak pojedynczą komórkę."""
    try:
        n = int(value or 1)
    except (TypeError, ValueError):
        return 1
    return n if 1 <= n <= cap else 1


def _trim(cells: list[str]) -> None:
    while cells and not cells[-1]:
        cells.pop()
