# Grafik — ward rota manager

A desktop app for building monthly nurse rotas. Polish UI, Windows target,
developed on macOS.

Replaces a manual Excel workflow: shifts are typed as short codes or free-form
hours, and hours, statutory norms, overtime, night hours and leave are
calculated automatically.

## Features

- **Monthly grid** — employees down the side, days across the top. Type `D`,
  `N`, `U`… or free-form hours (`8-14`, `7:30-19:30`, `0700-1900`, `7,5`).
- **Any month, past or future** — every month is kept; navigate freely.
- **Automatic totals** — hours worked, statutory monthly norm (art. 130 K.p.,
  7 h 35 min/day for medical staff), overtime balance, night hours
  (21:00–07:00), shift count, leave and sick days.
- **Day colouring** — Saturdays, Sundays and public holidays are shaded
  distinctly. Nurses work through holidays; the colours are for visibility, and
  the holiday still reduces the contractual norm as the law requires.
- **Employees** — add, edit, reorder, part-time fractions, end-of-employment
  without destroying history.
- **Shift types** — fully editable: code, name, hours, category, colour.
- **Excel export** — formatted, colour-coded, print-ready A4 landscape with a
  legend and frozen header. Opens in Excel and LibreOffice.
- **Excel import** — auto-detects table layout, maps names to existing
  employees, preview before writing.
- **Photo import (optional)** — OCR of a photographed rota via Tesseract.
  Best-effort; always reviewed in the import preview before saving.
- **Backups** — one-click snapshot and restore.

## Layout

```
app/
  core/      domain logic — no Qt imports
    calendar_pl.py   Polish holidays, statutory monthly norm
    shifts.py        shift types, entry parsing
    stats.py         monthly aggregation, night hours
  io/
    xlsx_export.py   formatted spreadsheet writer
    xlsx_import.py   layout detection + name matching
    ocr.py           optional photo reader
  ui/        PySide6 widgets
  db.py      SQLite storage
```

`core/` is pure Python and fully unit-tested; the UI is a thin layer over it.

## Running from source

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m app        # launch
.venv/bin/python -m pytest -q  # tests
```

Data lives in the OS application-data directory (`%APPDATA%\Grafik` on Windows,
`~/Library/Application Support/Grafik` on macOS), not in the repo.

## Building the Windows executable

PyInstaller cannot cross-compile, so the Windows build runs on a Windows
machine or on CI. The included GitHub Actions workflow does it for you:

```bash
git tag v1.0.0 && git push --tags
```

This runs the tests, builds with PyInstaller, wraps the result in an Inno Setup
installer, and attaches `Grafik-Instalator-1.0.0.exe` plus a portable zip to the
release. `workflow_dispatch` builds without tagging.

To build on a Windows machine directly:

```powershell
pip install -r requirements-dev.txt
pyinstaller grafik.spec --noconfirm --clean
```

The installer requires no administrator rights (`PrivilegesRequired=lowest`).

## Photo import

Requires Tesseract OCR with the Polish language pack. The app detects it and
explains how to install it if missing — everything else works without it.

- Windows: installer from <https://github.com/UB-Mannheim/tesseract/wiki>
  (tick Polish). The app finds it in `C:\Program Files\Tesseract-OCR`.
- macOS: `brew install tesseract tesseract-lang`

Accuracy depends heavily on photo quality. The result always lands in the
import preview for correction; unrecognised entries appear red in the grid.
