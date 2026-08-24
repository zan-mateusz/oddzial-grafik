# Grafik — ward rota manager

A desktop app for building monthly nurse rotas. Polish UI, Windows target,
developed on macOS.

Replaces a manual Excel workflow: shifts are typed as short codes or free-form
hours, and hours, statutory norms, overtime, night hours and leave are
calculated automatically.

## Features

- **Monthly grid** — employees down the side, days across the top. Full shifts
  are codes (`D`, `N`); shorter ones are typed as a plain duration (`7:30`,
  `10`, `6:45`). Comma and dot act as the minute separator the way she already
  writes it by hand, so `7,3` is 7 h 30 min and `7,35` is 7 h 35 min — never a
  decimal fraction. The cell echoes back the parsed value. Hour ranges
  (`8-14`, `19-7`) are accepted too. Days off are left blank.
- **Any month, past or future** — every month is kept; navigate freely.
- **Automatic totals** — hours worked, statutory monthly norm (art. 130 K.p.,
  7 h 35 min/day for medical staff), overtime balance, night hours
  (21:00–07:00), shift count, leave and sick days.
- **Day colouring** — Saturdays, Sundays and public holidays are shaded
  distinctly. Nurses work through holidays; the colours are for visibility, and
  the holiday still reduces the contractual norm as the law requires.
- **Multiple floors** — each floor has its own rota and its own staff, switched
  from a dropdown. A nurse can be pencilled in on another floor as cover: the
  shift records *where it was worked*, so no duplicate employee records. Her
  own floor then shows that day greyed out, which prevents double-booking, and
  clearing a cell only removes the shift from the floor being viewed.
  `Godz. tu` / `Dyż. tu` count the current floor; `Godziny` / `Wymiar` /
  `Bilans` always cover the whole month, since the statutory norm follows the
  contract rather than the floor. With one floor those columns disappear.
- **Employees** — add, edit, reorder, part-time fractions, floor assignment,
  end-of-employment without destroying history.
- **Shift types** — fully editable: code, name, hours, category, colour.
- **Excel export** — formatted, colour-coded, print-ready A4 landscape with a
  legend and frozen header, one sheet per floor. Opens in Excel and LibreOffice.
- **Spreadsheet import** — reads `.xlsx` and `.ods` (LibreOffice/OpenOffice).
  Auto-detects the table layout, infers the month from the sheet name, strips
  ordinal prefixes from names (`1. Kowalska`), skips section headers and empty
  roster slots, and maps names to existing employees — all previewed before
  anything is written.
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
  db.py      SQLite storage (versioned schema + migrations)
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
`~/Library/Application Support/Grafik` on macOS), not in the repo. A fresh
install starts empty — no employees, no entries, just the seven default shift
codes. Nothing is bundled into the installer.

Flags for testing without touching real data:

```bash
.venv/bin/python -m app --demo                  # sample ward in a separate demo.db
.venv/bin/python -m app --demo --month 2026-06  # open a specific month
.venv/bin/python -m app --db /tmp/scratch.db    # throwaway database
```

`--demo` marks the window title so it can't be mistaken for real data. Delete
the data directory to get the clean-install experience back.

## Building the Windows executable

PyInstaller cannot cross-compile, so **the Windows build must run on Windows** —
either a Windows machine or the included GitHub Actions workflow. Nothing about
the resulting program needs Python on the target machine; the interpreter and Qt
are bundled.

Two artifacts are produced:

| File | What it is |
|---|---|
| `Grafik-Instalator-<ver>.exe` | Installer. Creates a desktop shortcut, installs per-user (no admin rights). Fast startup. **Recommended.** |
| `Grafik-<ver>-przenosny.exe` | Single self-contained file. Copy anywhere and double-click, no installation. Starts a few seconds slower — it unpacks itself each run. |

### Via GitHub Actions (no Windows machine needed)

Push the repo to GitHub, then either tag a release:

```bash
git tag v1.0.0 && git push --tags
```

or trigger **Actions → Build Windows → Run workflow** for an untagged build.
The workflow runs the tests, stamps the version into the executable metadata,
builds both artifacts, verifies both exist, and — for a tag — attaches them to
the GitHub release. Untagged runs leave them as a downloadable artifact.

### On a Windows machine

```powershell
pip install -r requirements-dev.txt
pyinstaller grafik.spec --noconfirm --clean
```

That yields `dist\Grafik\Grafik.exe` (directory build) and
`dist\Grafik-przenosny.exe`. For the installer, install
[Inno Setup 6](https://jrsoftware.org/isdl.php) and run:

```powershell
& "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe" /DAppVersion=1.0.0 packaging\grafik.iss
```

### SmartScreen

The executables are unsigned, so Windows shows *"Windows protected your PC"* on
first run. The user clicks **More info → Run anyway**, once. Removing that
prompt requires a code-signing certificate (a paid, identity-verified purchase);
nothing in the build can suppress it. `packaging/INSTALACJA.md` is a plain-Polish
install guide covering this, written for the end user rather than a developer.

## Photo import

Requires Tesseract OCR with the Polish language pack. The app detects it and
explains how to install it if missing — everything else works without it.

- Windows: installer from <https://github.com/UB-Mannheim/tesseract/wiki>
  (tick Polish). The app finds it in `C:\Program Files\Tesseract-OCR`.
- macOS: `brew install tesseract tesseract-lang`

Accuracy depends heavily on photo quality. The result always lands in the
import preview for correction; unrecognised entries appear red in the grid.
