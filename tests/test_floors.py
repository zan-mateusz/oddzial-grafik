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


def test_the_team_is_shared_by_every_floor(ward):
    """Zespół rotuje między piętrami, więc każde pokazuje ten sam skład."""
    db, f1, f2, anna, maria = ward
    everyone = {e["id"] for e in db.employees_for_month(2026, 6)}
    assert everyone == {anna, maria}


def test_shift_without_a_floor_lands_on_the_first_one(ward):
    """Zdarza się przy danych sprzed podziału na piętra."""
    db, f1, f2, anna, _ = ward
    db.set_entry(anna, dt.date(2026, 6, 1), "D")
    assert db.month_entries(2026, 6, f1) == {(anna, dt.date(2026, 6, 1)): "D"}
    assert db.month_entries(2026, 6, f2) == {}


def test_a_shift_is_recorded_on_the_floor_it_was_worked(ward):
    db, f1, f2, anna, _ = ward
    db.set_entry(anna, dt.date(2026, 6, 2), "N", f2)
    assert db.month_entries(2026, 6, f1) == {}
    assert db.month_entries(2026, 6, f2) == {(anna, dt.date(2026, 6, 2)): "N"}


def test_everyone_stays_visible_on_both_floors(ward):
    db, f1, f2, anna, _ = ward
    db.set_entry(anna, dt.date(2026, 6, 2), "N", f2)
    visible = {e["id"] for e in db.employees_for_month(2026, 6)}
    assert anna in visible


def test_hours_count_towards_the_month_regardless_of_floor(ward):
    db, f1, f2, anna, _ = ward
    for day in range(1, 6):
        db.set_entry(anna, dt.date(2026, 6, day), "D", f1)
    for day in range(8, 11):
        db.set_entry(anna, dt.date(2026, 6, day), "D", f2)

    types = db.shift_types_by_code()
    everything = {k: resolve(v, types) for k, v in db.month_entries(2026, 6).items()}
    employees = db.employees_for_month(2026, 6)
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
    rows = [xi.ImportedRow(source_name="Pierwsza Anna", entries={1: "D"}, create_new=True)]
    xi.apply_import(db, 2026, 6, rows, floor_id=f2)
    created = [e for e in db.employees() if e["last_name"] == "Pierwsza"][0]
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

    from app.db import SCHEMA_VERSION

    db = Database(path)
    assert db.get_setting("schema_version") == str(SCHEMA_VERSION)
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


def test_floor_columns_count_shifts_where_they_happened(ward):
    """Nie ma piętra macierzystego — liczy się miejsce odbycia dyżuru."""
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    QApplication.instance() or QApplication([])
    from app.ui.rota_model import RotaModel

    db, f1, f2, anna, _ = ward
    db.set_entry(anna, dt.date(2026, 6, 1), "D", f1)
    db.set_entry(anna, dt.date(2026, 6, 2), "D", f1)
    db.set_entry(anna, dt.date(2026, 6, 3), "N", f2)

    model = RotaModel(db, 2026, 6, f1)
    values = model._summary_values(anna)
    assert values[f"pietro_{f1}"] == "2 (24:00)"
    assert values[f"pietro_{f2}"] == "1 (12:00)"

    # Widok drugiego piętra pokazuje dokładnie te same liczby.
    model.set_floor(f2)
    assert model._summary_values(anna)[f"pietro_{f1}"] == "2 (24:00)"


def test_an_employee_without_any_shift_still_appears_on_both_floors(ward):
    db, f1, f2, anna, maria = ward
    db.set_entry(anna, dt.date(2026, 6, 1), "D", f1)
    for floor in (f1, f2):
        visible = {e["id"] for e in db.employees_for_month(2026, 6)}
        assert maria in visible, floor


def _app():
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def test_only_people_with_shifts_on_a_floor_are_listed(ward):
    """Zespół potrafi liczyć trzydzieści osób — grafik piętra pokazuje tylko te,
    które faktycznie na nim pracują."""
    _app()
    from app.ui.rota_model import RotaModel

    db, f1, f2, anna, maria = ward
    db.add_employee("Bez", "Dyżurów")
    db.set_entry(anna, dt.date(2026, 6, 1), "D", f1)
    db.set_entry(maria, dt.date(2026, 6, 1), "D", f2)

    first = RotaModel(db, 2026, 6, f1)
    assert [e["id"] for e in first.employees] == [anna]

    second = RotaModel(db, 2026, 6, f2)
    assert [e["id"] for e in second.employees] == [maria]


