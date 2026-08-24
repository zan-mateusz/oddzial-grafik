"""Testy podziału na piętra i zastępstw między nimi."""
import datetime as dt
import sqlite3

import pytest

from app.core.calendar_pl import month_norm
from app.core.shifts import resolve
from app.core.stats import summarize_month
from app.db import Database
from app.io import xlsx_import as xi
from app.io.xlsx_export import export_month


@pytest.fixture
def db(tmp_path):
    database = Database(tmp_path / "t.db")
    yield database
    database.close()


@pytest.fixture
def ward(db):
    """Dwa piętra, po jednej pielęgniarce na każdym."""
    f1, f2 = (f["id"] for f in db.floors())
    anna = db.add_employee("Kowalska", "Anna", floor_id=f1)
    maria = db.add_employee("Nowak", "Maria", floor_id=f2)
    return db, f1, f2, anna, maria


def test_new_database_has_two_floors(db):
    assert [f["name"] for f in db.floors()] == ["I piętro", "II piętro"]


def test_employees_are_listed_per_floor(ward):
    db, f1, f2, anna, maria = ward
    assert [e["id"] for e in db.employees(floor_id=f1)] == [anna]
    assert [e["id"] for e in db.employees(floor_id=f2)] == [maria]


def test_shift_defaults_to_the_employees_own_floor(ward):
    db, f1, f2, anna, _ = ward
    db.set_entry(anna, dt.date(2026, 6, 1), "D")
    assert db.month_entries(2026, 6, f1) == {(anna, dt.date(2026, 6, 1)): "D"}
    assert db.month_entries(2026, 6, f2) == {}


def test_cover_shift_appears_on_the_other_floor(ward):
    db, f1, f2, anna, _ = ward
    db.set_entry(anna, dt.date(2026, 6, 2), "N", f2)
    assert db.month_entries(2026, 6, f1) == {}
    assert db.month_entries(2026, 6, f2) == {(anna, dt.date(2026, 6, 2)): "N"}
    # Anna pojawia się w składzie drugiego piętra mimo innego piętra macierzystego.
    assert anna in [e["id"] for e in db.employees_for_month(2026, 6, f2)]


def test_covering_nurse_is_not_lost_from_her_own_floor(ward):
    db, f1, f2, anna, _ = ward
    db.set_entry(anna, dt.date(2026, 6, 2), "N", f2)
    assert anna in [e["id"] for e in db.employees_for_month(2026, 6, f1)]


def test_hours_count_towards_the_month_regardless_of_floor(ward):
    db, f1, f2, anna, _ = ward
    for day in range(1, 6):
        db.set_entry(anna, dt.date(2026, 6, day), "D", f1)
    for day in range(8, 11):
        db.set_entry(anna, dt.date(2026, 6, day), "D", f2)

    types = db.shift_types_by_code()
    everything = {k: resolve(v, types) for k, v in db.month_entries(2026, 6).items()}
    employees = db.employees_for_month(2026, 6, f1)
    total = summarize_month(2026, 6, employees, everything)[anna]
    assert total.shift_days == 8
    assert total.worked_minutes == 8 * 720

    only_first = {k: resolve(v, types) for k, v in db.month_entries(2026, 6, f1).items()}
    on_floor = summarize_month(2026, 6, employees, only_first)[anna]
    assert on_floor.shift_days == 5

    # Wymiar to sprawa umowy, nie piętra — bilans liczy się od pełnego miesiąca.
    assert total.norm_minutes == month_norm(2026, 6).minutes


def test_clearing_one_floor_leaves_the_other_untouched(ward):
    db, f1, f2, anna, maria = ward
    db.set_entry(anna, dt.date(2026, 6, 1), "D", f1)
    db.set_entry(maria, dt.date(2026, 6, 1), "D", f2)
    db.clear_month(2026, 6, f1)
    assert db.month_entries(2026, 6, f1) == {}
    assert db.month_entries(2026, 6, f2) == {(maria, dt.date(2026, 6, 1)): "D"}


def test_one_shift_per_person_per_day(ward):
    """Wpisanie dyżuru na drugim piętrze przenosi go, a nie dubluje."""
    db, f1, f2, anna, _ = ward
    db.set_entry(anna, dt.date(2026, 6, 3), "D", f1)
    db.set_entry(anna, dt.date(2026, 6, 3), "N", f2)
    assert db.month_entries(2026, 6, f1) == {}
    assert db.month_entries(2026, 6, f2) == {(anna, dt.date(2026, 6, 3)): "N"}
    assert len(db.month_entries(2026, 6)) == 1


def test_export_writes_a_sheet_per_floor(ward, tmp_path):
    db, f1, f2, anna, maria = ward
    db.set_entry(anna, dt.date(2026, 6, 1), "D", f1)
    db.set_entry(maria, dt.date(2026, 6, 1), "D", f2)
    path = export_month(tmp_path / "g.xlsx", db, 2026, 6, "Oddział")
    assert [g.name for g in xi.read_sheets(path)] == ["I piętro", "II piętro"]


def test_export_sheet_shows_covering_nurse(ward, tmp_path):
    db, f1, f2, anna, _ = ward
    db.set_entry(anna, dt.date(2026, 6, 2), "N", f2)
    path = export_month(tmp_path / "g.xlsx", db, 2026, 6)
    second = [g for g in xi.read_sheets(path) if g.name == "II piętro"][0]
    text = "\n".join(" ".join(row) for row in second.cells)
    assert "Kowalska" in text and "zastępstwo" in text


