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


def fmt_hours_decimal(minutes: int) -> str:
    return f"{minutes / 60:.2f}".replace(".", ",")


# --- Parsowanie wpisów dowolnych -------------------------------------------

_TIME = r"(\d{1,2})(?:[:.](\d{2}))?"
_RANGE_RE = re.compile(rf"^\s*{_TIME}\s*[-–—]\s*{_TIME}\s*$")
_COMPACT_RE = re.compile(r"^\s*(\d{3,4})\s*[-–—]\s*(\d{3,4})\s*$")
_BARE_RE = re.compile(r"^\s*(\d{1,2})(?:[:.,](\d{1,2}))?\s*[hH]?\s*$")


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


def parse_bare_hours(text: str) -> int | None:
    """"8" -> 480 min, "7,5" / "7:30" -> 450 min. Bez godziny rozpoczęcia."""
    m = _BARE_RE.match(text)
    if not m:
        return None
    hours = int(m.group(1))
    frac = m.group(2)
    if frac is None:
        minutes = 0
    elif ":" in text or "." in text and len(frac) == 2 and int(frac) < 60:
        minutes = int(frac)
    else:
        minutes = round(float(f"0.{frac}") * 60)
    if hours > 24:
        return None
    return hours * 60 + minutes


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

    bare = parse_bare_hours(text)
    if bare is not None:
        return Entry(
            raw=text,
            minutes=bare,
            category=Category.WORK,
            label=text,
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
    ShiftType("D", "Dniówka", dt.time(7, 0), dt.time(19, 0), Category.WORK, "#D6E8FF"),
    ShiftType("N", "Nocka", dt.time(19, 0), dt.time(7, 0), Category.WORK, "#D8D4F0"),
    ShiftType("R", "Rano", dt.time(7, 0), dt.time(14, 35), Category.WORK, "#DFF3E4"),
    ShiftType("P", "Popołudnie", dt.time(14, 0), dt.time(21, 35), Category.WORK, "#FCE4D6"),
    ShiftType("U", "Urlop wypoczynkowy", None, None, Category.LEAVE, "#FFF2A8"),
    ShiftType("UŻ", "Urlop na żądanie", None, None, Category.LEAVE, "#FFF2A8"),
    ShiftType("UB", "Urlop bezpłatny", None, None, Category.ABSENCE, "#EFEFEF"),
    ShiftType("L4", "Zwolnienie lekarskie", None, None, Category.SICK, "#FFD9E6"),
    ShiftType("OP", "Opieka nad dzieckiem", None, None, Category.LEAVE, "#FFF2A8"),
    ShiftType("W", "Wolne", None, None, Category.OFF, "#F5F5F5"),
    ShiftType("WN", "Wolne za nadgodziny", None, None, Category.OFF, "#F5F5F5"),
    ShiftType("SZ", "Szkolenie", None, None, Category.WORK, "#E0E0FF", minutes_override=455),
)
