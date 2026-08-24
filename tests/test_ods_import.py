"""Testy importu arkuszy OpenDocument (.ods) — układ jak w prawdziwym grafiku."""
import pytest

from app.io import xlsx_import as xi

odf = pytest.importorskip("odf.opendocument")


def make_ods(path, sheet_name, rows):
    """Buduje plik .ods z listy wierszy (listy tekstów)."""
    from odf.opendocument import OpenDocumentSpreadsheet
    from odf.table import Table, TableCell, TableRow
    from odf.text import P

    doc = OpenDocumentSpreadsheet()
    table = Table(name=sheet_name)
    for row in rows:
        tr = TableRow()
        for value in row:
            cell = TableCell(valuetype="string")
            cell.addElement(P(text=str(value)))
            tr.addElement(cell)
        table.addElement(tr)
    doc.spreadsheet.addElement(table)
    doc.save(str(path))
    return path


@pytest.fixture
def ward_sheet(tmp_path):
    """Odwzorowuje układ arkusza używanego na oddziale.

    Tytuł, pusty wiersz, nagłówek z dniami 1-31, nagłówek sekcji ("I PIĘTRO"),
    nazwiska z numeracją porządkową i puste pozycje na końcu listy.
    """
    days = [str(d) for d in range(1, 32)]
    rows = [
        ["Harmonogram czasu pracy"], [], [],
        ["Nazwisko i imię", "", ""] + days,
        ["I PIĘTRO", "", ""] + [""] * 31,
        ["1. Dejnek Agata", "", ""] + ["N", "", "", "D"] + [""] * 27,
        ["2. Dudzińska Aneta", "", ""] + ["D", "", "U", "U"] + [""] * 27,
        ["10.Dyszewska Małgorzata", "", ""] + ["", "D", "N", "7,3"] + [""] * 27,
        ["14.", "", ""] + [""] * 31,
        ["15.", "", ""] + [""] * 31,
    ]
    return make_ods(tmp_path / "CZERWIEC.ods", "CZERWIEC", rows)


def test_reads_ods_files(ward_sheet):
    grids = xi.read_sheets(ward_sheet)
    assert len(grids) == 1
    assert grids[0].name == "CZERWIEC"


def test_detects_layout_of_real_ward_sheet(ward_sheet):
    grid = xi.read_sheets(ward_sheet)[0]
    layout = xi.detect_layout(grid, 30)
    assert layout.ok
    assert layout.header_row == 3
    assert layout.name_col == 0
    assert len(layout.day_cols) == 31


def test_strips_ordinal_prefixes_from_names(ward_sheet):
    grid = xi.read_sheets(ward_sheet)[0]
    rows = xi.extract_rows(grid, xi.detect_layout(grid, 30))
    assert [r.source_name for r in rows] == [
        "Dejnek Agata", "Dudzińska Aneta", "Dyszewska Małgorzata",
    ]


def test_skips_section_headers_and_empty_positions(ward_sheet):
    """„I PIĘTRO" i puste pozycje 14./15. nie są pracownikami."""
    grid = xi.read_sheets(ward_sheet)[0]
    rows = xi.extract_rows(grid, xi.detect_layout(grid, 30))
    names = {r.source_name for r in rows}
    assert "I PIĘTRO" not in names
    assert not any(n.strip(". ").isdigit() for n in names)


def test_entries_land_on_the_right_days(ward_sheet):
    grid = xi.read_sheets(ward_sheet)[0]
    rows = xi.extract_rows(grid, xi.detect_layout(grid, 30))
    dejnek = rows[0]
    assert dejnek.entries[1] == "N"
    assert dejnek.entries[4] == "D"
    assert dejnek.entries[2] == ""


def test_day_31_is_discarded_when_month_is_shorter(ward_sheet, tmp_path):
    from app.db import Database

    grid = xi.read_sheets(ward_sheet)[0]
    rows = xi.extract_rows(grid, xi.detect_layout(grid, 30))
    for row in rows:
        row.entries[31] = "D"   # szablon ma zawsze 31 kolumn
    db = Database(tmp_path / "t.db")
    xi.match_employees(rows, db.employees())
    xi.apply_import(db, 2026, 6, rows)      # czerwiec ma 30 dni
    assert all(day.day <= 30 for _, day in db.month_entries(2026, 6))
    db.close()


@pytest.mark.parametrize("text,expected", [
    ("1. Kowalska Anna", "Kowalska Anna"),
    ("10.Nowak Maria", "Nowak Maria"),
    ("3) Wiśniewska", "Wiśniewska"),
    ("Kowalska Anna", "Kowalska Anna"),
    ("14.", ""),
])
def test_strip_ordinal(text, expected):
    assert xi.strip_ordinal(text) == expected


@pytest.mark.parametrize("sheet,filename,expected", [
    ("CZERWIEC", "", (None, 6)),
    ("SIERPIEŃ 2026", "", (2026, 8)),
    ("Arkusz1", "SIERPIEŃ 2026(1)", (2026, 8)),
    ("CZERWIEC", "SIERPIEŃ 2026", (2026, 6)),   # arkusz ma pierwszeństwo
    ("PAŹDZIERNIK", "", (None, 10)),
    ("Arkusz1", "", (None, None)),
])
def test_guess_month(sheet, filename, expected):
    assert xi.guess_month(sheet, filename) == expected


def test_name_matching_ignores_ordinal_prefix(tmp_path):
    from app.db import Database
    db = Database(tmp_path / "t.db")
    db.add_employee("Dejnek", "Agata")
    rows = [xi.ImportedRow(source_name="1. Dejnek Agata", entries={1: "D"})]
    xi.match_employees(rows, db.employees())
    assert rows[0].employee_id is not None
    db.close()