def test_import_targets_a_single_floor(ward):
    db, f1, f2, _, _ = ward
    rows = [xi.ImportedRow(source_name="Dejnek Agata", entries={1: "D"}, create_new=True)]
    xi.apply_import(db, 2026, 6, rows, floor_id=f2)
    created = [e for e in db.employees() if e["last_name"] == "Dejnek"][0]
    assert created["floor_id"] == f2
    assert db.month_entries(2026, 6, f2)[(created["id"], dt.date(2026, 6, 1))] == "D"
    assert db.month_entries(2026, 6, f1) == {}


def test_import_replace_does_not_wipe_the_other_floor(ward):
    db, f1, f2, anna, maria = ward
    db.set_entry(anna, dt.date(2026, 6, 5), "D", f1)
    rows = [xi.ImportedRow(source_name="Nowak Maria", entries={1: "N"}, employee_id=maria)]
    xi.apply_import(db, 2026, 6, rows, replace=True, floor_id=f2)
    assert db.month_entries(2026, 6, f1) == {(anna, dt.date(2026, 6, 5)): "D"}


def test_migration_from_single_floor_database(tmp_path):
    """Baza sprzed podziału na piętra musi zachować wszystkie dane."""
    path = tmp_path / "old.db"
    con = sqlite3.connect(path)
    con.executescript("""
        CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE employees(id INTEGER PRIMARY KEY AUTOINCREMENT,
          last_name TEXT NOT NULL, first_name TEXT NOT NULL DEFAULT '',
          position TEXT NOT NULL DEFAULT '', fte_num INTEGER NOT NULL DEFAULT 1,
          fte_den INTEGER NOT NULL DEFAULT 1, active INTEGER NOT NULL DEFAULT 1,
          sort_order INTEGER NOT NULL DEFAULT 0, hired_on TEXT, ended_on TEXT,
          notes TEXT NOT NULL DEFAULT '');
        CREATE TABLE entries(employee_id INTEGER NOT NULL, day TEXT NOT NULL,
          raw TEXT NOT NULL, PRIMARY KEY(employee_id, day));
        CREATE TABLE shift_types(id INTEGER PRIMARY KEY AUTOINCREMENT,
          code TEXT NOT NULL UNIQUE, name TEXT NOT NULL DEFAULT '', start_time TEXT,
          end_time TEXT, category TEXT NOT NULL DEFAULT 'praca',
          color TEXT NOT NULL DEFAULT '#E8EDF4', minutes_override INTEGER,
          sort_order INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE months(year INTEGER, month INTEGER, note TEXT DEFAULT '',
          locked INTEGER DEFAULT 0, PRIMARY KEY(year, month));
        INSERT INTO meta VALUES('schema_version','1');
        INSERT INTO employees(last_name) VALUES('Kowalska'),('Nowak');
        INSERT INTO entries VALUES(1,'2026-06-01','D'),(2,'2026-06-01','U');
    """)
    con.commit()
    con.close()

    db = Database(path)
    assert db.get_setting("schema_version") == "2"
    first = db.floors()[0]["id"]
    assert all(e["floor_id"] == first for e in db.employees())
    assert db.month_entries(2026, 6, first) == {
        (1, dt.date(2026, 6, 1)): "D", (2, dt.date(2026, 6, 1)): "U",
    }
    db.close()


def test_clearing_a_cell_does_not_erase_the_other_floors_shift(ward):
    """Pusta komórka znaczy „nie pracuje tutaj", nie „nie pracuje nigdzie"."""
    db, f1, f2, anna, _ = ward
    db.set_entry(anna, dt.date(2026, 6, 4), "N", f2)      # zastępstwo
    db.set_entry(anna, dt.date(2026, 6, 4), "", f1)       # czyszczenie na I piętrze
    assert db.month_entries(2026, 6, f2) == {(anna, dt.date(2026, 6, 4)): "N"}


def test_clearing_without_a_floor_removes_the_shift_entirely(ward):
    db, f1, f2, anna, _ = ward
    db.set_entry(anna, dt.date(2026, 6, 4), "N", f2)
    db.set_entry(anna, dt.date(2026, 6, 4), "")
    assert db.month_entries(2026, 6) == {}


def test_importing_one_floor_keeps_the_other_floors_shifts(ward):
    """Puste komórki w arkuszu jednego piętra nie mogą kasować drugiego."""
    db, f1, f2, anna, maria = ward
    db.set_entry(anna, dt.date(2026, 6, 10), "D", f1)
    # Arkusz II piętra zawiera Annę (zastępstwo) z pustymi polami w innych dniach.
    rows = [xi.ImportedRow(
        source_name="Kowalska Anna",
        entries={day: ("N" if day == 12 else "") for day in range(1, 31)},
        employee_id=anna,
    )]
    xi.apply_import(db, 2026, 6, rows, replace=False, floor_id=f2)
    assert db.month_entries(2026, 6, f1) == {(anna, dt.date(2026, 6, 10)): "D"}
    assert db.month_entries(2026, 6, f2) == {(anna, dt.date(2026, 6, 12)): "N"}
