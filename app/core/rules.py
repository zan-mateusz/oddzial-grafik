"""Zasady rozliczania czasu pracy — z podstawą prawną i możliwością zmiany.

Kodeks pracy w kilku miejscach zostawia wybór pracodawcy (np. które 8 godzin
jest porą nocną), a część rozwiązań zależy od praktyki oddziału. Dlatego
wszystkie te ustawienia są w jednym miejscu i można je zmienić bez zmiany
programu.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, replace

from app.core.calendar_pl import (
    NORM_MEDICAL_MINUTES, NORM_STANDARD_MINUTES, is_holiday,
)

# Ramy wyznaczone przez art. 151(7) § 1 K.p. — pora nocna to 8 godzin
# mieszczących się między 21:00 a 7:00.
NIGHT_SPAN_START = dt.time(21, 0)
NIGHT_SPAN_END = dt.time(7, 0)
NIGHT_WINDOW_MINUTES = 8 * 60


@dataclass(frozen=True)
class Rules:
    """Komplet zasad, według których liczone są godziny i wymiar."""

    daily_norm_minutes: int = NORM_MEDICAL_MINUTES
    night_start: dt.time = dt.time(22, 0)
    night_end: dt.time = dt.time(6, 0)
    # Urlop przypada na dni, które są dla pracownika dniami pracy — wpis
    # postawiony w sobotę czy niedzielę nie zużywa urlopu.
    leave_on_working_days_only: bool = True
    leave_day_minutes: int | None = None      # None = tyle, co norma dobowa
    leave_reduces_norm: bool = True
    sick_reduces_norm: bool = True

    @property
    def leave_minutes(self) -> int:
        return (
            self.leave_day_minutes
            if self.leave_day_minutes is not None
            else self.daily_norm_minutes
        )

    def is_working_day(self, day: dt.date) -> bool:
        """Dzień, w którym urlop czy zwolnienie zużywa wymiar czasu pracy."""
        if not self.leave_on_working_days_only:
            return True
        return day.weekday() < 5 and not is_holiday(day)

    def with_night_window(self, start: dt.time) -> "Rules":
        """Ustawia porę nocną jako 8 godzin liczonych od podanej godziny."""
        minutes = (start.hour * 60 + start.minute + NIGHT_WINDOW_MINUTES) % (24 * 60)
        end = dt.time(minutes // 60, minutes % 60)
        return replace(self, night_start=start, night_end=end)


def validate_night_window(start: dt.time, end: dt.time) -> str | None:
    """Zwraca opis błędu albo None, gdy okno pory nocnej jest dopuszczalne."""
    a = start.hour * 60 + start.minute
    b = end.hour * 60 + end.minute
    length = (b - a) % (24 * 60)
    if length != NIGHT_WINDOW_MINUTES:
        return (
            "Pora nocna musi obejmować dokładnie 8 godzin "
            "(art. 151⁷ § 1 Kodeksu pracy)."
        )
    span_start = NIGHT_SPAN_START.hour * 60
    # Dopuszczalne początki: od 21:00 do 23:00, aby całe okno zmieściło się
    # w przedziale 21:00-7:00.
    latest_start = span_start + (10 * 60 - NIGHT_WINDOW_MINUTES)
    normalised = a if a >= span_start else a + 24 * 60
    if not (span_start <= normalised <= latest_start):
        return (
            "Pora nocna musi mieścić się między 21:00 a 7:00, więc może "
            "zaczynać się najwcześniej o 21:00 i najpóźniej o 23:00."
        )
    return None


NORM_PRESETS = [
    ("7 godz. 35 min — personel medyczny", NORM_MEDICAL_MINUTES),
    ("8 godz. — norma podstawowa", NORM_STANDARD_MINUTES),
]

# Krótkie objaśnienia pokazywane obok ustawień. Mają pomóc zrozumieć, skąd
# biorą się liczby — nie zastępują porady kadrowej.
LEGAL_NOTES = {
    "daily_norm": (
        "Dobowa norma czasu pracy",
        "Dla pracowników podmiotów leczniczych wynosi 7 godz. 35 min "
        "(art. 93 ust. 1 ustawy o działalności leczniczej). Poza ochroną "
        "zdrowia obowiązuje 8 godzin (art. 129 § 1 Kodeksu pracy).",
    ),
    "month_norm": (
        "Wymiar czasu pracy w miesiącu",
        "Liczba dni od poniedziałku do piątku pomnożona przez normę dobową, "
        "pomniejszona o każde święto przypadające w dniu innym niż niedziela "
        "(art. 130 § 1 i 2 Kodeksu pracy). Święto obniża wymiar także wtedy, "
        "gdy tego dnia ktoś pracuje — wypracowane godziny stają się wówczas "
        "nadgodzinami.",
    ),
    "night": (
        "Pora nocna",
        "Obejmuje 8 godzin mieszczących się między 21:00 a 7:00; konkretne "
        "godziny ustala pracodawca w regulaminie pracy (art. 151⁷ § 1 "
        "Kodeksu pracy). Za każdą godzinę pracy w porze nocnej przysługuje "
        "dodatek (art. 151⁸ § 1).",
    ),
    "leave": (
        "Urlop wypoczynkowy",
        "Urlopu udziela się w dni, które są dla pracownika dniami pracy "
        "(art. 154² § 1 Kodeksu pracy), więc wpis postawiony w sobotę, "
        "niedzielę lub święto nie zużywa urlopu. Dzień urlopu odpowiada "
        "dobowej normie czasu pracy.",
    ),
    "absence": (
        "Urlop i zwolnienie a wymiar",
        "Wymiar czasu pracy obniża się o godziny usprawiedliwionej "
        "nieobecności przypadające do przepracowania w czasie tej "
        "nieobecności (art. 130 § 3 Kodeksu pracy). Dzięki temu urlop ani "
        "zwolnienie nie tworzą sztucznych niedogodzin.",
    ),
    "holiday": (
        "Praca w niedziele i święta",
        "Za pracę w niedzielę lub święto pracownikowi przysługuje inny dzień "
        "wolny, a gdy jest to niemożliwe — dodatek (art. 151¹¹ oraz "
        "151¹⁰ Kodeksu pracy). Program zlicza te godziny osobno, aby "
        "łatwiej było je rozliczyć.",
    ),
}

SETTING_KEYS = {
    "daily_norm_minutes": "daily_norm_minutes",
    "night_start": "night_start",
    "night_end": "night_end",
    "leave_on_working_days_only": "leave_on_working_days_only",
    "leave_day_minutes": "leave_day_minutes",
    "leave_reduces_norm": "leave_reduces_norm",
    "sick_reduces_norm": "sick_reduces_norm",
}


def _parse_time(text: str, fallback: dt.time) -> dt.time:
    try:
        hh, mm = text.split(":")
        return dt.time(int(hh), int(mm))
    except (ValueError, AttributeError):
        return fallback


def load_rules(db) -> Rules:
    """Odczytuje zasady z ustawień; brakujące pola przyjmują wartości domyślne."""
    default = Rules()
    try:
        norm = int(db.get_setting("daily_norm_minutes", str(default.daily_norm_minutes)))
    except ValueError:
        norm = default.daily_norm_minutes
    raw_leave_minutes = db.get_setting("leave_day_minutes", "")
    try:
        leave_minutes = int(raw_leave_minutes) if raw_leave_minutes else None
    except ValueError:
        leave_minutes = None
    return Rules(
        daily_norm_minutes=norm,
        night_start=_parse_time(db.get_setting("night_start", ""), default.night_start),
        night_end=_parse_time(db.get_setting("night_end", ""), default.night_end),
        leave_on_working_days_only=db.get_setting(
            "leave_on_working_days_only", "1"
        ) != "0",
        leave_day_minutes=leave_minutes,
        leave_reduces_norm=db.get_setting("leave_reduces_norm", "1") != "0",
        sick_reduces_norm=db.get_setting("sick_reduces_norm", "1") != "0",
    )


def save_rules(db, rules: Rules) -> None:
    db.set_setting("daily_norm_minutes", str(rules.daily_norm_minutes))
    db.set_setting("night_start", rules.night_start.strftime("%H:%M"))
    db.set_setting("night_end", rules.night_end.strftime("%H:%M"))
    db.set_setting(
        "leave_on_working_days_only", "1" if rules.leave_on_working_days_only else "0"
    )
    db.set_setting(
        "leave_day_minutes",
        "" if rules.leave_day_minutes is None else str(rules.leave_day_minutes),
    )
    db.set_setting("leave_reduces_norm", "1" if rules.leave_reduces_norm else "0")
    db.set_setting("sick_reduces_norm", "1" if rules.sick_reduces_norm else "0")
