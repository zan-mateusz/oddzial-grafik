"""Testy zasad rozliczania czasu pracy."""
import datetime as dt

import pytest

from app.core.calendar_pl import NORM_MEDICAL_MINUTES, month_norm
from app.core.rules import (
    NIGHT_WINDOW_MINUTES, Rules, load_rules, save_rules, validate_night_window,
)
from app.core.shifts import DEFAULT_SHIFT_TYPES, resolve
from app.core.stats import night_minutes, summarize_month
from app.db import Database

TYPES = {t.code: t for t in DEFAULT_SHIFT_TYPES}


class FakeEmp(dict):
    pass


def _emp(emp_id=1, num=1, den=1):
    return FakeEmp(id=emp_id, fte_num=num, fte_den=den)


def _leave(start: dt.date, days: int, code="U"):
    entries = {}
    for i in range(days):
        day = start + dt.timedelta(days=i)
        if day.month != start.month:
            break
        entries[(1, day)] = resolve(code, TYPES)
    return entries


# --- pora nocna ------------------------------------------------------------

def test_default_night_window_is_eight_hours():
    rules = Rules()
    assert (rules.night_start, rules.night_end) == (dt.time(22, 0), dt.time(6, 0))
    assert validate_night_window(rules.night_start, rules.night_end) is None


def test_night_shift_credits_exactly_the_window():
    """Dyżur 19:00-7:00 obejmuje całą 8-godzinną porę nocną, nie 10 godzin."""
    assert night_minutes(dt.time(19, 0), dt.time(7, 0)) == NIGHT_WINDOW_MINUTES


@pytest.mark.parametrize("start", [dt.time(21, 0), dt.time(22, 0), dt.time(23, 0)])
def test_any_allowed_window_is_eight_hours_long(start):
    rules = Rules().with_night_window(start)
    assert validate_night_window(rules.night_start, rules.night_end) is None
    assert night_minutes(dt.time(19, 0), dt.time(7, 0), rules) == NIGHT_WINDOW_MINUTES


def test_full_21_to_7_span_is_rejected():
    """Cały przedział 21:00-7:00 to 10 godzin — przepis mówi o ośmiu."""
    assert validate_night_window(dt.time(21, 0), dt.time(7, 0)) is not None


@pytest.mark.parametrize("start,end", [
    (dt.time(20, 0), dt.time(4, 0)),      # zaczyna się przed 21:00
    (dt.time(23, 30), dt.time(7, 30)),    # kończy się po 7:00
    (dt.time(0, 0), dt.time(8, 0)),
])
def test_windows_outside_the_legal_span_are_rejected(start, end):
    assert validate_night_window(start, end) is not None


def test_changing_the_window_changes_counted_hours():
    early = Rules().with_night_window(dt.time(21, 0))
    late = Rules().with_night_window(dt.time(23, 0))
    afternoon = (dt.time(14, 0), dt.time(21, 35))
    assert night_minutes(*afternoon, early) == 35
    assert night_minutes(*afternoon, late) == 0


# --- urlop -----------------------------------------------------------------

def test_leave_is_only_consumed_on_working_days():
    """15 dni kalendarzowych z rzędu to 11 dni urlopu (2 tygodnie + 1 dzień)."""
    entries = _leave(dt.date(2026, 7, 6), 15)     # poniedziałek, brak świąt
    s = summarize_month(2026, 7, [_emp()], entries)[1]
    assert s.leave_entries == 15
    assert s.leave_days == 11
    assert s.leave_minutes == 11 * NORM_MEDICAL_MINUTES


def test_three_days_of_leave_count_three_times_the_daily_norm():
    entries = _leave(dt.date(2026, 7, 6), 3)
    s = summarize_month(2026, 7, [_emp()], entries)[1]
    assert s.leave_days == 3
    assert s.leave_minutes == 3 * NORM_MEDICAL_MINUTES


def test_weekend_leave_entries_consume_nothing():
    entries = _leave(dt.date(2026, 7, 11), 2)     # sobota i niedziela
    s = summarize_month(2026, 7, [_emp()], entries)[1]
    assert (s.leave_entries, s.leave_days, s.leave_minutes) == (2, 0, 0)


