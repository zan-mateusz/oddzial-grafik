"""Polski kalendarz: święta ustawowe i wymiar czasu pracy."""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache

# Dobowa norma czasu pracy personelu medycznego to 7 h 35 min
# (ustawa o działalności leczniczej, art. 93 ust. 1). Poza ochroną zdrowia — 8 h.
NORM_MEDICAL_MINUTES = 7 * 60 + 35
NORM_STANDARD_MINUTES = 8 * 60


def easter_sunday(year: int) -> dt.date:
    """Niedziela Wielkanocna — algorytm Meeusa/Jonesa/Butchera."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    lam = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * lam) // 451
    month, day = divmod(h + lam - 7 * m + 114, 31)
    return dt.date(year, month, day + 1)


@lru_cache(maxsize=64)
def holidays(year: int) -> dict[dt.date, str]:
    """Dni ustawowo wolne od pracy w danym roku.

    Uwaga: na oddziale i tak ktoś tego dnia pracuje — lista służy do oznaczenia
    dni w grafiku oraz do obniżenia wymiaru czasu pracy (art. 130 § 2 K.p.).
    """
    easter = easter_sunday(year)
    days = {
        dt.date(year, 1, 1): "Nowy Rok",
        dt.date(year, 1, 6): "Trzech Króli",
        easter: "Wielkanoc",
        easter + dt.timedelta(days=1): "Poniedziałek Wielkanocny",
        dt.date(year, 5, 1): "Święto Pracy",
        dt.date(year, 5, 3): "Święto Konstytucji 3 Maja",
        easter + dt.timedelta(days=49): "Zesłanie Ducha Świętego",
        easter + dt.timedelta(days=60): "Boże Ciało",
        dt.date(year, 8, 15): "Wniebowzięcie NMP",
        dt.date(year, 11, 1): "Wszystkich Świętych",
        dt.date(year, 11, 11): "Narodowe Święto Niepodległości",
        dt.date(year, 12, 25): "Boże Narodzenie",
        dt.date(year, 12, 26): "Drugi dzień Bożego Narodzenia",
    }
    # Wigilia jest dniem ustawowo wolnym od 2025 r. (Dz.U. 2024 poz. 1774).
    if year >= 2025:
        days[dt.date(year, 12, 24)] = "Wigilia"
    return days


def holiday_name(day: dt.date) -> str | None:
    return holidays(day.year).get(day)


def is_holiday(day: dt.date) -> bool:
    return day in holidays(day.year)


class DayKind(Enum):
    """Rodzaj dnia — używany do kolorowania kolumn w grafiku."""

    WEEKDAY = "powszedni"
    SATURDAY = "sobota"
    SUNDAY = "niedziela"
    HOLIDAY = "święto"


def day_kind(day: dt.date) -> DayKind:
    """Święto ma pierwszeństwo przed dniem tygodnia."""
    if is_holiday(day):
        return DayKind.HOLIDAY
    if day.weekday() == 5:
        return DayKind.SATURDAY
    if day.weekday() == 6:
        return DayKind.SUNDAY
    return DayKind.WEEKDAY


def month_days(year: int, month: int) -> list[dt.date]:
    first = dt.date(year, month, 1)
    nxt = dt.date(year + 1, 1, 1) if month == 12 else dt.date(year, month + 1, 1)
    return [first + dt.timedelta(days=i) for i in range((nxt - first).days)]


@dataclass(frozen=True)
class MonthNorm:
    """Wymiar czasu pracy w miesiącu (norma umowna, nie grafik)."""

    working_days: int
    holidays_reducing: int
    minutes: int

    @property
    def hours(self) -> float:
        return self.minutes / 60.0


def month_norm(
    year: int, month: int, daily_minutes: int = NORM_MEDICAL_MINUTES
) -> MonthNorm:
    """Wymiar czasu pracy zgodnie z art. 130 Kodeksu pracy.

    Liczba dni od poniedziałku do piątku × norma dobowa, pomniejszona o każde
    święto przypadające w dniu innym niż niedziela. Obniżenie obowiązuje nawet
    wtedy, gdy pracownik tego dnia pracuje — wypracowane godziny stają się wtedy
    nadgodzinami albo są odbierane w innym terminie.
    """
    weekdays = 0
    holiday_reducing = 0
    for day in month_days(year, month):
        if day.weekday() < 5:
            weekdays += 1
        if is_holiday(day) and day.weekday() != 6:
            holiday_reducing += 1
    working_days = weekdays - holiday_reducing
    return MonthNorm(
        working_days=working_days,
        holidays_reducing=holiday_reducing,
        minutes=working_days * daily_minutes,
    )


PL_MONTHS = [
    "styczeń", "luty", "marzec", "kwiecień", "maj", "czerwiec",
    "lipiec", "sierpień", "wrzesień", "październik", "listopad", "grudzień",
]
PL_MONTHS_TITLE = [m.capitalize() for m in PL_MONTHS]
PL_WEEKDAYS_SHORT = ["Pn", "Wt", "Śr", "Cz", "Pt", "So", "Nd"]
