"""Testy czyszczenia danych — po testach na danych przykładowych."""
import datetime as dt

import pytest

from app.db import Database
from app.demo import seed_demo


@pytest.fixture
def filled(tmp_path):
    db = Database(tmp_path / "t.db")
    db.set_setting("ward_name", "Oddział testowy")
    db.set_setting("update_repo", "ktos/grafik")
    seed_demo(db, 2026, 6)
    yield db
    db.close()


def test_summary_counts_what_is_there(filled):
    counts = filled.data_summary()
    assert counts["employees"] == 10
    assert counts["entries"] > 100
    assert counts["months"] == 1
    assert counts["floors"] == 2


def test_clearing_rotas_keeps_people_and_settings(filled):
    filled.reset_data(keep_employees=True, keep_settings=True)

    assert filled.month_entries(2026, 6) == {}
    assert filled.months_with_data() == []
    assert len(filled.employees()) == 10
    assert filled.get_setting("ward_name") == "Oddział testowy"
    assert filled.get_setting("update_repo") == "ktos/grafik"
    assert len(filled.shift_types()) > 0
    assert len(filled.floors()) == 2


def test_clearing_everything_returns_to_a_fresh_install(filled):
    filled.reset_data(keep_employees=False, keep_settings=False)

    assert filled.employees() == []
    assert filled.month_entries(2026, 6) == {}
    assert filled.get_setting("ward_name") == ""
    assert filled.get_setting("update_repo") == ""
    # Wartości domyślne wracają, żeby program nadal dało się używać.
    assert [f["name"] for f in filled.floors()] == ["I piętro", "II piętro"]
    assert {t.code for t in filled.shift_types()} >= {"D", "N", "U", "L4"}


def test_reset_keeps_the_database_usable(filled, tmp_path):
    filled.reset_data(keep_employees=False, keep_settings=False)
    # Po wyczyszczeniu można od razu pracować dalej.
    emp = filled.add_employee("Nowa", "Osoba")
    filled.set_entry(emp, dt.date(2026, 7, 1), "D")
    assert filled.month_entries(2026, 7) == {(emp, dt.date(2026, 7, 1)): "D"}


def test_schema_version_survives_a_full_reset(filled, tmp_path):
    """Po wyczyszczeniu baza nie może wyglądać jak plik nieznanej wersji."""
    from app.db import SCHEMA_VERSION

    filled.reset_data(keep_employees=False, keep_settings=False)
    assert filled.get_setting("schema_version") == str(SCHEMA_VERSION)
    filled.close()

    reopened = Database(tmp_path / "t.db")
    assert reopened.last_upgrade_backup is None    # brak zbędnej migracji
    reopened.close()


def test_clearing_rotas_leaves_both_floors_empty(filled):
    floors = filled.floors()
    filled.reset_data(keep_employees=True, keep_settings=True)
    for floor in floors:
        assert filled.month_entries(2026, 6, floor["id"]) == {}
