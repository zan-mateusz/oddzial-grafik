"""Model tabeli grafiku dla QTableView."""
from __future__ import annotations

import datetime as dt

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont

from app.core.calendar_pl import (
    DayKind, PL_MONTHS, PL_QUARTER_NAMES, PL_WEEKDAYS_SHORT, day_kind,
    holiday_name, month_days, quarter_months, quarter_of,
)
from app.core.rules import load_rules
from app.core.shifts import (
    Category, fmt_days_hours, fmt_minutes, fmt_signed, resolve,
)
from app.core.stats import summarize_month

# Tło kolumn zależne od rodzaju dnia — święta wyraźnie odróżnione od weekendu.
DAY_TINT = {
    DayKind.WEEKDAY: QColor("#FFFFFF"),
    DayKind.SATURDAY: QColor("#EDF3FA"),
    DayKind.SUNDAY: QColor("#E4EDF8"),
    DayKind.HOLIDAY: QColor("#FBE7EC"),
}
HEADER_TINT = {
    DayKind.WEEKDAY: QColor("#F3F4F6"),
    DayKind.SATURDAY: QColor("#DCE7F5"),
    DayKind.SUNDAY: QColor("#C9DCF1"),
    DayKind.HOLIDAY: QColor("#F6CFD8"),
}
HEADER_TEXT = {
    DayKind.WEEKDAY: QColor("#374151"),
    DayKind.SATURDAY: QColor("#1E4B7A"),
    DayKind.SUNDAY: QColor("#12385E"),
    DayKind.HOLIDAY: QColor("#8C1D32"),
}

# Dyżur odbywany na innym piętrze — widoczny, ale wyszarzony, żeby nie dało się
# przypadkiem zaplanować komuś drugiego dyżuru tego samego dnia.
ELSEWHERE_BG = QColor("#EDEDED")
ELSEWHERE_FG = QColor("#8A9099")

# Kolory bilansu: brak godzin na czerwono, nadgodziny na zielono, wyrównanie
# na czarno. Czerwień ma zwracać uwagę tylko wtedy, gdy czegoś brakuje.
BALANCE_SHORT = QColor("#B00020")
BALANCE_OVER = QColor("#15803D")
BALANCE_EVEN = QColor("#1F2328")


def balance_colour(minutes: int) -> QColor:
    """Kolor liczby bilansu — ujemny czerwony, dodatni zielony, zero czarne."""
    if minutes < 0:
        return BALANCE_SHORT
    if minutes > 0:
        return BALANCE_OVER
    return BALANCE_EVEN

# Kolumny podsumowania. Każda ma klucz, nagłówek i objaśnienie; zestaw zależy
# od tego, co faktycznie jest w miesiącu — kolumny bez treści tylko zaśmiecają.
COL_NORM = ("wymiar", "Wymiar", "Obowiązujący wymiar czasu pracy w miesiącu "
            "(etat, święta, urlopy)")
COL_ALL = ("dyzury", "Dyżury", "Dyżury w miesiącu — liczba dni i łączny czas")
COL_BALANCE = ("bilans", "Bilans", "Nadgodziny (+) albo niedogodziny (−) "
               "w tym miesiącu")
COL_QUARTER = ("kwartal", "Kwartał", "Bilans narastająco od początku kwartału "
               "— nadgodziny rozliczają się w okresie kwartalnym")


def floor_column(floor) -> tuple[str, str, str]:
    """Kolumna z dyżurami na konkretnym piętrze."""
    return (
        f"pietro_{floor['id']}",
        floor["name"],
        f"Dyżury na piętrze {floor['name']} — liczba dni i łączny czas",
    )
COL_DAY = ("dzien", "Dzień", "Dyżury dzienne — liczba dni i łączny czas")
COL_NIGHT = ("noc", "Noc", "Dyżury nocne, czyli sięgające pory nocnej — "
             "liczba dni i łączny czas")
