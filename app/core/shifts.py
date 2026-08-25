"""Model zmian: typy predefiniowane + wpisy dowolne (np. "8-14")."""
from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass
from enum import Enum


class Category(Enum):
    """Rodzaj wpisu — decyduje o tym, jak liczą się godziny."""

    WORK = "praca"
    LEAVE = "urlop"
    SICK = "zwolnienie"
    ABSENCE = "nieobecność"
    OFF = "wolne"

    @property
    def counts_as_worked(self) -> bool:
        return self is Category.WORK

    @property
    def counts_toward_norm(self) -> bool:
        """Urlop i zwolnienie obniżają wymiar do wypracowania (art. 130 § 3 K.p.)."""
        return self in (Category.LEAVE, Category.SICK)


@dataclass(frozen=True)
class ShiftType:
    """Predefiniowana zmiana, np. D = 7:00-19:00."""

    code: str
    name: str
    start: dt.time | None
    end: dt.time | None
    category: Category = Category.WORK
    color: str = "#E8EDF4"
    minutes_override: int | None = None
    id: int | None = None

    @property
    def minutes(self) -> int:
        if self.minutes_override is not None:
            return self.minutes_override
        if self.start is None or self.end is None:
            return 0
        return span_minutes(self.start, self.end)

    @property
    def crosses_midnight(self) -> bool:
        return (
            self.start is not None
            and self.end is not None
            and self.end <= self.start
        )


def span_minutes(start: dt.time, end: dt.time) -> int:
    """Długość zmiany w minutach; zmiana kończąca się o/przed godziną startu
    traktowana jest jako nocna i przechodzi przez północ."""
    a = start.hour * 60 + start.minute
    b = end.hour * 60 + end.minute
    if b <= a:
        b += 24 * 60
    return b - a


def fmt_minutes(minutes: int) -> str:
    """480 -> '8:00'. Ujemne wartości zachowują znak: -90 -> '-1:30'."""
    sign = "-" if minutes < 0 else ""
    minutes = abs(minutes)
    return f"{sign}{minutes // 60}:{minutes % 60:02d}"


def fmt_days_hours(days: int, minutes: int) -> str:
    """Zestawienie liczby dni i godzin w jednej komórce: 14 (168:00).

    Puste, gdy nic nie ma — pusta kolumna czyta się lepiej niż rząd zer.
    """
    if not days and not minutes:
        return ""
    return f"{days} ({fmt_minutes(minutes)})"


def fmt_hours_decimal(minutes: int) -> str:
    return f"{minutes / 60:.2f}".replace(".", ",")


# --- Parsowanie wpisów dowolnych -------------------------------------------

_TIME = r"(\d{1,2})(?:[:.](\d{2}))?"
_RANGE_RE = re.compile(rf"^\s*{_TIME}\s*[-–—]\s*{_TIME}\s*$")
_COMPACT_RE = re.compile(r"^\s*(\d{3,4})\s*[-–—]\s*(\d{3,4})\s*$")
_DURATION_RE = re.compile(r"^\s*(\d{1,2})(?:\s*[:.,]\s*(\d{1,2}))?\s*[hH]?\s*$")


def _mk_time(hour: int, minute: int) -> dt.time | None:
    if hour == 24 and minute == 0:
        hour = 0
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return None
    return dt.time(hour, minute)


def parse_freeform(text: str) -> tuple[dt.time, dt.time] | None:
    """"8-14", "7:30-19:30", "0700-1900" -> (start, koniec). Inaczej None."""
    m = _COMPACT_RE.match(text)
    if m:
        a, b = m.group(1), m.group(2)
        start = _mk_time(int(a[:-2]), int(a[-2:]))
        end = _mk_time(int(b[:-2]), int(b[-2:]))
        if start and end:
            return start, end
        return None
    m = _RANGE_RE.match(text)
    if m:
        start = _mk_time(int(m.group(1)), int(m.group(2) or 0))
        end = _mk_time(int(m.group(3)), int(m.group(4) or 0))
        if start and end:
            return start, end
    return None


