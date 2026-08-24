"""Zakładka: definicje zmian (kody używane w grafiku)."""
from __future__ import annotations

import datetime as dt

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView, QColorDialog, QComboBox, QDialog, QDialogButtonBox,
    QFormLayout, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMessageBox,
    QPushButton, QTableWidget, QTableWidgetItem, QTimeEdit, QVBoxLayout,
    QWidget,
)

from app.core.shifts import Category, ShiftType, fmt_minutes, span_minutes


class ShiftTypeDialog(QDialog):
    def __init__(self, parent=None, st: ShiftType | None = None):
        super().__init__(parent)
        self.setWindowTitle("Definicja zmiany")
        self.setMinimumWidth(400)
        self._color = st.color if st else "#E8EDF4"
        self._st = st

        self.ed_code = QLineEdit(st.code if st else "")
        self.ed_code.setPlaceholderText("np. D, N, R, U, L4")
        self.ed_code.setMaxLength(6)
        self.ed_name = QLineEdit(st.name if st else "")
        self.ed_name.setPlaceholderText("np. Dyżur dzienny")

        self.cmb_category = QComboBox()
        for cat in Category:
            self.cmb_category.addItem(cat.value.capitalize(), cat)
        if st:
            self.cmb_category.setCurrentIndex(list(Category).index(st.category))

        self.te_start = QTimeEdit()
        self.te_start.setDisplayFormat("HH:mm")
        self.te_end = QTimeEdit()
        self.te_end.setDisplayFormat("HH:mm")
        if st and st.start and st.end:
            self.te_start.setTime(st.start)
            self.te_end.setTime(st.end)
        else:
            self.te_start.setTime(dt.time(7, 0))
            self.te_end.setTime(dt.time(19, 0))

        self.btn_color = QPushButton("Zmień kolor")
        self.btn_color.clicked.connect(self._pick_color)
        self.lbl_color = QLabel()
        self.lbl_color.setFixedSize(60, 22)
        self._paint_color()
        color_row = QHBoxLayout()
        color_row.addWidget(self.lbl_color)
        color_row.addWidget(self.btn_color)
        color_row.addStretch(1)
        color_wrap = QWidget()
        color_wrap.setLayout(color_row)

        self.lbl_duration = QLabel()
        self.te_start.timeChanged.connect(self._update_duration)
        self.te_end.timeChanged.connect(self._update_duration)
        self.cmb_category.currentIndexChanged.connect(self._update_enabled)

        form = QFormLayout()
        form.addRow("Kod *", self.ed_code)
        form.addRow("Nazwa", self.ed_name)
        form.addRow("Rodzaj", self.cmb_category)
        form.addRow("Od godziny", self.te_start)
        form.addRow("Do godziny", self.te_end)
        form.addRow("Czas trwania", self.lbl_duration)
        form.addRow("Kolor", color_wrap)

        self.lbl_hint = QLabel(
            "Zmiana kończąca się o godzinie wcześniejszej niż początek jest "
            "traktowana jako nocna i przechodzi przez północ."
        )
        self.lbl_hint.setWordWrap(True)
        self.lbl_hint.setStyleSheet("color:#555;")

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Zapisz")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Anuluj")
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.lbl_hint)
        layout.addWidget(buttons)

        self._update_enabled()
        self._update_duration()

    def _pick_color(self) -> None:
        color = QColorDialog.getColor(QColor(self._color), self, "Kolor zmiany")
        if color.isValid():
            self._color = color.name()
            self._paint_color()

    def _paint_color(self) -> None:
        self.lbl_color.setStyleSheet(
            f"background:{self._color};border:1px solid #999;border-radius:3px;"
        )

    def _is_timed(self) -> bool:
        return self.cmb_category.currentData() is Category.WORK

    def _update_enabled(self) -> None:
        timed = self._is_timed()
        for w in (self.te_start, self.te_end):
            w.setEnabled(timed)
        self._update_duration()

    def _update_duration(self) -> None:
        if not self._is_timed():
            self.lbl_duration.setText("—  (wpis nie generuje godzin pracy)")
            return
        minutes = span_minutes(self.te_start.time().toPython(), self.te_end.time().toPython())
        night = " • zmiana nocna" if self.te_end.time() <= self.te_start.time() else ""
        self.lbl_duration.setText(f"{fmt_minutes(minutes)} h{night}")

    def _accept(self) -> None:
        if not self.ed_code.text().strip():
            QMessageBox.warning(self, "Brak kodu", "Podaj kod zmiany, np. D albo N.")
            return
        self.accept()

    def values(self) -> ShiftType:
        cat = self.cmb_category.currentData()
        timed = cat is Category.WORK
        return ShiftType(
            id=self._st.id if self._st else None,
            code=self.ed_code.text().strip().upper(),
            name=self.ed_name.text().strip(),
            start=self.te_start.time().toPython() if timed else None,
            end=self.te_end.time().toPython() if timed else None,
            category=cat,
            color=self._color,
        )