COL_HOLIDAY = ("swieta", "Święta", "Dyżury w święta ustawowo wolne od pracy")
COL_LEAVE = ("urlop", "Urlop", "Zużyty urlop — liczba dni i odpowiadający "
             "im czas pracy")
COL_SICK = ("l4", "L4", "Zwolnienie lekarskie — liczba dni i odpowiadający "
            "im czas pracy")

class RotaModel(QAbstractTableModel):
    """Wiersz = pracownik, kolumna = dzień miesiąca, potem podsumowanie."""

    entryChanged = Signal()

    def __init__(self, db, year: int, month: int, floor_id: int | None = None, parent=None):
        super().__init__(parent)
        self.db = db
        self.year = year
        self.month = month
        self.floor_id = floor_id
        self.rules = load_rules(db)
        self.days: list[dt.date] = []
        self.employees: list = []
        self.summary_columns: list[tuple[str, str, str]] = []
        self._raw: dict[tuple[int, dt.date], str] = {}
        self._entries: dict = {}
        self._elsewhere: dict = {}
        self._summaries: dict = {}
        self._floor_summaries: dict = {}
        self._has_sick_anywhere = False
        self.hide_without_shifts = False
        self.hidden_count = 0
        self.quarter_balance: dict[int, int] = {}
        self.quarter_months: list[tuple[int, int]] = []
        self._types: dict = {}
        self.reload()

    # --- ładowanie ----------------------------------------------------------

    def set_month(self, year: int, month: int) -> None:
        self.beginResetModel()
        self.year, self.month = year, month
        self._load()
        self.endResetModel()

    def set_hide_without_shifts(self, hide: bool) -> None:
        if hide == self.hide_without_shifts:
            return
        self.beginResetModel()
        self.hide_without_shifts = hide
        self._load()
        self.endResetModel()

    def set_floor(self, floor_id: int | None) -> None:
        self.beginResetModel()
        self.floor_id = floor_id
        self._load()
        self.endResetModel()

    def reload(self) -> None:
        self.beginResetModel()
        self._load()
        self.endResetModel()

    def _load(self) -> None:
        self.rules = load_rules(self.db)
        self.days = month_days(self.year, self.month)
        self._types = self.db.shift_types_by_code()

        floors = self.db.floors()
        # Skład zależy od oglądanego piętra: pokazujemy osoby, które mają na
        # nim dyżur albo zostały do niego dopisane. Widok łączny zbiera
        # wszystkich z całego miesiąca.
        self.employees = self.db.employees_on_floor(
            self.year, self.month, self.floor_id
        )
        # Osoby dopisane do składu, którym nie przydzielono jeszcze dyżuru,
        # można ukryć — przy dużym zespole puste wiersze przeszkadzają.
        self.hidden_count = 0
        if self.hide_without_shifts:
            counts = self.db.shift_counts_on_floor(
                self.year, self.month, self.floor_id
            )
            with_shifts = [e for e in self.employees if counts.get(e["id"])]
            self.hidden_count = len(self.employees) - len(with_shifts)
            self.employees = with_shifts
        # Komórki pokazują dyżury tego piętra; sumy liczą cały miesiąc.
        all_raw = self.db.month_entries(self.year, self.month)
        self._raw = (
            all_raw if self.floor_id is None
            else self.db.month_entries(self.year, self.month, self.floor_id)
        )
        entry_floors = self.db.month_entry_floors(self.year, self.month)
        self._entry_floors = entry_floors

        self._entries = {}
        for key, raw in self._raw.items():
            entry = resolve(raw, self._types)
            if entry is not None:
                self._entries[key] = entry

        all_entries = {}
        self._elsewhere = {}
        for key, raw in all_raw.items():
            entry = resolve(raw, self._types)
            if entry is None:
                continue
            all_entries[key] = entry
            if key not in self._raw:
                self._elsewhere[key] = (entry, entry_floors.get(key))

        # Kolumna ze zwolnieniami zależy od całego miesiąca, nie od oglądanego
        # piętra — inaczej pojawiałaby się i znikała przy przełączaniu.
        self._has_sick_anywhere = any(
            e.category is Category.SICK for e in all_entries.values()
        )

        # Dyżury liczone osobno dla każdego piętra. Nie ma pojęcia piętra
        # macierzystego — zespół rotuje, więc liczy się tylko to, gdzie dyżur
        # faktycznie się odbył.
        self._floor_summaries = {}
        for floor in floors:
            per_floor = {
                key: entry for key, entry in all_entries.items()
                if entry_floors.get(key) == floor["id"]
            }
            self._floor_summaries[floor["id"]] = summarize_month(
                self.year, self.month, self.employees, per_floor, self.rules
            )

        self._summaries = summarize_month(
            self.year, self.month, self.employees, all_entries, self.rules
        )
        self._load_quarter()
        self.summary_columns = self._build_columns()

    def _load_quarter(self) -> None:
        """Bilans narastająco w obrębie kwartału.

        Liczone są miesiące kwartału, które mają już ułożony grafik, oraz
        zawsze ten oglądany. Pusty miesiąc z przyszłości pominięto celowo —
        inaczej jego pełny wymiar zaniżałby bilans o kilkadziesiąt godzin.
        """
        self.quarter_balance: dict[int, int] = {}
        self.quarter_months: list[tuple[int, int]] = []
        # Rozbicie na miesiące — żeby dało się sprawdzić, skąd bierze się suma.
        self.quarter_detail: dict[int, list[tuple[int, int, int]]] = {}

        for year, month in quarter_months(self.year, self.month):
            current = (year, month) == (self.year, self.month)
            raw = self.db.month_entries(year, month)
            if not raw and not current:
                continue
            if current:
                summaries = self._summaries
            else:
                entries = {}
                for key, text in raw.items():
                    entry = resolve(text, self._types)
                    if entry is not None:
                        entries[key] = entry
                summaries = summarize_month(
                    year, month,
                    self.db.employees_for_month(year, month),
                    entries, self.rules,
                )
            self.quarter_months.append((year, month))
            for emp_id, summary in summaries.items():
                self.quarter_balance[emp_id] = (
                    self.quarter_balance.get(emp_id, 0) + summary.balance_minutes
                )
                self.quarter_detail.setdefault(emp_id, []).append(
                    (year, month, summary.balance_minutes)
                )

    def _build_columns(self) -> list[tuple[str, str, str]]:
        """Kolumny zależne od zawartości miesiąca."""
        has_sick = self._has_sick_anywhere
        floors = self.db.floors()

        columns = [COL_NORM]
        if len(floors) > 1:
            columns += [floor_column(f) for f in floors]
        else:
            columns.append(COL_ALL)
        columns += [COL_BALANCE, COL_QUARTER, COL_DAY, COL_NIGHT,
                    COL_HOLIDAY, COL_LEAVE]
        if has_sick:
            columns.append(COL_SICK)
        return columns

    # --- wymiary ------------------------------------------------------------

    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self.employees)

    def columnCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self.days) + len(self.summary_columns)

    @property
    def combined(self) -> bool:
        """Widok łączny — wszystkie piętra naraz, tylko do oglądania."""
        return self.floor_id is None

    def is_summary_column(self, col: int) -> bool:
        return col >= len(self.days)

    def date_for_column(self, col: int) -> dt.date | None:
        return self.days[col] if 0 <= col < len(self.days) else None

    def employee_at(self, row: int):
        return self.employees[row] if 0 <= row < len(self.employees) else None

    def summary_for_row(self, row: int):
        emp = self.employee_at(row)
        return self._summaries.get(emp["id"]) if emp is not None else None

    # --- dane ---------------------------------------------------------------

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        row, col = index.row(), index.column()
        emp = self.employee_at(row)
        if emp is None:
            return None

        if self.is_summary_column(col):
            return self._summary_data(row, col - len(self.days), role)

        day = self.days[col]
        key = (emp["id"], day)
        entry = self._entries.get(key)
        other = self._elsewhere.get(key)
        kind = day_kind(day)

        if role == Qt.ItemDataRole.EditRole:
            return self._raw.get(key, "")

        if role == Qt.ItemDataRole.DisplayRole:
            if entry is not None:
                return entry.label
            return other[0].label if other else ""

        if role == Qt.ItemDataRole.BackgroundRole:
            if entry is not None:
                return QBrush(QColor(entry.color))
            if other is not None:
                return QBrush(ELSEWHERE_BG)
            return QBrush(DAY_TINT[kind])

        if role == Qt.ItemDataRole.ForegroundRole:
            if entry is not None and entry.unknown:
                return QBrush(QColor("#B00020"))
            if entry is None and other is not None:
                return QBrush(ELSEWHERE_FG)
            return None

        if role == Qt.ItemDataRole.TextAlignmentRole:
            return int(Qt.AlignmentFlag.AlignCenter)

        if role == Qt.ItemDataRole.FontRole:
            f = QFont()
            label = entry.label if entry else (other[0].label if other else "")
            f.setPointSize(10 if len(label) <= 3 else (8 if len(label) <= 5 else 7))
            if entry is not None and entry.category is Category.WORK:
                f.setBold(True)
            if entry is None and other is not None:
                f.setItalic(True)
            return f

        if role == Qt.ItemDataRole.ToolTipRole:
            return self._cell_tooltip(emp, day, entry, other)

        return None

    def _cell_tooltip(self, emp, day: dt.date, entry, other) -> str:
        parts = [
            f"{self._emp_name(emp)} — {day.strftime('%d.%m.%Y')} "
            f"({PL_WEEKDAYS_SHORT[day.weekday()]})"
        ]
        hol = holiday_name(day)
        if hol:
            parts.append(f"Święto: {hol}")
        if entry is not None and self.combined:
            where = self.db.floor_name(self._entry_floors.get((emp["id"], day)))
            if where:
                parts.append(f"Piętro: {where}")
        if entry is not None:
            st = self._types.get(entry.label.upper())
            if st is not None and st.name:
                parts.append(f"{st.code} — {st.name}")
            if entry.minutes:
                parts.append(f"Czas pracy: {fmt_minutes(entry.minutes)}")
            if entry.unknown:
                parts.append("⚠ Nierozpoznany wpis — sprawdź pisownię kodu")
        elif other is not None:
            shift, floor_id = other
            where = self.db.floor_name(floor_id) or "inne piętro"
            parts.append(f"Dyżur na innym piętrze: {where} ({shift.label})")
            parts.append("Wpisanie tu dyżuru przeniesie go na to piętro.")
        return "\n".join(parts)

    def _summary_values(self, emp_id: int) -> dict[str, str]:
        """Treść komórek podsumowania. Poza wymiarem i bilansami wszystko
        podawane jest jako „dni (godziny)"."""
        month = self._summaries.get(emp_id)
        if month is None:
            return {}
        values = {
            "wymiar": month.norm_hhmm,
            "dyzury": fmt_days_hours(month.shift_days, month.worked_minutes),
            "bilans": month.balance_hhmm,
            "kwartal": fmt_signed(self.quarter_balance.get(emp_id, 0)),
            "dzien": fmt_days_hours(month.day_shifts, month.day_minutes),
            "noc": fmt_days_hours(month.night_shifts, month.night_shift_minutes),
            "swieta": fmt_days_hours(month.holidays_worked, month.holiday_minutes),
            "urlop": fmt_days_hours(month.leave_days, month.leave_minutes),
            "l4": fmt_days_hours(month.sick_days, month.sick_minutes),
        }
        for floor_id, summaries in self._floor_summaries.items():
            summary = summaries.get(emp_id)
            values[f"pietro_{floor_id}"] = (
                fmt_days_hours(summary.shift_days, summary.worked_minutes)
                if summary else ""
            )
        return values

    def _summary_data(self, row: int, idx: int, role: int):
        emp = self.employee_at(row)
        if emp is None or not (0 <= idx < len(self.summary_columns)):
            return None
        key, _, tooltip = self.summary_columns[idx]
        month = self._summaries.get(emp["id"])
        if month is None:
            return None

        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            return self._summary_values(emp["id"]).get(key, "")

        if role == Qt.ItemDataRole.TextAlignmentRole:
            return int(Qt.AlignmentFlag.AlignCenter)

        if role == Qt.ItemDataRole.BackgroundRole:
            # Wymiar i bilanse to podsumowanie umowne — inne tło niż dyżury.
            shade = ("#EFF3F8" if key in ("wymiar", "bilans", "kwartal")
                     else "#F7F8FA")
            return QBrush(QColor(shade))

        if role == Qt.ItemDataRole.FontRole:
            f = QFont()
            f.setPointSize(9)
            f.setBold(key in ("bilans", "kwartal"))
            return f

        if role == Qt.ItemDataRole.ForegroundRole:
            if key == "bilans":
                return QBrush(balance_colour(month.balance_minutes))
            if key == "kwartal":
                return QBrush(balance_colour(self.quarter_balance.get(emp["id"], 0)))
            return None

        if role == Qt.ItemDataRole.ToolTipRole:
            return self._summary_tooltip(key, tooltip, month)
        return None

    def _summary_tooltip(self, key: str, base: str, month) -> str:
        extra: list[str] = []
        if key == "kwartal":
            extra.extend(self._quarter_breakdown(month.employee_id))
        elif key == "noc":
            window = (f"{self.rules.night_start.strftime('%H:%M')}–"
                      f"{self.rules.night_end.strftime('%H:%M')}")
            extra.append(f"Przyjęta pora nocna: {window}")
            extra.append(
                f"Godziny przypadające na porę nocną: "
                f"{fmt_minutes(month.night_minutes)}"
            )
        elif key == "swieta" and month.sunday_minutes:
            extra.append(
                f"W niedziele: {fmt_minutes(month.sunday_minutes)} "
                f"({month.sundays_worked} dyż.)"
            )
        elif key == "urlop" and month.leave_ignored:
            extra.append(
                f"Pominięto wpisów w dni wolne: {month.leave_ignored} — "
                "urlopu udziela się tylko w dni pracy"
            )
        elif key == "bilans":
            extra.append(f"Wypracowane godziny: {month.worked_hhmm}")
            extra.append(f"Wymiar: {month.norm_hhmm}")
        return base + ("\n\n" + "\n".join(extra) if extra else "")

    def _quarter_breakdown(self, emp_id: int) -> list[str]:
        """Miesiąc po miesiącu — z czego składa się bilans kwartalny."""
        quarter = quarter_of(self.month)
        lines = [f"{PL_QUARTER_NAMES[quarter - 1]} {self.year}:"]
        detail = self.quarter_detail.get(emp_id, [])
        for year, month, minutes in detail:
            lines.append(f"   {PL_MONTHS[month - 1]}: {fmt_signed(minutes)}")

        counted = {(y, m) for y, m, _ in detail}
        missing = [
            m for y, m in quarter_months(self.year, self.month)
            if (y, m) not in counted
        ]
        if missing:
            names = ", ".join(PL_MONTHS[m - 1] for m in missing)
            lines.append("")
            lines.append(f"Nie liczone (brak grafiku): {names}")
        return lines

    def setData(self, index: QModelIndex, value, role=Qt.ItemDataRole.EditRole) -> bool:
        if role != Qt.ItemDataRole.EditRole or not index.isValid():
            return False
        if self.is_summary_column(index.column()) or self.combined:
            return False
        emp = self.employee_at(index.row())
        day = self.days[index.column()]
        raw = (str(value) or "").strip()
        key = (emp["id"], day)
        if self._raw.get(key, "") == raw and key not in self._elsewhere:
            return False
        self.db.set_entry(emp["id"], day, raw, self.floor_id)
        self._reload_keep_selection()
        self.entryChanged.emit()
        return True

    def _reload_keep_selection(self) -> None:
        self.beginResetModel()
        self._load()
        self.endResetModel()

    def set_range(self, cells: list[tuple[int, int]], raw: str) -> None:
        """Wypełnia wiele komórek naraz (zaznaczenie + wybór zmiany)."""
        if self.combined:
            return
        items = []
        for row, col in cells:
            if self.is_summary_column(col):
                continue
            emp = self.employee_at(row)
            if emp is None:
                continue
            items.append((emp["id"], self.days[col], raw, self.floor_id))
        if not items:
            return
        self.db.set_entries_bulk(items)
        self._reload_keep_selection()
        self.entryChanged.emit()

    def flags(self, index: QModelIndex):
        base = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        # W widoku łącznym nie wiadomo, na które piętro zapisać dyżur, więc
        # edycja jest wyłączona — od wpisywania są grafiki poszczególnych pięter.
        if (index.isValid() and not self.is_summary_column(index.column())
                and not self.combined):
            return base | Qt.ItemFlag.ItemIsEditable
        return base

    # --- nagłówki -----------------------------------------------------------

    @staticmethod
    def _emp_name(emp) -> str:
        name = f"{emp['last_name']} {emp['first_name']}".strip()
        if emp["fte_num"] != emp["fte_den"]:
            name += f"  ({emp['fte_num']}/{emp['fte_den']})"
        return name

    def headerData(self, section: int, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal:
            if self.is_summary_column(section):
                idx = section - len(self.days)
                _, label, tip = self.summary_columns[idx]
                if role == Qt.ItemDataRole.DisplayRole:
                    return label
                if role == Qt.ItemDataRole.ToolTipRole:
                    return tip
                if role == Qt.ItemDataRole.BackgroundRole:
                    return QBrush(QColor("#E5E7EB"))
                return None
            day = self.days[section]
            kind = day_kind(day)
            if role == Qt.ItemDataRole.DisplayRole:
                return f"{day.day}\n{PL_WEEKDAYS_SHORT[day.weekday()]}"
            if role == Qt.ItemDataRole.BackgroundRole:
                return QBrush(HEADER_TINT[kind])
            if role == Qt.ItemDataRole.ForegroundRole:
                return QBrush(HEADER_TEXT[kind])
            if role == Qt.ItemDataRole.FontRole:
                f = QFont()
                f.setPointSize(9)
                f.setBold(kind is not DayKind.WEEKDAY)
                return f
            if role == Qt.ItemDataRole.ToolTipRole:
                hol = holiday_name(day)
                base = day.strftime("%d.%m.%Y")
                return f"{base}\nŚwięto: {hol}" if hol else base
            return None

        if orientation == Qt.Orientation.Vertical:
            emp = self.employee_at(section)
            if emp is None:
                return None
            if role == Qt.ItemDataRole.DisplayRole:
                return self._emp_name(emp)
            if role == Qt.ItemDataRole.ToolTipRole:
                bits = [self._emp_name(emp)]
                if emp["position"]:
                    bits.append(emp["position"])
                summary = self._summaries.get(emp["id"])
                if summary:
                    bits.append(
                        f"Miesiąc: {summary.worked_hhmm} / wymiar "
                        f"{summary.norm_hhmm} ({summary.balance_hhmm})"
                    )
                    bits.append(
                        f"Kwartał: {fmt_signed(self.quarter_balance.get(emp['id'], 0))}"
                    )
                return "\n".join(bits)
            if role == Qt.ItemDataRole.FontRole:
                f = QFont()
                f.setPointSize(10)
                return f
        return None
