"""Testy budowania składu grafiku: kopiowanie, dodawanie, usuwanie."""
import datetime as dt

import pytest

from app.db import Database


@pytest.fixture
def db(tmp_path):
    database = Database(tmp_path / "t.db")
    yield database
    database.close()


@pytest.fixture
def ward(db):
    f1, f2 = (f["id"] for f in db.floors())
    anna = db.add_employee("Pierwsza", "Anna")
    maria = db.add_employee("Druga", "Maria")
    ewa = db.add_employee("Trzecia", "Ewa")
    return db, f1, f2, anna, maria, ewa


def _names(rows):
    return sorted(r["last_name"] for r in rows)


# --- pusty początek ---------------------------------------------------------

def test_a_new_month_starts_empty(ward):
    """Kolejny miesiąc zaczyna się od czystej karty."""
    db, f1, _, anna, _, _ = ward
    db.set_entry(anna, dt.date(2026, 6, 1), "D", f1)
    assert db.employees_on_floor(2026, 6, f1) != []
    assert db.employees_on_floor(2026, 7, f1) == []


# --- kopiowanie składu ------------------------------------------------------

def test_copying_the_team_brings_people_without_their_shifts(ward):
    db, f1, _, anna, maria, _ = ward
    db.set_entry(anna, dt.date(2026, 6, 1), "D", f1)
    db.add_to_roster(2026, 6, f1, [maria])

    added = db.copy_roster((2026, 6), (2026, 7), f1)
    assert added == 2
    assert _names(db.employees_on_floor(2026, 7, f1)) == ["Druga", "Pierwsza"]
    # Same dyżury nie są kopiowane — lipiec zostaje pusty.
    assert db.month_entries(2026, 7) == {}


def test_copying_twice_adds_nobody_new(ward):
    db, f1, _, anna, _, _ = ward
    db.add_to_roster(2026, 6, f1, [anna])
    assert db.copy_roster((2026, 6), (2026, 7), f1) == 1
    assert db.copy_roster((2026, 6), (2026, 7), f1) == 0
    assert len(db.employees_on_floor(2026, 7, f1)) == 1


def test_people_who_have_left_are_not_copied(ward):
    db, f1, _, anna, maria, _ = ward
    db.add_to_roster(2026, 6, f1, [anna, maria])
    db.update_employee(maria, active=0, ended_on="2026-06-30")

    db.copy_roster((2026, 6), (2026, 7), f1)
    assert _names(db.employees_on_floor(2026, 7, f1)) == ["Pierwsza"]


def test_copying_keeps_floors_apart(ward):
    db, f1, f2, anna, maria, _ = ward
    db.add_to_roster(2026, 6, f1, [anna])
    db.add_to_roster(2026, 6, f2, [maria])

    db.copy_roster((2026, 6), (2026, 7), f1)
    assert _names(db.employees_on_floor(2026, 7, f1)) == ["Pierwsza"]
    assert db.employees_on_floor(2026, 7, f2) == []


def test_copying_from_an_empty_month_does_nothing(ward):
    db, f1, _, _, _, _ = ward
    assert db.copy_roster((2026, 5), (2026, 6), f1) == 0


# --- liczba dyżurów ---------------------------------------------------------

def test_shift_counts_are_per_floor(ward):
    db, f1, f2, anna, _, _ = ward
    db.set_entry(anna, dt.date(2026, 6, 1), "D", f1)
    db.set_entry(anna, dt.date(2026, 6, 2), "D", f1)
    db.set_entry(anna, dt.date(2026, 6, 3), "N", f2)

    assert db.shift_counts_on_floor(2026, 6, f1) == {anna: 2}
    assert db.shift_counts_on_floor(2026, 6, f2) == {anna: 1}
    assert db.shift_counts_on_floor(2026, 6, None) == {anna: 3}


# --- usuwanie ze składu -----------------------------------------------------

def test_removing_someone_without_shifts(ward):
    db, f1, _, anna, maria, _ = ward
    db.add_to_roster(2026, 6, f1, [anna, maria])

    removed = db.remove_from_rota(2026, 6, f1, [maria])
    assert removed == 0
    assert _names(db.employees_on_floor(2026, 6, f1)) == ["Pierwsza"]


def test_removing_several_people_at_once(ward):
    db, f1, _, anna, maria, ewa = ward
    db.add_to_roster(2026, 6, f1, [anna, maria, ewa])

    db.remove_from_rota(2026, 6, f1, [anna, ewa])
    assert _names(db.employees_on_floor(2026, 6, f1)) == ["Druga"]


def test_removing_with_shifts_deletes_only_that_floors_entries(ward):
    db, f1, f2, anna, _, _ = ward
    db.set_entry(anna, dt.date(2026, 6, 1), "D", f1)
    db.set_entry(anna, dt.date(2026, 6, 2), "N", f2)

    removed = db.remove_from_rota(2026, 6, f1, [anna], drop_shifts=True)
    assert removed == 1
    assert db.month_entries(2026, 6, f1) == {}
    # Dyżur na drugim piętrze nietknięty.
    assert db.month_entries(2026, 6, f2) == {(anna, dt.date(2026, 6, 2)): "N"}


def test_removing_leaves_other_months_alone(ward):
    db, f1, _, anna, _, _ = ward
    db.set_entry(anna, dt.date(2026, 6, 1), "D", f1)
    db.set_entry(anna, dt.date(2026, 7, 1), "D", f1)

    db.remove_from_rota(2026, 6, f1, [anna], drop_shifts=True)
    assert db.month_entries(2026, 6, f1) == {}
    assert db.month_entries(2026, 7, f1) == {(anna, dt.date(2026, 7, 1)): "D"}


def test_removing_does_not_delete_the_employee(ward):
    db, f1, _, anna, _, _ = ward
    db.add_to_roster(2026, 6, f1, [anna])
    db.remove_from_rota(2026, 6, f1, [anna])
    assert anna in [e["id"] for e in db.employees()]