def test_a_holiday_inside_a_leave_period_does_not_consume_leave():
    """4 czerwca 2026 to Boże Ciało — urlopu tego dnia się nie udziela."""
    entries = _leave(dt.date(2026, 6, 1), 15)
    s = summarize_month(2026, 6, [_emp()], entries)[1]
    assert s.leave_entries == 15
    assert s.leave_days == 10       # o jeden mniej niż w tygodniu bez święta
    assert s.leave_ignored == 5


def test_leave_reduces_the_norm_by_the_days_actually_used():
    full = summarize_month(2026, 7, [_emp()], {})[1]
    entries = _leave(dt.date(2026, 7, 6), 15)
    with_leave = summarize_month(2026, 7, [_emp()], entries)[1]
    assert with_leave.norm_minutes == full.norm_minutes - 11 * NORM_MEDICAL_MINUTES


def test_counting_every_calendar_day_can_be_turned_on():
    rules = Rules(leave_on_working_days_only=False)
    entries = _leave(dt.date(2026, 7, 6), 15)
    s = summarize_month(2026, 7, [_emp()], entries, rules)[1]
    assert s.leave_days == 15


def test_sick_leave_follows_the_same_working_day_rule():
    entries = _leave(dt.date(2026, 7, 11), 2, code="L4")
    s = summarize_month(2026, 7, [_emp()], entries)[1]
    assert s.sick_entries == 2 and s.sick_days == 0


def test_absences_can_be_excluded_from_the_norm():
    rules = Rules(leave_reduces_norm=False)
    entries = _leave(dt.date(2026, 7, 6), 5)
    s = summarize_month(2026, 7, [_emp()], entries, rules)[1]
    assert s.norm_minutes == month_norm(2026, 7).minutes


# --- godziny świąteczne ----------------------------------------------------

def test_holiday_hours_are_counted_separately():
    entries = {
        (1, dt.date(2026, 6, 4)): resolve("D", TYPES),    # Boże Ciało
        (1, dt.date(2026, 6, 7)): resolve("D", TYPES),    # niedziela
        (1, dt.date(2026, 6, 9)): resolve("D", TYPES),    # wtorek
    }
    s = summarize_month(2026, 6, [_emp()], entries)[1]
    assert s.holiday_minutes == 720 and s.holidays_worked == 1
    assert s.sunday_minutes == 720 and s.sundays_worked == 1
    assert s.worked_minutes == 3 * 720


def test_holiday_work_still_leaves_the_norm_reduced():
    """Święto obniża wymiar, więc praca w nim wchodzi w całości na plus."""
    idle = summarize_month(2026, 6, [_emp()], {})[1]
    entries = {(1, dt.date(2026, 6, 4)): resolve("D", TYPES)}   # Boże Ciało
    worked = summarize_month(2026, 6, [_emp()], entries)[1]

    # Wymiar jest ten sam — praca w święto go nie podnosi.
    assert worked.norm_minutes == idle.norm_minutes == month_norm(2026, 6).minutes
    # Cały dyżur poprawia bilans, czyli staje się nadgodzinami.
    assert worked.balance_minutes - idle.balance_minutes == 720


# --- zapis i odczyt --------------------------------------------------------

def test_rules_survive_saving_and_loading(tmp_path):
    db = Database(tmp_path / "t.db")
    rules = Rules(
        daily_norm_minutes=480,
        leave_on_working_days_only=False,
        sick_reduces_norm=False,
    ).with_night_window(dt.time(23, 0))
    save_rules(db, rules)
    assert load_rules(db) == rules
    db.close()


def test_defaults_apply_to_a_fresh_database(tmp_path):
    db = Database(tmp_path / "t.db")
    assert load_rules(db) == Rules()
    db.close()


def test_corrupted_settings_fall_back_to_defaults(tmp_path):
    db = Database(tmp_path / "t.db")
    db.set_setting("daily_norm_minutes", "nonsens")
    db.set_setting("night_start", "25:99")
    rules = load_rules(db)
    assert rules.daily_norm_minutes == Rules().daily_norm_minutes
    assert rules.night_start == Rules().night_start
    db.close()
