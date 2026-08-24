import datetime as dt

import pytest

from app.core.calendar_pl import (
    DayKind, day_kind, easter_sunday, holiday_name, is_holiday, month_norm,
    NORM_MEDICAL_MINUTES, NORM_STANDARD_MINUTES,
)
from app.core.shifts import (
    DEFAULT_SHIFT_TYPES, fmt_duration_label, fmt_minutes, parse_duration,
    parse_freeform, resolve, span_minutes,
)
from app.core.stats import night_minutes, summarize_month

TYPES = {t.code: t for t in DEFAULT_SHIFT_TYPES}


@pytest.mark.parametrize("year,expected", [
    (2024, dt.date(2024, 3, 31)), (2025, dt.date(2025, 4, 20)),
    (2026, dt.date(2026, 4, 5)),  (2027, dt.date(2027, 3, 28)),
])
def test_easter(year, expected):
    assert easter_sunday(year) == expected


def test_movable_holidays_follow_easter():
    assert holiday_name(dt.date(2026, 4, 6)) == "Poniedziałek Wielkanocny"
    assert holiday_name(dt.date(2026, 6, 4)) == "Boże Ciało"


def test_christmas_eve_is_holiday_only_from_2025():
    assert not is_holiday(dt.date(2024, 12, 24))
    assert is_holiday(dt.date(2025, 12, 24))


def test_day_kind_holiday_beats_weekday():
    assert day_kind(dt.date(2026, 8, 15)) is DayKind.HOLIDAY   # sobota
    assert day_kind(dt.date(2026, 8, 16)) is DayKind.SUNDAY
    assert day_kind(dt.date(2026, 8, 17)) is DayKind.WEEKDAY


