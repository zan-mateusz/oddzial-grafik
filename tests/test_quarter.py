"""Testy bilansu kwartalnego i kolorów bilansu."""
import datetime as dt

import pytest

from app.core.calendar_pl import month_norm, quarter_months, quarter_of
from app.core.shifts import fmt_signed
from app.db import Database


@pytest.fixture
def db(tmp_path):
    database = Database(tmp_path / "t.db")
    yield database
    database.close()


# --- podział na kwartały ----------------------------------------------------

@pytest.mark.parametrize("month,expected", [
    (1, 1), (3, 1), (4, 2), (6, 2), (7, 3), (9, 3), (10, 4), (12, 4),
])
def test_quarter_of(month, expected):
    assert quarter_of(month) == expected


@pytest.mark.parametrize("month,months", [
    (2, [1, 2, 3]), (5, [4, 5, 6]), (8, [7, 8, 9]), (11, [10, 11, 12]),
])
def test_quarter_months(month, months):
    assert [m for _, m in quarter_months(2026, month)] == months


def test_quarter_never_crosses_the_year():
    assert quarter_months(2026, 12) == [(2026, 10), (2026, 11), (2026, 12)]
    assert quarter_months(2026, 1) == [(2026, 1), (2026, 2), (2026, 3)]


# --- format i kolor ---------------------------------------------------------

@pytest.mark.parametrize("minutes,text", [
    (500, "+8:20"), (-90, "-1:30"), (0, "0:00"),
])
def test_fmt_signed(minutes, text):
    assert fmt_signed(minutes) == text


def test_balance_colour_follows_the_sign():
    """Brak godzin na czerwono, nadgodziny na zielono, równo na czarno."""
    from app.ui.rota_model import (
        BALANCE_EVEN, BALANCE_OVER, BALANCE_SHORT, balance_colour,
    )

    assert balance_colour(-1) is BALANCE_SHORT
    assert balance_colour(1) is BALANCE_OVER
    assert balance_colour(0) is BALANCE_EVEN


def test_export_uses_the_same_colour_rule():
    from app.io.xlsx_export import _balance_colour

    assert _balance_colour(-60) == "B00020"      # czerwony
    assert _balance_colour(60) == "15803D"       # zielony
    assert _balance_colour(0) == "000000"        # czarny


# --- bilans narastająco -----------------------------------------------------

def _fill_month(db, emp, year, month, code="D", days=20):
    floor = db.floors()[0]["id"]
    added = 0
    day = dt.date(year, month, 1)
    while added < days and day.month == month:
        db.set_entry(emp, day, code, floor)
        added += 1
        day += dt.timedelta(days=1)


def _model(db, year, month):
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    QApplication.instance() or QApplication([])
    from app.ui.rota_model import RotaModel

    return RotaModel(db, year, month, db.floors()[0]["id"])


def test_quarter_adds_up_the_months_already_planned(db):
    emp = db.add_employee("Testowa", "Osoba")
    _fill_month(db, emp, 2026, 7, days=20)       # lipiec
    _fill_month(db, emp, 2026, 8, days=20)       # sierpień

    model = _model(db, 2026, 8)
    july = 20 * 720 - month_norm(2026, 7).minutes
    august = 20 * 720 - month_norm(2026, 8).minutes
    assert model.quarter_balance[emp] == july + august
    assert model.quarter_months == [(2026, 7), (2026, 8)]


def test_unplanned_future_months_are_left_out(db):
    """Pusty wrzesień nie może zaniżać kwartału o cały swój wymiar."""
    emp = db.add_employee("Testowa", "Osoba")
    _fill_month(db, emp, 2026, 7, days=20)

    model = _model(db, 2026, 7)
    assert model.quarter_months == [(2026, 7)]
    assert model.quarter_balance[emp] == 20 * 720 - month_norm(2026, 7).minutes


def test_the_month_being_viewed_always_counts(db):
    """Nawet pusty — tak samo jak w kolumnie miesięcznej."""
    emp = db.add_employee("Testowa", "Osoba")
    _fill_month(db, emp, 2026, 7, days=20)

    model = _model(db, 2026, 8)                  # sierpień jeszcze pusty
    assert (2026, 8) in model.quarter_months
    assert model.quarter_balance[emp] == (
        20 * 720 - month_norm(2026, 7).minutes - month_norm(2026, 8).minutes
    )


def test_quarter_resets_between_quarters(db):
    emp = db.add_employee("Testowa", "Osoba")
    _fill_month(db, emp, 2026, 6, days=20)       # II kwartał
    _fill_month(db, emp, 2026, 7, days=20)       # III kwartał

    july_only = _model(db, 2026, 7)
    assert july_only.quarter_months == [(2026, 7)]
    assert july_only.quarter_balance[emp] == 20 * 720 - month_norm(2026, 7).minutes


def test_quarter_matches_the_month_when_only_one_is_planned(db):
    emp = db.add_employee("Testowa", "Osoba")
    _fill_month(db, emp, 2026, 4, days=18)

    model = _model(db, 2026, 4)
    values = model._summary_values(emp)
    assert values["bilans"] == values["kwartal"]


def test_quarter_appears_in_the_export(db, tmp_path):
    from app.io import xlsx_import as xi
    from app.io.xlsx_export import export_month

    emp = db.add_employee("Testowa", "Osoba")
    _fill_month(db, emp, 2026, 7, days=20)
    _fill_month(db, emp, 2026, 8, days=20)

    path = export_month(tmp_path / "g.xlsx", db, 2026, 8)
    sheet = xi.read_sheets(path)[0]
    headers = [c for c in sheet.cells[3] if c]
    assert "Kwartał" in headers

    model = _model(db, 2026, 8)
    expected = fmt_signed(model.quarter_balance[emp])
    assert any(expected in row for row in sheet.cells)
