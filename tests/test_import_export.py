"""Testy zapisu i odczytu arkuszy."""
import calendar
import datetime as dt

import pytest

from app.db import Database
from app.demo import seed_demo
from app.io import xlsx_import as xi
from app.core.shifts import resolve
from app.io.xlsx_export import export_month


@pytest.fixture
def db(tmp_path):
    database = Database(tmp_path / "test.db")
    yield database
    database.close()


@pytest.fixture
def seeded(db):
    seed_demo(db, 2026, 9)
    return db


def test_export_creates_readable_file(seeded, tmp_path):
    path = export_month(tmp_path / "g.xlsx", seeded, 2026, 9, "Oddział")
    assert path.exists() and path.stat().st_size > 5000
    grids = xi.read_sheets(path)
    assert len(grids) == 1 and grids[0].name == "Grafik 09-2026"


def test_roundtrip_preserves_every_entry(seeded, tmp_path):
    original = seeded.month_entries(2026, 9)
    path = export_month(tmp_path / "g.xlsx", seeded, 2026, 9)

    grid = xi.read_sheets(path)[0]
    layout = xi.detect_layout(grid, calendar.monthrange(2026, 9)[1])
    assert layout.ok and layout.confidence == 1.0
    assert len(layout.day_cols) == 30

    rows = xi.extract_rows(grid, layout)
    assert len(rows) == len(seeded.employees())

    target = Database(tmp_path / "target.db")
    for emp in seeded.employees():
        target.add_employee(emp["last_name"], emp["first_name"])
    xi.match_employees(rows, target.employees())
    assert all(r.employee_id for r in rows)

    count, created = xi.apply_import(target, 2026, 9, rows)
    assert created == 0

    names_a = {e["id"]: e["last_name"] for e in seeded.employees()}
    names_b = {e["id"]: e["last_name"] for e in target.employees()}
    a = {(names_a[k[0]], k[1]): v for k, v in original.items()}
    b = {(names_b[k[0]], k[1]): v for k, v in target.month_entries(2026, 9).items()}

    # Eksport zapisuje czas w postaci znormalizowanej ("7,3" -> "7:30"), więc
    # porównujemy znaczenie wpisów, a nie dosłowną treść komórek.
    types = seeded.shift_types_by_code()
    assert a.keys() == b.keys()
    for key, raw in a.items():
        before, after = resolve(raw, types), resolve(b[key], types)
        assert (before.minutes, before.category) == (after.minutes, after.category), key

    # Kody zmian muszą przechodzić przez eksport i import bez żadnej zmiany.
    codes = {k: v for k, v in a.items() if v in types}
    assert codes and all(b[k] == v for k, v in codes.items())
    target.close()


def test_import_skips_legend_and_footer_rows(seeded, tmp_path):
    """Eksport dopisuje pod tabelą legendę — nie może trafić do listy pracowników."""
    path = export_month(tmp_path / "g.xlsx", seeded, 2026, 9)
    grid = xi.read_sheets(path)[0]
    rows = xi.extract_rows(grid, xi.detect_layout(grid, 30))
    names = {r.source_name for r in rows}
    assert "Legenda" not in names
    assert not any(r.source_name in {"D", "N", "U", "L4", "UŻ"} for r in rows)


@pytest.mark.parametrize("text,expected", [
    ("1", 1), ("31", 31), ("1 Pn", 1), ("15\nŚr", 15),
    ("01.09", 1), ("2026-09-07", 7), ("32", None), ("razem", None), ("", None),
])
def test_day_number_parsing(text, expected):
    assert xi._day_number(text) == expected


def test_name_normalisation_ignores_diacritics_and_order():
    assert xi.normalize_name("Wiśniewska Katarzyna") == xi.normalize_name("KATARZYNA WISNIEWSKA")
    assert xi.normalize_name("Nowak, Maria") == xi.normalize_name("maria nowak")


def test_matching_falls_back_to_surname(db):
    db.add_employee("Kowalska", "Anna")
    rows = [xi.ImportedRow(source_name="Kowalska A.", entries={1: "D"})]
    xi.match_employees(rows, db.employees())
    assert rows[0].employee_id is not None and not rows[0].create_new


def test_import_creates_unknown_employees(db):
    rows = [xi.ImportedRow(source_name="Nowa Osoba", entries={1: "D", 2: "N"}, create_new=True)]
    count, created = xi.apply_import(db, 2026, 9, rows)
    assert (count, created) == (2, 1)
    assert db.employees()[0]["last_name"] == "Nowa"


def test_import_ignores_days_outside_month(db):
    emp = db.add_employee("Testowa", "Osoba")
    rows = [xi.ImportedRow(source_name="Testowa Osoba",
                           entries={30: "D", 31: "N"}, employee_id=emp)]
    # Wrzesień ma 30 dni — wpis z 31. musi zostać pominięty.
    count, _ = xi.apply_import(db, 2026, 9, rows)
    assert count == 1
    assert db.month_entries(2026, 9) == {(emp, dt.date(2026, 9, 30)): "D"}


def test_matching_never_uses_first_names(db):
    """Dwie Ewy na oddziale to norma — imię nie może decydować o dopasowaniu."""
    db.add_employee("Przykładowa", "Ewa")
    rows = [xi.ImportedRow(source_name="Mazurek Ewa", entries={1: "D"})]
    xi.match_employees(rows, db.employees())
    assert rows[0].employee_id is None
    assert rows[0].create_new


def test_matching_is_case_and_diacritic_insensitive(db):
    emp = db.add_employee("Dudzińska", "Aneta")
    rows = [xi.ImportedRow(source_name="DUDZINSKA ANETA", entries={1: "D"})]
    xi.match_employees(rows, db.employees())
    assert rows[0].employee_id == emp


def test_matching_by_surname_alone_when_unambiguous(db):
    emp = db.add_employee("Mazurek", "Ewa")
    db.add_employee("Testowy", "Jan")
    for source in ("Mazurek", "Mazurek A.", "1. Mazurek Ewa"):
        rows = [xi.ImportedRow(source_name=source, entries={1: "D"})]
        xi.match_employees(rows, db.employees())
        assert rows[0].employee_id == emp, source


def test_shared_surname_is_left_for_the_user_to_decide(db):
    """Przy dwóch osobach o tym samym nazwisku zgadywanie byłoby ryzykowne."""
    db.add_employee("Nowak", "Anna")
    db.add_employee("Nowak", "Maria")
    rows = [xi.ImportedRow(source_name="Nowak", entries={1: "D"})]
    xi.match_employees(rows, db.employees())
    assert rows[0].employee_id is None

    # Pełne imię i nazwisko nadal rozstrzyga jednoznacznie.
    rows = [xi.ImportedRow(source_name="Nowak Maria", entries={1: "D"})]
    xi.match_employees(rows, db.employees())
    assert rows[0].employee_id is not None


def test_unmatched_rows_default_to_creating_employees(db):
    """Import ma sam zakładać brakujących pracowników."""
    rows = [
        xi.ImportedRow(source_name="Dejnek Agata", entries={1: "D"}),
        xi.ImportedRow(source_name="Tryk Emilia", entries={2: "N"}),
    ]
    xi.match_employees(rows, db.employees())
    assert all(r.create_new for r in rows)
    count, created = xi.apply_import(db, 2026, 6, rows)
    assert (count, created) == (2, 2)
    assert {e["last_name"] for e in db.employees()} == {"Dejnek", "Tryk"}