def parse_duration(text: str) -> int | None:
    """Zamienia zapis czasu trwania dyżuru na minuty.

    Przecinek, kropka i dwukropek oddzielają minuty, a nie ułamek godziny —
    tak zapisuje się czas w grafiku prowadzonym ręcznie:

        "10"    -> 10:00    (same pełne godziny)
        "7:30"  ->  7:30
        "7,3"   ->  7:30    (jedna cyfra to dziesiątki minut)
        "7,35"  ->  7:35    (dwie cyfry to minuty)
    """
    m = _DURATION_RE.match(text)
    if not m:
        return None
    hours = int(m.group(1))
    digits = m.group(2)
    if digits is None:
        minutes = 0
    elif len(digits) == 1:
        minutes = int(digits) * 10
    else:
        minutes = int(digits)
    if hours > 24 or minutes > 59 or (hours == 24 and minutes):
        return None
    return hours * 60 + minutes


def fmt_duration_label(minutes: int) -> str:
    """Etykieta w komórce: pełne godziny bez końcówki ("10"), reszta jako "7:30"."""
    return str(minutes // 60) if minutes % 60 == 0 else fmt_minutes(minutes)


@dataclass(frozen=True)
class Entry:
    """Rozwiązany wpis w komórce grafiku."""

    raw: str
    minutes: int
    category: Category
    label: str
    color: str
    start: dt.time | None = None
    end: dt.time | None = None
    shift_code: str | None = None
    unknown: bool = False

    @property
    def crosses_midnight(self) -> bool:
        return self.start is not None and self.end is not None and self.end <= self.start


FREEFORM_COLOR = "#FFF3D6"
UNKNOWN_COLOR = "#FFD6D6"


def resolve(raw: str, types_by_code: dict[str, ShiftType]) -> Entry | None:
    """Zamienia zawartość komórki na wpis. Pusty tekst -> None.

    Kolejność: kod zmiany (bez rozróżniania wielkości liter) -> zakres godzin
    -> sama liczba godzin -> wpis nierozpoznany (oznaczony na czerwono).
    """
    text = (raw or "").strip()
    if not text:
        return None

    st = types_by_code.get(text.upper())
    if st is not None:
        return Entry(
            raw=text,
            minutes=st.minutes,
            category=st.category,
            label=st.code,
            color=st.color,
            start=st.start,
            end=st.end,
            shift_code=st.code,
        )

    span = parse_freeform(text)
    if span is not None:
        start, end = span
        return Entry(
            raw=text,
            minutes=span_minutes(start, end),
            category=Category.WORK,
            label=f"{start.strftime('%-H:%M') if start.minute else str(start.hour)}"
            f"-{end.strftime('%-H:%M') if end.minute else str(end.hour)}",
            color=FREEFORM_COLOR,
            start=start,
            end=end,
        )

    duration = parse_duration(text)
    if duration is not None:
        # Sam czas trwania, bez pory rozpoczęcia — nie wlicza się do pory nocnej.
        return Entry(
            raw=text,
            minutes=duration,
            category=Category.WORK,
            label=fmt_duration_label(duration),
            color=FREEFORM_COLOR,
        )

    return Entry(
        raw=text,
        minutes=0,
        category=Category.ABSENCE,
        label=text,
        color=UNKNOWN_COLOR,
        unknown=True,
    )


DEFAULT_SHIFT_TYPES: tuple[ShiftType, ...] = (
    ShiftType("D", "Dyżur dzienny", dt.time(7, 0), dt.time(19, 0), Category.WORK, "#D6E8FF"),
    ShiftType("N", "Dyżur nocny", dt.time(19, 0), dt.time(7, 0), Category.WORK, "#D8D4F0"),
    ShiftType("U", "Urlop wypoczynkowy", None, None, Category.LEAVE, "#FFF2A8"),
    ShiftType("UŻ", "Urlop na żądanie", None, None, Category.LEAVE, "#FFF2A8"),
    ShiftType("L4", "Zwolnienie lekarskie", None, None, Category.SICK, "#FFD9E6"),
    ShiftType("OP", "Opieka nad dzieckiem", None, None, Category.LEAVE, "#FFE7C2"),
    ShiftType("W", "Wolne", None, None, Category.OFF, "#F0F1F3"),
)