def test_combined_view_shows_everyone_with_any_shift(ward):
    _app()
    from app.ui.rota_model import RotaModel

    db, f1, f2, anna, maria = ward
    db.set_entry(anna, dt.date(2026, 6, 1), "D", f1)
    db.set_entry(maria, dt.date(2026, 6, 2), "N", f2)

    model = RotaModel(db, 2026, 6, None)
    assert model.combined
    assert {e["id"] for e in model.employees} == {anna, maria}
    # Widoczne są dyżury z obu pięter.
    assert model._entries.keys() == {
        (anna, dt.date(2026, 6, 1)), (maria, dt.date(2026, 6, 2)),
    }


def test_combined_view_cannot_be_edited(ward):
    """Nie wiadomo, na które piętro zapisać dyżur, więc edycja jest wyłączona."""
    _app()
    from PySide6.QtCore import Qt

    from app.ui.rota_model import RotaModel

    db, f1, f2, anna, _ = ward
    db.set_entry(anna, dt.date(2026, 6, 1), "D", f1)

    model = RotaModel(db, 2026, 6, None)
    index = model.index(0, 0)
    assert not (model.flags(index) & Qt.ItemFlag.ItemIsEditable)
    assert model.setData(index, "N") is False
    model.set_range([(0, 1)], "N")
    assert db.month_entries(2026, 6, f2) == {}


def test_a_person_added_to_the_rota_shows_up_without_any_shift(ward):
    _app()
    from app.ui.rota_model import RotaModel

    db, f1, f2, _, _ = ward
    newcomer = db.add_employee("Nowa", "Osoba")

    before = RotaModel(db, 2026, 6, f1)
    assert newcomer not in [e["id"] for e in before.employees]

    db.add_to_roster(2026, 6, f1, [newcomer])
    after = RotaModel(db, 2026, 6, f1)
    assert newcomer in [e["id"] for e in after.employees]
    # Tylko na tym piętrze — drugie zostaje nietknięte.
    assert newcomer not in [e["id"] for e in RotaModel(db, 2026, 6, f2).employees]


def test_being_added_to_the_rota_survives_a_restart(ward, tmp_path):
    """Dopisanie do grafiku jest zapisywane, a nie tylko trzymane w pamięci."""
    db, f1, _, _, _ = ward
    newcomer = db.add_employee("Nowa", "Osoba")
    db.add_to_roster(2026, 6, f1, [newcomer])
    path = db.path
    db.close()

    reopened = Database(path)
    assert newcomer in [e["id"] for e in reopened.employees_on_floor(2026, 6, f1)]
    reopened.close()


def test_the_roster_is_per_month(ward):
    db, f1, _, _, _ = ward
    newcomer = db.add_employee("Nowa", "Osoba")
    db.add_to_roster(2026, 6, f1, [newcomer])
    assert db.employees_on_floor(2026, 7, f1) == []


def test_someone_with_shifts_stays_even_without_a_roster_entry(ward):
    """Dotychczasowe grafiki nie mają wpisów składu — muszą działać jak dotąd."""
    db, f1, _, anna, _ = ward
    db.set_entry(anna, dt.date(2026, 6, 1), "D", f1)
    assert db.roster_ids(2026, 6, f1) == set()
    assert [e["id"] for e in db.employees_on_floor(2026, 6, f1)] == [anna]


def test_export_sheets_list_only_that_floors_team(ward, tmp_path):
    from app.io import xlsx_import as xi
    from app.io.xlsx_export import export_month

    db, f1, f2, anna, maria = ward
    db.add_employee("Bez", "Dyżurów")
    db.set_entry(anna, dt.date(2026, 6, 1), "D", f1)
    db.set_entry(maria, dt.date(2026, 6, 1), "D", f2)

    path = export_month(tmp_path / "g.xlsx", db, 2026, 6)
    sheets = {s.name: s for s in xi.read_sheets(path)}
    first = "\n".join(" ".join(r) for r in sheets["I piętro"].cells)
    second = "\n".join(" ".join(r) for r in sheets["II piętro"].cells)

    assert "Kowalska" in first and "Nowak" not in first
    assert "Nowak" in second and "Kowalska" not in second
    assert "Bez" not in first and "Bez" not in second