class ShiftTypesView(QWidget):
    HEADERS = ["Kod", "Nazwa", "Rodzaj", "Od", "Do", "Czas", "Kolor"]

    def __init__(self, db, on_change=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.on_change = on_change
        self._build_ui()
        self.reload()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)

        bar = QHBoxLayout()
        for text, slot in [
            ("Dodaj", self.add_type), ("Edytuj", self.edit_type), ("Usuń", self.delete_type),
        ]:
            btn = QPushButton(text)
            btn.clicked.connect(slot)
            bar.addWidget(btn)
        bar.addStretch(1)
        root.addLayout(bar)

        self.table = QTableWidget(0, len(self.HEADERS))
        self.table.setHorizontalHeaderLabels(self.HEADERS)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.doubleClicked.connect(self.edit_type)
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        root.addWidget(self.table)

        hint = QLabel(
            "Kody wpisujesz wprost w grafiku. Krótszy dyżur zapisz samym czasem "
            "trwania: <b>7:30</b>, <b>10</b>, <b>6:45</b> — przecinek działa jak "
            "dwukropek, więc <b>7,3</b> to 7 godz. 30 min. Można też podać "
            "przedział godzin, np. <b>8-14</b>."
        )
        hint.setTextFormat(Qt.TextFormat.RichText)
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#555;")
        root.addWidget(hint)

    def reload(self) -> None:
        self._types = self.db.shift_types()
        self.table.setRowCount(len(self._types))
        for r, st in enumerate(self._types):
            timed = st.start is not None and st.end is not None
            values = [
                st.code, st.name, st.category.value.capitalize(),
                st.start.strftime("%H:%M") if timed else "—",
                st.end.strftime("%H:%M") if timed else "—",
                fmt_minutes(st.minutes) if st.minutes else "—",
                "",
            ]
            for c, val in enumerate(values):
                item = QTableWidgetItem(str(val))
                if c == 0:
                    item.setBackground(QColor(st.color))
                self.table.setItem(r, c, item)
            swatch = QTableWidgetItem("")
            swatch.setBackground(QColor(st.color))
            swatch.setToolTip(st.color)
            self.table.setItem(r, len(values) - 1, swatch)

    def _selected(self) -> ShiftType | None:
        r = self.table.currentRow()
        return self._types[r] if 0 <= r < len(self._types) else None

    def add_type(self) -> None:
        dlg = ShiftTypeDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        st = dlg.values()
        if any(t.code == st.code for t in self._types):
            QMessageBox.warning(self, "Kod zajęty", f"Zmiana o kodzie „{st.code}” już istnieje.")
            return
        self.db.save_shift_type(st)
        self.reload()
        self._notify()

    def edit_type(self) -> None:
        st = self._selected()
        if st is None:
            return
        dlg = ShiftTypeDialog(self, st)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        new = dlg.values()
        if any(t.code == new.code and t.id != new.id for t in self._types):
            QMessageBox.warning(self, "Kod zajęty", f"Zmiana o kodzie „{new.code}” już istnieje.")
            return
        self.db.save_shift_type(new)
        self.reload()
        self._notify()

    def delete_type(self) -> None:
        st = self._selected()
        if st is None or st.id is None:
            return
        used = self.db.conn.execute(
            "SELECT COUNT(*) AS n FROM entries WHERE UPPER(raw)=?", (st.code.upper(),)
        ).fetchone()["n"]
        msg = f"Usunąć definicję zmiany „{st.code}”?"
        if used:
            msg += (
                f"\n\nUwaga: kod jest użyty {used} razy w grafikach. Te wpisy pozostaną, "
                "ale przestaną być rozpoznawane i nie będą liczone do godzin."
            )
        answer = QMessageBox.question(
            self, "Usunięcie zmiany", msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.db.delete_shift_type(st.id)
        self.reload()
        self._notify()

    def _notify(self) -> None:
        if self.on_change:
            self.on_change()
