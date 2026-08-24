"""Testy importu arkuszy OpenDocument (.ods) — układ jak w prawdziwym grafiku."""
import pytest

from app.io import xlsx_import as xi

odf = pytest.importorskip("odf.opendocument")


def make_ods(path, *sheets):
    """Buduje plik .ods. Każdy arkusz to para (nazwa, wiersze)."""
    from odf.opendocument import OpenDocumentSpreadsheet
    from odf.table import Table, TableCell, TableRow
    from odf.text import P

    doc = OpenDocumentSpreadsheet()
    for sheet_name, rows in sheets:
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


def ward_rows():
    """Układ arkusza używanego na oddziale."""
    days = [str(d) for d in range(1, 32)]
    return [
        ["Harmonogram czasu pracy"], [], [],
        ["Nazwisko i imię", "", ""] + days,
        ["I PIĘTRO", "", ""] + [""] * 31,
        ["1. Dejnek Agata", "", ""] + ["N", "", "", "D"] + [""] * 27,
        ["2. Dudzińska Aneta", "", ""] + ["D", "", "U", "U"] + [""] * 27,
        ["10.Dyszewska Małgorzata", "", ""] + ["", "D", "N", "7,3"] + [""] * 27,
        ["14.", "", ""] + [""] * 31,
        ["15.", "", ""] + [""] * 31,
    ]


@pytest.fixture
def ward_sheet(tmp_path):
    """Plik z jednym arkuszem — układ jak na oddziale."""
    return make_ods(tmp_path / "CZERWIEC.ods", ("CZERWIEC", ward_rows()))


@pytest.fixture
def workbook_with_empty_sheets(tmp_path):
    """Skoroszyt z pustymi arkuszami przed właściwym grafikiem.

    Tak wygląda prawdziwy plik prowadzony od lat: "Arkusz14", "Arkusz15",
    "Arkusz16" i dopiero potem "CZERWIEC".
    """
    return make_ods(
        tmp_path / "SIERPIEŃ 2026.ods",
        ("Arkusz14", []), ("Arkusz15", []), ("Arkusz16", [[""], [""]]),
        ("CZERWIEC", ward_rows()),
    )


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


def test_picks_the_sheet_that_holds_the_rota(workbook_with_empty_sheets):
    """Puste arkusze na początku skoroszytu nie mogą przesłonić grafiku."""
    grids = xi.read_sheets(workbook_with_empty_sheets)
    assert [g.name for g in grids][:3] == ["Arkusz14", "Arkusz15", "Arkusz16"]

    chosen = xi.best_sheet_index(grids, 30)
    assert grids[chosen].name == "CZERWIEC"

    layout = xi.detect_layout(grids[chosen], 30)
    assert layout.ok
    assert len(xi.extract_rows(grids[chosen], layout)) == 3


def test_best_sheet_index_survives_a_workbook_with_no_rota(tmp_path):
    path = make_ods(tmp_path / "puste.ods", ("Arkusz1", []), ("Arkusz2", [["x"]]))
    grids = xi.read_sheets(path)
    assert xi.best_sheet_index(grids, 30) in range(len(grids))


def test_month_is_taken_from_the_chosen_sheet_not_the_filename(workbook_with_empty_sheets):
    """Plik nazywa się SIERPIEŃ, ale grafik jest na czerwiec."""
    grids = xi.read_sheets(workbook_with_empty_sheets)
    chosen = grids[xi.best_sheet_index(grids, 30)]
    assert xi.guess_month(chosen.name, "SIERPIEŃ 2026") == (2026, 6)
