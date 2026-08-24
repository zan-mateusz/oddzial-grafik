"""Model tabeli grafiku dla QTableView."""
from __future__ import annotations

import datetime as dt

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont

from app.core.calendar_pl import (
    DayKind, PL_WEEKDAYS_SHORT, day_kind, holiday_name, month_days,
)
from app.core.rules import load_rules
from app.core.shifts import Category, fmt_minutes, resolve
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
COVER_FG = QColor("#8C4A00")

# Kolumny liczone dla całego miesiąca, niezależnie od piętra.
MONTH_COLUMNS = [
    ("Godziny", "Wypracowane godziny w całym miesiącu, łącznie z zastępstwami"),
    ("Wymiar", "Obowiązujący wymiar czasu pracy (etat, urlopy, święta)"),
    ("Bilans", "Nadgodziny (+) lub niedogodziny (−) w skali miesiąca"),
    ("Dyż.", "Liczba dyżurów w całym miesiącu"),
    ("Noc", "Godziny przypadające na porę nocną — zakres ustawiasz na "
            "zakładce Zasady"),
    ("Święta", "Godziny przepracowane w święta ustawowo wolne od pracy"),
    ("Urlop", "Dni urlopu zużyte w tym miesiącu"),
    ("L4", "Dni zwolnienia lekarskiego"),
]
# Kolumny liczone tylko dla oglądanego piętra (gdy pięter jest więcej niż jedno).
FLOOR_COLUMNS = [
    ("Godz. tu", "Godziny wypracowane na tym piętrze"),
    ("Dyż. tu", "Liczba dyżurów na tym piętrze"),
]


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
        self.summary_columns: list[tuple[str, str]] = list(MONTH_COLUMNS)
        self._show_floor_columns = False
        self._raw: dict[tuple[int, dt.date], str] = {}
        self._entries: dict = {}
        self._elsewhere: dict = {}
        self._summaries: dict = {}
        self._floor_summaries: dict = {}
        self._types: dict = {}
        self._extra_rows: list[int] = []
        self.reload()

    # --- ładowanie ----------------------------------------------------------

    def set_month(self, year: int, month: int) -> None:
        self.beginResetModel()
        self.year, self.month = year, month
        self._extra_rows.clear()
        self._load()
        self.endResetModel()

    def set_floor(self, floor_id: int | None) -> None:
        self.beginResetModel()
        self.floor_id = floor_id
        self._extra_rows.clear()
        self._load()
        self.endResetModel()

    def reload(self) -> None:
        self.beginResetModel()
        self._load()
        self.endResetModel()

    def add_cover_employee(self, employee_id: int) -> None:
        """Dodaje do grafiku osobę z innego piętra, żeby wpisać jej zastępstwo."""
        if employee_id not in self._extra_rows:
            self._extra_rows.append(employee_id)
        self.reload()

    def _load(self) -> None:
        self.rules = load_rules(self.db)
        self.days = month_days(self.year, self.month)
        self._types = self.db.shift_types_by_code()

        floors = self.db.floors()
        self._show_floor_columns = len(floors) > 1 and self.floor_id is not None
        self.summary_columns = (
            FLOOR_COLUMNS + MONTH_COLUMNS if self._show_floor_columns else list(MONTH_COLUMNS)
        )

        self.employees = self.db.employees_for_month(self.year, self.month, self.floor_id)
        shown = {e["id"] for e in self.employees}
        for emp_id in self._extra_rows:
            if emp_id not in shown:
                row = self.db.conn.execute(
                    "SELECT * FROM employees WHERE id=?", (emp_id,)
                ).fetchone()
                if row is not None:
                    self.employees.append(row)

        # Komórki pokazują dyżury tego piętra; sumy liczą cały miesiąc.
        self._raw = self.db.month_entries(self.year, self.month, self.floor_id)
        all_raw = self.db.month_entries(self.year, self.month)
        entry_floors = self.db.month_entry_floors(self.year, self.month)

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

        self._summaries = summarize_month(
            self.year, self.month, self.employees, all_entries, self.rules
        )
        self._floor_summaries = summarize_month(
            self.year, self.month, self.employees, self._entries, self.rules
        )

    # --- wymiary ------------------------------------------------------------

    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self.employees)

    def columnCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self.days) + len(self.summary_columns)

    def is_summary_column(self, col: int) -> bool:
        return col >= len(self.days)

    def date_for_column(self, col: int) -> dt.date | None:
        return self.days[col] if 0 <= col < len(self.days) else None

    def employee_at(self, row: int):
        return self.employees[row] if 0 <= row < len(self.employees) else None

    def summary_for_row(self, row: int):
        emp = self.employee_at(row)
        return self._summaries.get(emp["id"]) if emp is not None else None

    def is_cover_row(self, row: int) -> bool:
        """Czy to osoba z innego piętra, wpisana tu na zastępstwo."""
        emp = self.employee_at(row)
        return (
            emp is not None
            and self.floor_id is not None
            and emp["floor_id"] != self.floor_id
        )

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

    def _summary_data(self, row: int, idx: int, role: int):
        emp = self.employee_at(row)
        if emp is None:
            return None
        month = self._summaries.get(emp["id"])
        floor = self._floor_summaries.get(emp["id"])
        if month is None:
            return None

        offset = len(FLOOR_COLUMNS) if self._show_floor_columns else 0
        is_floor_column = self._show_floor_columns and idx < offset

        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            if is_floor_column:
                return [fmt_minutes(floor.worked_minutes), str(floor.shift_days)][idx]
            return [
                month.worked_hhmm, month.norm_hhmm, month.balance_hhmm,
                str(month.shift_days), fmt_minutes(month.night_minutes),
                fmt_minutes(month.holiday_minutes) if month.holiday_minutes else "",
                str(month.leave_days) if month.leave_days else "",
                str(month.sick_days) if month.sick_days else "",
            ][idx - offset]

        if role == Qt.ItemDataRole.TextAlignmentRole:
            return int(Qt.AlignmentFlag.AlignCenter)

        if role == Qt.ItemDataRole.BackgroundRole:
            return QBrush(QColor("#EFF3F8") if is_floor_column else QColor("#F7F8FA"))

        if role == Qt.ItemDataRole.FontRole:
            f = QFont()
            f.setPointSize(10)
            f.setBold(not is_floor_column and idx - offset in (0, 2))
            return f

        if role == Qt.ItemDataRole.ForegroundRole:
            if not is_floor_column and idx - offset == 2:
                if month.balance_minutes > 0:
                    return QBrush(QColor("#B45309"))
                if month.balance_minutes < 0:
                    return QBrush(QColor("#B00020"))
                return QBrush(QColor("#15803D"))
            return None

        if role == Qt.ItemDataRole.ToolTipRole:
            return self._summary_tooltip(idx, offset, is_floor_column, month, floor)
        return None

    def _summary_tooltip(self, idx, offset, is_floor_column, month, floor) -> str:
        base = self.summary_columns[idx][1]
        if is_floor_column or floor is None:
            return base
        j = idx - offset
        extra: list[str] = []

        if j == 4:      # pora nocna
            window = (f"{self.rules.night_start.strftime('%H:%M')}"
                      f"–{self.rules.night_end.strftime('%H:%M')}")
            extra.append(f"Przyjęta pora nocna: {window}")
        elif j == 5:    # święta
            extra.append(f"Dyżurów w święta: {month.holidays_worked}")
            if month.sunday_minutes:
                extra.append(
                    f"W niedziele: {fmt_minutes(month.sunday_minutes)} "
                    f"({month.sundays_worked} dyż.)"
                )
        elif j == 6:    # urlop
            extra.append(f"Zużyty urlop: {month.leave_hhmm}")
            if month.leave_ignored:
                extra.append(
                    f"Pominięto wpisów w dni wolne: {month.leave_ignored} "
                    "(urlopu udziela się tylko w dni pracy)"
                )
        elif j in (0, 1, 2, 3):
            elsewhere = month.shift_days - floor.shift_days
            if elsewhere > 0 and self.floor_id is not None:
                here = self.db.floor_name(self.floor_id)
                extra.append(f"Na tym piętrze ({here}): {floor.shift_days} dyż.")
                extra.append(f"Na innych piętrach: {elsewhere} dyż.")

        return base + ("\n\n" + "\n".join(extra) if extra else "")

    def setData(self, index: QModelIndex, value, role=Qt.ItemDataRole.EditRole) -> bool:
        if role != Qt.ItemDataRole.EditRole or not index.isValid():
            return False
        if self.is_summary_column(index.column()):
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
        if index.isValid() and not self.is_summary_column(index.column()):
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
                label, tip = self.summary_columns[idx]
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
            cover = self.is_cover_row(section)
            if role == Qt.ItemDataRole.DisplayRole:
                name = self._emp_name(emp)
                if cover:
                    name += f"  ↻ {self.db.floor_name(emp['floor_id'])}"
                return name
            if role == Qt.ItemDataRole.ForegroundRole and cover:
                return QBrush(COVER_FG)
            if role == Qt.ItemDataRole.ToolTipRole:
                bits = [self._emp_name(emp)]
                if emp["position"]:
                    bits.append(emp["position"])
                if cover:
                    bits.append(
                        f"Pracuje na piętrze: {self.db.floor_name(emp['floor_id'])}"
                        " — tutaj na zastępstwie"
                    )
                s = self._summaries.get(emp["id"])
                if s:
                    bits.append(
                        f"Cały miesiąc: {s.worked_hhmm} / wymiar {s.norm_hhmm} ({s.balance_hhmm})"
                    )
                return "\n".join(bits)
            if role == Qt.ItemDataRole.FontRole:
                f = QFont()
                f.setPointSize(10)
                f.setItalic(cover)
                return f
        return None