def test_month_norm_matches_official_figures():
    # Wymiary czasu pracy dla pełnego etatu (8 h) w 2026 r.
    expected = [160, 160, 176, 168, 160, 168, 184, 160, 176, 176, 160, 160]
    got = [month_norm(2026, m, NORM_STANDARD_MINUTES).minutes // 60 for m in range(1, 13)]
    assert got == expected
    assert sum(got) == 2008  # roczny wymiar 2026


def _art130_minutes(year, month, daily=NORM_STANDARD_MINUTES):
    """Niezależna implementacja wzoru z art. 130 § 1-2 K.p.:
    40 h × pełne tygodnie + 8 h × dni wystające, minus święta poza niedzielą."""
    from app.core.calendar_pl import month_days
    days = month_days(year, month)
    full_weeks = len(days) // 7
    leftover = sum(1 for d in days[full_weeks * 7:] if d.weekday() < 5)
    hol = sum(1 for d in days if is_holiday(d) and d.weekday() != 6)
    return (full_weeks * 5 + leftover - hol) * daily


@pytest.mark.parametrize("year", [2025, 2026, 2027, 2028])
def test_month_norm_agrees_with_statutory_formula(year):
    for month in range(1, 13):
        assert month_norm(year, month, NORM_STANDARD_MINUTES).minutes == \
            _art130_minutes(year, month), f"{year}-{month:02d}"


def test_holiday_on_sunday_does_not_reduce_norm():
    # 3 maja 2026 wypada w niedzielę — nie obniża wymiaru.
    assert dt.date(2026, 5, 3).weekday() == 6
    assert month_norm(2026, 5).holidays_reducing == 1  # tylko 1 maja


@pytest.mark.parametrize("text,minutes", [
    ("8-14", 360), ("7:30-19:30", 720), ("0700-1900", 720),
    ("19-7", 720), ("22-6", 480), ("7.30-15.05", 455),
])
def test_freeform_ranges(text, minutes):
    start, end = parse_freeform(text)
    assert span_minutes(start, end) == minutes


@pytest.mark.parametrize("text", ["25-30", "abc", "8..14", "", "8-"])
def test_freeform_rejects_nonsense(text):
    assert parse_freeform(text) is None


@pytest.mark.parametrize("text,minutes", [
    ("8", 480), ("10", 600), ("12", 720),          # same pełne godziny
    ("7:30", 450), ("7.30", 450),                  # zapis zegarowy
    ("7,3", 450), ("7.3", 450),                    # jedna cyfra = dziesiątki minut
    ("7,35", 455), ("6,45", 405),                  # dwie cyfry = minuty
    ("7,5", 470),                                  # 7:50, a nie 7,5 godziny
])
def test_duration_uses_minutes_not_decimal_fractions(text, minutes):
    """W grafiku przecinek oddziela minuty — "7,3" to 7 godz. 30 min."""
    assert parse_duration(text) == minutes


@pytest.mark.parametrize("text", ["25", "7,70", "7,99", "abc", "", "-3"])
def test_duration_rejects_impossible_values(text):
    assert parse_duration(text) is None


@pytest.mark.parametrize("minutes,label", [
    (600, "10"), (720, "12"), (450, "7:30"), (455, "7:35"),
])
def test_duration_label_is_normalised_for_the_grid(minutes, label):
    """Komórka pokazuje odczytaną wartość, żeby było widać, co program zrozumiał."""
    assert fmt_duration_label(minutes) == label


def test_typed_duration_is_displayed_normalised():
    assert resolve("7,3", TYPES).label == "7:30"
    assert resolve("10", TYPES).label == "10"


def test_duration_without_start_time_has_no_night_hours():
    """Sam czas trwania nie mówi, o której zaczyna się dyżur."""
    entry = resolve("10", TYPES)
    assert entry.start is None and entry.end is None


def test_resolve_shift_code_is_case_insensitive():
    assert resolve("n", TYPES).minutes == 720
    assert resolve("N", TYPES).shift_code == "N"


def test_resolve_marks_unknown_entries():
    e = resolve("???", TYPES)
    assert e.unknown and e.minutes == 0


def test_resolve_empty_is_none():
    assert resolve("   ", TYPES) is None


@pytest.mark.parametrize("start,end,expected", [
    ((19, 0), (7, 0), 600), ((7, 0), (19, 0), 0), ((22, 0), (6, 0), 480),
    ((14, 0), (21, 35), 35), ((6, 0), (8, 0), 60),
])
def test_night_minutes(start, end, expected):
    assert night_minutes(dt.time(*start), dt.time(*end)) == expected


def test_fmt_minutes_keeps_sign():
    assert fmt_minutes(455) == "7:35"
    assert fmt_minutes(-90) == "-1:30"


class FakeEmp(dict):
    """Zastępuje sqlite3.Row w testach."""


def _emp(emp_id, num=1, den=1):
    return FakeEmp(id=emp_id, fte_num=num, fte_den=den)


def test_summary_counts_hours_and_balance():
    entries = {}
    # 20 dyżurów dziennych po 12 h w sierpniu 2026.
    for day in range(1, 21):
        entries[(1, dt.date(2026, 8, day))] = resolve("D", TYPES)
    s = summarize_month(2026, 8, [_emp(1)], entries)[1]
    assert s.worked_minutes == 20 * 720
    assert s.shift_days == 20
    assert s.norm_minutes == month_norm(2026, 8).minutes
    assert s.balance_minutes == 20 * 720 - s.norm_minutes


def test_leave_reduces_individual_norm():
    full = summarize_month(2026, 8, [_emp(1)], {})[1]
    entries = {(1, dt.date(2026, 8, d)): resolve("U", TYPES) for d in range(3, 8)}
    with_leave = summarize_month(2026, 8, [_emp(1)], entries)[1]
    assert with_leave.leave_days == 5
    assert with_leave.norm_minutes == full.norm_minutes - 5 * NORM_MEDICAL_MINUTES


def test_part_time_halves_the_norm():
    full = summarize_month(2026, 8, [_emp(1)], {})[1]
    half = summarize_month(2026, 8, [_emp(2, 1, 2)], {})[2]
    assert half.norm_minutes == round(full.norm_minutes / 2)


def test_holiday_and_sunday_shifts_are_counted_separately():
    entries = {
        (1, dt.date(2026, 8, 15)): resolve("D", TYPES),  # święto (sobota)
        (1, dt.date(2026, 8, 16)): resolve("D", TYPES),  # niedziela
        (1, dt.date(2026, 8, 22)): resolve("D", TYPES),  # sobota
    }
    s = summarize_month(2026, 8, [_emp(1)], entries)[1]
    assert (s.holidays_worked, s.sundays_worked, s.saturdays_worked) == (1, 1, 1)


def test_night_shift_hours_land_on_starting_day():
    entries = {(1, dt.date(2026, 8, 31)): resolve("N", TYPES)}
    s = summarize_month(2026, 8, [_emp(1)], entries)[1]
    assert s.worked_minutes == 720
    assert s.night_minutes == 600
