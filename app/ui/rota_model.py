"""Model tabeli grafiku dla QTableView."""
from __future__ import annotations

import datetime as dt

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont

from app.core.calendar_pl import (
    DayKind, NORM_MEDICAL_MINUTES, PL_WEEKDAYS_SHORT, day_kind, holiday_name,
    month_days,
)
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

SUMMARY_COLUMNS = [
    ("Godziny", "Wypracowane godziny w miesiącu"),
    ("Wymiar", "Obowiązujący wymiar czasu pracy (etat, urlopy, święta)"),
    ("Bilans", "Nadgodziny (+) lub niedogodziny (−)"),
    ("Dyż.", "Liczba dyżurów"),
    ("Noc", "Godziny w porze nocnej (21:00–7:00)"),
    ("Urlop", "Dni urlopu"),
    ("L4", "Dni zwolnienia lekarskiego"),
]


class RotaModel(QAbstractTableModel):
    """Wiersz = pracownik, kolumna = dzień miesiąca, potem podsumowanie."""

    entryChanged = Signal()

    def __init__(self, db, year: int, month: int, parent=None):
        super().__init__(parent)
        self.db = db
        self.year = year
        self.month = month
        self.daily_norm = NORM_MEDICAL_MINUTES
        self.days: list[dt.date] = []
        self.employees: list = []
        self._raw: dict[tuple[int, dt.date], str] = {}
        self._entries: dict = {}
        self._summaries: dict = {}
        self._types: dict = {}
        self.reload()

    # --- ładowanie ----------------------------------------------------------

    def set_month(self, year: int, month: int) -> None:
        self.beginResetModel()
        self.year, self.month = year, month
        self._load()
        self.endResetModel()

    def reload(self) -> None:
        self.beginResetModel()
        self._load()
        self.endResetModel()

    def _load(self) -> None:
        self.daily_norm = int(self.db.get_setting("daily_norm_minutes", str(NORM_MEDICAL_MINUTES)))
        self.days = month_days(self.year, self.month)
        self.employees = self.db.employees_for_month(self.year, self.month)
        self._types = self.db.shift_types_by_code()
        self._raw = self.db.month_entries(self.year, self.month)
        self._rebuild_entries()

    def _rebuild_entries(self) -> None:
        self._entries = {}
        for key, raw in self._raw.items():
            entry = resolve(raw, self._types)
            if entry is not None:
                self._entries[key] = entry
        self._summaries = summarize_month(
            self.year, self.month, self.employees, self._entries, self.daily_norm
        )

    # --- wymiary ------------------------------------------------------------

    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self.employees)

    def columnCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self.days) + len(SUMMARY_COLUMNS)

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
        entry = self._entries.get((emp["id"], day))
        kind = day_kind(day)

        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            if role == Qt.ItemDataRole.EditRole:
                return self._raw.get((emp["id"], day), "")
            return entry.label if entry else ""

        if role == Qt.ItemDataRole.BackgroundRole:
            if entry is not None:
                return QBrush(QColor(entry.color))
            return QBrush(DAY_TINT[kind])

        if role == Qt.ItemDataRole.ForegroundRole:
            if entry is not None and entry.unknown:
                return QBrush(QColor("#B00020"))
            return None

        if role == Qt.ItemDataRole.TextAlignmentRole:
            return int(Qt.AlignmentFlag.AlignCenter)

        if role == Qt.ItemDataRole.FontRole:
            f = QFont()
            # Wpisy godzinowe ("7:30-19:30") są dłuższe niż kody zmian i muszą
            # zmieścić się w wąskiej kolumnie dnia.
            label = entry.label if entry else ""
            f.setPointSize(10 if len(label) <= 3 else (8 if len(label) <= 5 else 7))
            if entry is not None and entry.category is Category.WORK:
                f.setBold(True)
            return f

        if role == Qt.ItemDataRole.ToolTipRole:
            parts = [f"{self._emp_name(emp)} — {day.strftime('%d.%m.%Y')} ({PL_WEEKDAYS_SHORT[day.weekday()]})"]
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
            return "\n".join(parts)

        return None

    def _summary_data(self, row: int, idx: int, role: int):
        s = self.summary_for_row(row)
        if s is None:
            return None
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            return [
                s.worked_hhmm, s.norm_hhmm, s.balance_hhmm, str(s.shift_days),
                fmt_minutes(s.night_minutes),
                str(s.leave_days) if s.leave_days else "",
                str(s.sick_days) if s.sick_days else "",
            ][idx]
        if role == Qt.ItemDataRole.TextAlignmentRole:
            return int(Qt.AlignmentFlag.AlignCenter)
        if role == Qt.ItemDataRole.BackgroundRole:
            return QBrush(QColor("#F7F8FA"))
        if role == Qt.ItemDataRole.FontRole:
            f = QFont()
            f.setPointSize(10)
            f.setBold(idx in (0, 2))
            return f
        if role == Qt.ItemDataRole.ForegroundRole and idx == 2:
            if s.balance_minutes > 0:
                return QBrush(QColor("#B45309"))
            if s.balance_minutes < 0:
                return QBrush(QColor("#B00020"))
            return QBrush(QColor("#15803D"))
        if role == Qt.ItemDataRole.ToolTipRole:
            return SUMMARY_COLUMNS[idx][1]
        return None

    def setData(self, index: QModelIndex, value, role=Qt.ItemDataRole.EditRole) -> bool:
        if role != Qt.ItemDataRole.EditRole or not index.isValid():
            return False
        if self.is_summary_column(index.column()):
            return False
        emp = self.employee_at(index.row())
        day = self.days[index.column()]
        raw = (str(value) or "").strip()
        key = (emp["id"], day)
        if self._raw.get(key, "") == raw:
            return False
        self.db.set_entry(emp["id"], day, raw)
        if raw:
            self._raw[key] = raw
        else:
            self._raw.pop(key, None)
        self._rebuild_entries()
        self.dataChanged.emit(index, index)
        # Podsumowanie wiersza zależy od całego miesiąca.
        self.dataChanged.emit(
            self.index(index.row(), len(self.days)),
            self.index(index.row(), self.columnCount() - 1),
        )
        self.entryChanged.emit()
        return True

    def set_range(self, cells: list[tuple[int, int]], raw: str) -> None:
        """Wypełnia wiele komórek naraz (zaznaczenie + wybór zmiany)."""
        items = []
        for row, col in cells:
            if self.is_summary_column(col):
                continue
            emp = self.employee_at(row)
            if emp is None:
                continue
            day = self.days[col]
            items.append((emp["id"], day, raw))
            key = (emp["id"], day)
            if raw.strip():
                self._raw[key] = raw.strip()
            else:
                self._raw.pop(key, None)
        if not items:
            return
        self.db.set_entries_bulk(items)
        self._rebuild_entries()
        self.beginResetModel()
        self.endResetModel()
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
                if role == Qt.ItemDataRole.DisplayRole:
                    return SUMMARY_COLUMNS[idx][0]
                if role == Qt.ItemDataRole.ToolTipRole:
                    return SUMMARY_COLUMNS[idx][1]
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
                s = self._summaries.get(emp["id"])
                if s:
                    bits.append(f"Godziny: {s.worked_hhmm} / wymiar {s.norm_hhmm} ({s.balance_hhmm})")
                return "\n".join(bits)
            if role == Qt.ItemDataRole.FontRole:
                f = QFont()
                f.setPointSize(10)
                return f
        return None
