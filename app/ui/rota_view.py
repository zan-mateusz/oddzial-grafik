"""Zakładka z grafikiem miesięcznym."""
from __future__ import annotations

import datetime as dt

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QFont, QKeySequence
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QDialog, QDialogButtonBox, QHBoxLayout,
    QHeaderView, QLabel, QListWidget, QListWidgetItem, QMenu, QMessageBox,
    QPushButton, QSpinBox, QTableView, QToolButton, QVBoxLayout, QWidget,
)

from app.core.calendar_pl import PL_MONTHS_TITLE, day_kind, month_norm
from app.core.shifts import fmt_minutes
from app.core.stats import daily_coverage
from app.ui.delegates import ShiftCellDelegate
from app.ui.rota_model import RotaModel

DAY_COL_MIN = 26
DAY_COL_MAX = 44
SUMMARY_COL_WIDTH = 56
NAME_COL_WIDTH = 186


class CoverPickerDialog(QDialog):
    """Wybór osób z innych pięter do wpisania na zastępstwo."""

    def __init__(self, db, candidates, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Dodaj zastępstwo")
        self.setMinimumWidth(420)
        self._candidates = candidates

        self.list = QListWidget()
        self.list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        for emp in candidates:
            name = f"{emp['last_name']} {emp['first_name']}".strip()
            floor = db.floor_name(emp["floor_id"]) or "bez piętra"
            item = QListWidgetItem(f"{name} — {floor}")
            item.setData(Qt.ItemDataRole.UserRole, emp["id"])
            self.list.addItem(item)

        hint = QLabel(
            "Wybrane osoby pojawią się w grafiku tego piętra. Wpisany im dyżur "
            "liczy się do ich własnego miesięcznego wymiaru czasu pracy."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#555;")

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Dodaj")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Anuluj")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(self.list)
        layout.addWidget(hint)
        layout.addWidget(buttons)

    def selected_ids(self) -> list[int]:
        return [i.data(Qt.ItemDataRole.UserRole) for i in self.list.selectedItems()]


class RotaView(QWidget):
    """Grafik: nawigacja po miesiącach, siatka, szybkie wypełnianie."""

    monthChanged = Signal(int, int)
    dataEdited = Signal()

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        today = dt.date.today()
        floors = db.floors()
        self.floor_id = floors[0]["id"] if floors else None
        self.model = RotaModel(db, today.year, today.month, self.floor_id, self)
        self.model.entryChanged.connect(self._on_edited)

        self._build_ui()
        self._apply_month_to_controls()
        self._refresh_palette()
        self._refresh_footer()

    # --- budowa interfejsu --------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 8, 10, 8)
        root.setSpacing(6)

        root.addLayout(self._build_toolbar())

        self.palette_bar = QHBoxLayout()
        self.palette_bar.setSpacing(4)
        pal_wrap = QWidget()
        pal_wrap.setLayout(self.palette_bar)
        root.addWidget(pal_wrap)

        self.table = QTableView()
        self.table.setModel(self.model)
        self.delegate = ShiftCellDelegate(self.db, self.table)
        self.table.setItemDelegate(self.delegate)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ContiguousSelection)
        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked
            | QAbstractItemView.EditTrigger.EditKeyPressed
            | QAbstractItemView.EditTrigger.AnyKeyPressed
        )
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.table.setAlternatingRowColors(False)
        self.table.setShowGrid(True)
        self.table.setCornerButtonEnabled(False)
        vh = self.table.verticalHeader()
        vh.setDefaultSectionSize(26)
        vh.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        vh.setFixedWidth(NAME_COL_WIDTH)
        vh.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        hh.setFixedHeight(38)
        root.addWidget(self.table, 1)

        self.footer = QLabel()
        self.footer.setTextFormat(Qt.TextFormat.RichText)
        self.footer.setWordWrap(True)
        root.addWidget(self.footer)

        self.table.selectionModel().currentChanged.connect(
            lambda *_: self._refresh_footer()
        )

        self._delete_action = QAction(self)
        self._delete_action.setShortcut(QKeySequence(Qt.Key.Key_Delete))
        self._delete_action.triggered.connect(lambda: self._fill_selection(""))
        self.addAction(self._delete_action)

        self._resize_columns()

    def _build_toolbar(self) -> QHBoxLayout:
        bar = QHBoxLayout()
        bar.setSpacing(6)

        self.btn_prev = QToolButton()
        self.btn_prev.setText("◀")
        self.btn_prev.setToolTip("Poprzedni miesiąc")
        self.btn_prev.clicked.connect(lambda: self._step_month(-1))

        self.btn_next = QToolButton()
        self.btn_next.setText("▶")
        self.btn_next.setToolTip("Następny miesiąc")
        self.btn_next.clicked.connect(lambda: self._step_month(1))

        self.cmb_month = QComboBox()
        self.cmb_month.addItems(PL_MONTHS_TITLE)
        self.cmb_month.currentIndexChanged.connect(self._on_controls_changed)

        self.spin_year = QSpinBox()
        self.spin_year.setRange(2000, 2100)
        self.spin_year.valueChanged.connect(self._on_controls_changed)

        self.btn_today = QPushButton("Bieżący miesiąc")
        self.btn_today.clicked.connect(self._go_today)

        self.cmb_floor = QComboBox()
        self.cmb_floor.setToolTip("Piętro, którego grafik jest wyświetlany")

        self.btn_cover = QPushButton("Dodaj zastępstwo…")
        self.btn_cover.setToolTip(
            "Dopisz do tego grafiku osobę z innego piętra, aby wpisać jej dyżur"
        )
        self.btn_cover.clicked.connect(self._add_cover)

        # Dopiero teraz — wypełnienie listy pięter ustawia widoczność obu kontrolek.
        self._reload_floors()
        self.cmb_floor.currentIndexChanged.connect(self._on_floor_changed)

        bar.addWidget(self.btn_prev)
        bar.addWidget(self.cmb_month)
        bar.addWidget(self.spin_year)
        bar.addWidget(self.btn_next)
        bar.addWidget(self.btn_today)
        bar.addSpacing(16)
        bar.addWidget(QLabel("Piętro:"))
        bar.addWidget(self.cmb_floor)
        bar.addWidget(self.btn_cover)
        bar.addSpacing(16)

        self.lbl_norm = QLabel()
        f = QFont()
        f.setBold(True)
        self.lbl_norm.setFont(f)
        bar.addWidget(self.lbl_norm)
        bar.addStretch(1)
        return bar

    # --- paleta zmian -------------------------------------------------------

    def _refresh_palette(self) -> None:
        while self.palette_bar.count():
            item = self.palette_bar.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        hint = QLabel("Wypełnij zaznaczenie:")
        hint.setStyleSheet("color:#555;")
        self.palette_bar.addWidget(hint)

        for st in self.db.shift_types():
            btn = QToolButton()
            btn.setText(st.code)
            tip = st.name or st.code
            if st.start and st.end:
                tip += f"  ({st.start.strftime('%H:%M')}–{st.end.strftime('%H:%M')}, {fmt_minutes(st.minutes)})"
            btn.setToolTip(tip)
            btn.setStyleSheet(
                f"QToolButton{{background:{st.color};border:1px solid #B9BFC9;"
                f"border-radius:4px;padding:3px 8px;font-weight:600;}}"
                f"QToolButton:hover{{border:1px solid #4B5563;}}"
            )
            btn.clicked.connect(lambda _=False, code=st.code: self._fill_selection(code))
            self.palette_bar.addWidget(btn)

        btn_clear = QToolButton()
        btn_clear.setText("Wyczyść")
        btn_clear.setToolTip("Usuń wpisy z zaznaczonych komórek (Delete)")
        btn_clear.setStyleSheet(
            "QToolButton{border:1px solid #B9BFC9;border-radius:4px;padding:3px 8px;}"
        )
        btn_clear.clicked.connect(lambda: self._fill_selection(""))
        self.palette_bar.addWidget(btn_clear)
        self.palette_bar.addStretch(1)
        self.delegate.refresh_codes()

    def _selected_cells(self) -> list[tuple[int, int]]:
        return [
            (i.row(), i.column())
            for i in self.table.selectionModel().selectedIndexes()
            if not self.model.is_summary_column(i.column())
        ]

    def _fill_selection(self, code: str) -> None:
        cells = self._selected_cells()
        if cells:
            self.model.set_range(cells, code)

    def _show_context_menu(self, pos) -> None:
        index = self.table.indexAt(pos)
        if not index.isValid():
            return
        if not self.table.selectionModel().isSelected(index):
            self.table.setCurrentIndex(index)
        menu = QMenu(self)
        for st in self.db.shift_types():
            act = menu.addAction(f"{st.code} — {st.name}" if st.name else st.code)
            act.triggered.connect(lambda _=False, c=st.code: self._fill_selection(c))
        menu.addSeparator()
        menu.addAction("Wyczyść", lambda: self._fill_selection(""))
        menu.exec(self.table.viewport().mapToGlobal(pos))

    # --- miesiąc ------------------------------------------------------------

    def _apply_month_to_controls(self) -> None:
        self.cmb_month.blockSignals(True)
        self.spin_year.blockSignals(True)
        self.cmb_month.setCurrentIndex(self.model.month - 1)
        self.spin_year.setValue(self.model.year)
        self.cmb_month.blockSignals(False)
        self.spin_year.blockSignals(False)

    def _on_controls_changed(self) -> None:
        self.set_month(self.spin_year.value(), self.cmb_month.currentIndex() + 1)

    def _step_month(self, delta: int) -> None:
        y, m = self.model.year, self.model.month + delta
        if m < 1:
            y, m = y - 1, 12
        elif m > 12:
            y, m = y + 1, 1
        self.set_month(y, m)

    def _go_today(self) -> None:
        today = dt.date.today()
        self.set_month(today.year, today.month)

    def set_month(self, year: int, month: int) -> None:
        if (year, month) == (self.model.year, self.model.month):
            return
        self.model.set_month(year, month)
        self._apply_month_to_controls()
        self._resize_columns()
        self._refresh_footer()
        self.monthChanged.emit(year, month)

    def _reload_floors(self) -> None:
        self.cmb_floor.blockSignals(True)
        self.cmb_floor.clear()
        floors = self.db.floors()
        for floor in floors:
            self.cmb_floor.addItem(floor["name"], floor["id"])
        if self.floor_id is not None:
            index = self.cmb_floor.findData(self.floor_id)
            if index >= 0:
                self.cmb_floor.setCurrentIndex(index)
        self.cmb_floor.blockSignals(False)
        multi = len(floors) > 1
        self.cmb_floor.setVisible(multi)
        self.btn_cover.setVisible(multi)

    def _on_floor_changed(self) -> None:
        floor_id = self.cmb_floor.currentData()
        if floor_id == self.floor_id:
            return
        self.floor_id = floor_id
        self.model.set_floor(floor_id)
        self._resize_columns()
        self._refresh_footer()

    def _add_cover(self) -> None:
        """Dopisuje do grafiku osobę z innego piętra."""
        shown = {e["id"] for e in self.model.employees}
        candidates = [
            e for e in self.db.employees()
            if e["id"] not in shown and e["floor_id"] != self.floor_id
        ]
        if not candidates:
            QMessageBox.information(
                self, "Zastępstwo",
                "Wszyscy pracownicy z pozostałych pięter są już w tym grafiku.",
            )
            return
        dialog = CoverPickerDialog(self.db, candidates, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        for emp_id in dialog.selected_ids():
            self.model.add_cover_employee(emp_id)
        self._resize_columns()
        self._refresh_footer()

    def refresh(self) -> None:
        self._reload_floors()
        self.model.floor_id = self.floor_id
        self.model.reload()
        self._refresh_palette()
        self._resize_columns()
        self._refresh_footer()

    def _on_edited(self) -> None:
        self._refresh_footer()
        self.dataEdited.emit()

    # --- układ kolumn i stopka ---------------------------------------------

    def _resize_columns(self) -> None:
        """Dni rozciągają się na dostępną szerokość, żeby kolumny podsumowania
        (godziny, wymiar, bilans) mieściły się w oknie bez przewijania."""
        n_days = len(self.model.days)
        if not n_days:
            return
        summary_width = SUMMARY_COL_WIDTH * len(self.model.summary_columns)
        available = self.table.viewport().width() - summary_width - 4
        day_width = max(DAY_COL_MIN, min(DAY_COL_MAX, available // n_days))
        for col in range(self.model.columnCount()):
            width = SUMMARY_COL_WIDTH if self.model.is_summary_column(col) else day_width
            self.table.setColumnWidth(col, width)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._resize_columns()

    def _refresh_footer(self) -> None:
        norm = month_norm(self.model.year, self.model.month,
                          self.model.rules.daily_norm_minutes)
        floor_txt = ""
        if self.cmb_floor.isVisible():
            floor_txt = f"{self.db.floor_name(self.floor_id)}   •   "
        self.lbl_norm.setText(
            f"{floor_txt}{PL_MONTHS_TITLE[self.model.month - 1]} {self.model.year}   •   "
            f"wymiar: {fmt_minutes(norm.minutes)} h  ({norm.working_days} dni roboczych)"
        )

        total = sum(s.worked_minutes for s in self.model._summaries.values())
        unknown = sum(s.unknown_entries for s in self.model._summaries.values())
        staff = len(self.model.employees)

        holidays_in_month = [
            (d, day_kind(d)) for d in self.model.days if day_kind(d).value == "święto"
        ]
        from app.core.calendar_pl import holiday_name
        hol_txt = ", ".join(
            f"{d.day}.{d.month:02d} {holiday_name(d)}" for d, _ in holidays_in_month
        ) or "brak"

        coverage_txt = self._coverage_text()

        warn = (
            f" &nbsp; <span style='color:#B00020;font-weight:600'>"
            f"⚠ nierozpoznane wpisy: {unknown}</span>" if unknown else ""
        )
        covers = sum(
            1 for r in range(len(self.model.employees)) if self.model.is_cover_row(r)
        )
        cover_txt = (
            f" &nbsp;•&nbsp; <span style='color:#8C4A00'>na zastępstwie: "
            f"<b>{covers}</b></span>" if covers else ""
        )
        self.footer.setText(
            f"<span style='color:#444'>Pracowników w grafiku: <b>{staff}</b>{cover_txt} &nbsp;•&nbsp; "
            f"łącznie godzin: <b>{fmt_minutes(total)}</b> &nbsp;•&nbsp; "
            f"święta: {hol_txt}</span>{coverage_txt}{warn}"
        )

    def _coverage_text(self) -> str:
        """Obsada dnia wskazanego kursorem — ile osób na której zmianie."""
        index = self.table.currentIndex()
        if not index.isValid() or self.model.is_summary_column(index.column()):
            return ""
        day = self.model.date_for_column(index.column())
        if day is None:
            return ""
        counts = daily_coverage([day], self.model.employees, self.model._entries)[day]
        if not counts:
            body = "nikt nie pracuje"
        else:
            body = ", ".join(f"{code}: <b>{n}</b>" for code, n in sorted(counts.items()))
        return (
            f"<br><span style='color:#444'>Obsada {day.day}.{day.month:02d}: {body}</span>"
        )
