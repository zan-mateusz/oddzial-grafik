"""Podsumowania miesięczne: godziny, dyżury, nadgodziny."""
from __future__ import annotations

import datetime as dt
from collections import Counter
from dataclasses import dataclass, field

from app.core.calendar_pl import (
    NORM_MEDICAL_MINUTES,
    is_holiday,
    month_days,
    month_norm,
)
from app.core.shifts import Category, Entry, fmt_minutes

# Pora nocna: 8 godzin pomiędzy 21:00 a 7:00 (art. 151(7) § 1 K.p.).
NIGHT_START = dt.time(21, 0)
NIGHT_END = dt.time(7, 0)


def _to_min(t: dt.time) -> int:
    return t.hour * 60 + t.minute


def night_minutes(start: dt.time | None, end: dt.time | None) -> int:
    """Ile minut zmiany przypada na porę nocną (21:00-7:00)."""
    if start is None or end is None:
        return 0
    a = _to_min(start)
    b = _to_min(end)
    if b <= a:
        b += 24 * 60
    total = 0
    # Okna pory nocnej powtarzane co dobę, żeby objąć zmiany przez północ.
    for offset in (-24 * 60, 0, 24 * 60):
        ns = _to_min(NIGHT_START) + offset
        ne = _to_min(NIGHT_END) + 24 * 60 + offset
        total += max(0, min(b, ne) - max(a, ns))
    return total


@dataclass
class EmployeeSummary:
    employee_id: int
    worked_minutes: int = 0
    night_minutes: int = 0
    shift_days: int = 0
    leave_days: int = 0
    sick_days: int = 0
    absence_days: int = 0
    off_days: int = 0
    sundays_worked: int = 0
    holidays_worked: int = 0
    saturdays_worked: int = 0
    unknown_entries: int = 0
    by_code: Counter[str] = field(default_factory=Counter)
    norm_minutes: int = 0

    @property
    def balance_minutes(self) -> int:
        """Nadgodziny (+) lub niedogodziny (-) względem wymiaru."""
        return self.worked_minutes - self.norm_minutes

    @property
    def worked_hhmm(self) -> str:
        return fmt_minutes(self.worked_minutes)

    @property
    def norm_hhmm(self) -> str:
        return fmt_minutes(self.norm_minutes)

    @property
    def balance_hhmm(self) -> str:
        m = self.balance_minutes
        return ("+" if m > 0 else "") + fmt_minutes(m)


def summarize_month(
    year: int,
    month: int,
    employees: list,
    entries: dict[tuple[int, dt.date], Entry],
    daily_norm_minutes: int = NORM_MEDICAL_MINUTES,
) -> dict[int, EmployeeSummary]:
    """Liczy podsumowanie dla każdego pracownika.

    Zmiana nocna liczona jest w całości do dnia, w którym się zaczyna — tak jak
    w arkuszu, gdzie wpis "N" stoi w kolumnie dnia rozpoczęcia dyżuru.
    """
    base = month_norm(year, month, daily_norm_minutes)
    days = month_days(year, month)
    summaries: dict[int, EmployeeSummary] = {}

    for emp in employees:
        emp_id = emp["id"] if not isinstance(emp, int) else emp
        s = EmployeeSummary(employee_id=emp_id)
        for day in days:
            entry = entries.get((emp_id, day))
            if entry is None:
                continue
            if entry.unknown:
                s.unknown_entries += 1
            cat = entry.category
            if cat is Category.WORK:
                s.worked_minutes += entry.minutes
                s.night_minutes += night_minutes(entry.start, entry.end)
                if entry.minutes > 0:
                    s.shift_days += 1
                    if is_holiday(day):
                        s.holidays_worked += 1
                    elif day.weekday() == 6:
                        s.sundays_worked += 1
                    elif day.weekday() == 5:
                        s.saturdays_worked += 1
            elif cat is Category.LEAVE:
                s.leave_days += 1
            elif cat is Category.SICK:
                s.sick_days += 1
            elif cat is Category.ABSENCE:
                s.absence_days += 1
            elif cat is Category.OFF:
                s.off_days += 1
            if entry.shift_code:
                s.by_code[entry.shift_code] += 1

        fte = _fte(emp)
        # Wymiar indywidualny: norma miesiąca × etat, obniżona o dni urlopu
        # i zwolnienia (art. 130 § 3 K.p.).
        excused = s.leave_days + s.sick_days
        norm = round(base.minutes * fte) - round(excused * daily_norm_minutes * fte)
        s.norm_minutes = max(0, norm)
        summaries[emp_id] = s

    return summaries


def _fte(emp) -> float:
    if isinstance(emp, int):
        return 1.0
    try:
        num = emp["fte_num"]
        den = emp["fte_den"] or 1
        return num / den
    except (KeyError, IndexError, TypeError):
        return 1.0


def daily_coverage(
    days: list[dt.date],
    employees: list,
    entries: dict[tuple[int, dt.date], Entry],
) -> dict[dt.date, Counter[str]]:
    """Obsada każdego dnia wg kodu zmiany — do wiersza sumy pod grafikiem."""
    out: dict[dt.date, Counter[str]] = {d: Counter() for d in days}
    for emp in employees:
        emp_id = emp["id"] if not isinstance(emp, int) else emp
        for day in days:
            e = entries.get((emp_id, day))
            if e is None or e.category is not Category.WORK or e.minutes <= 0:
                continue
            out[day][e.shift_code or "inne"] += 1
    return out
