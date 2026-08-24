"""Zakładka: pracownicy."""
from __future__ import annotations

import datetime as dt

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QDialog, QDialogButtonBox,
    QFormLayout, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMessageBox,
    QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

FTE_CHOICES = [
    ("pełny etat", 1, 1), ("3/4 etatu", 3, 4), ("1/2 etatu", 1, 2),
    ("1/4 etatu", 1, 4), ("1/3 etatu", 1, 3), ("2/3 etatu", 2, 3),
]


class EmployeeDialog(QDialog):
    def __init__(self, parent=None, row=None):
        super().__init__(parent)
        self.setWindowTitle("Pracownik")
        self.setMinimumWidth(380)

        self.ed_last = QLineEdit()
        self.ed_first = QLineEdit()
        self.ed_position = QLineEdit()
        self.ed_position.setPlaceholderText("np. pielęgniarka, oddziałowa")
        self.cmb_fte = QComboBox()
        for label, num, den in FTE_CHOICES:
            self.cmb_fte.addItem(label, (num, den))
        self.ed_hired = QLineEdit()
        self.ed_hired.setPlaceholderText("RRRR-MM-DD (opcjonalnie)")
        self.ed_ended = QLineEdit()
        self.ed_ended.setPlaceholderText("RRRR-MM-DD (opcjonalnie)")
        self.chk_active = QCheckBox("Pracuje obecnie")
        self.chk_active.setChecked(True)
        self.ed_notes = QLineEdit()

        if row is not None:
            self.ed_last.setText(row["last_name"])
            self.ed_first.setText(row["first_name"])
            self.ed_position.setText(row["position"])
            for i in range(self.cmb_fte.count()):
                if self.cmb_fte.itemData(i) == (row["fte_num"], row["fte_den"]):
                    self.cmb_fte.setCurrentIndex(i)
                    break
            self.ed_hired.setText(row["hired_on"] or "")
            self.ed_ended.setText(row["ended_on"] or "")
            self.chk_active.setChecked(bool(row["active"]))
            self.ed_notes.setText(row["notes"])

        form = QFormLayout()
        form.addRow("Nazwisko *", self.ed_last)
        form.addRow("Imię", self.ed_first)
        form.addRow("Stanowisko", self.ed_position)
        form.addRow("Wymiar etatu", self.cmb_fte)
        form.addRow("Zatrudniona od", self.ed_hired)
        form.addRow("Zatrudniona do", self.ed_ended)
        form.addRow("", self.chk_active)
        form.addRow("Uwagi", self.ed_notes)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Zapisz")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Anuluj")
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _accept(self) -> None:
        if not self.ed_last.text().strip():
            QMessageBox.warning(self, "Brak nazwiska", "Podaj nazwisko pracownika.")
            return
        for field, label in ((self.ed_hired, "Zatrudniona od"), (self.ed_ended, "Zatrudniona do")):
            text = field.text().strip()
            if text:
                try:
                    dt.date.fromisoformat(text)
                except ValueError:
                    QMessageBox.warning(
                        self, "Zła data", f"Pole „{label}” musi mieć format RRRR-MM-DD."
                    )
                    return
        self.accept()

    def values(self) -> dict:
        num, den = self.cmb_fte.currentData()
        return {
            "last_name": self.ed_last.text().strip(),
            "first_name": self.ed_first.text().strip(),
            "position": self.ed_position.text().strip(),
            "fte_num": num,
            "fte_den": den,
            "hired_on": self.ed_hired.text().strip() or None,
            "ended_on": self.ed_ended.text().strip() or None,
            "active": 1 if self.chk_active.isChecked() else 0,
            "notes": self.ed_notes.text().strip(),
        }


class EmployeesView(QWidget):
    HEADERS = ["Nazwisko", "Imię", "Stanowisko", "Etat", "Od", "Do", "Pracuje", "Uwagi"]

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
        for text, slot, tip in [
            ("Dodaj", self.add_employee, "Dodaj nowego pracownika"),
            ("Edytuj", self.edit_employee, "Zmień dane zaznaczonego pracownika"),
            ("Zakończ pracę", self.deactivate_employee,
             "Oznacz jako niepracującego — grafiki z przeszłości pozostaną nietknięte"),
            ("Usuń trwale", self.delete_employee,
             "Usuwa pracownika RAZEM z wszystkimi jego wpisami w grafikach"),
        ]:
            btn = QPushButton(text)
            btn.setToolTip(tip)
            btn.clicked.connect(slot)
            bar.addWidget(btn)
        bar.addSpacing(20)
        for text, delta in (("▲", -1), ("▼", 1)):
            btn = QPushButton(text)
            btn.setFixedWidth(34)
            btn.setToolTip("Zmień kolejność w grafiku")
            btn.clicked.connect(lambda _=False, d=delta: self.move_employee(d))
            bar.addWidget(btn)
        bar.addSpacing(20)
        self.chk_show_inactive = QCheckBox("Pokaż byłych pracowników")
        self.chk_show_inactive.stateChanged.connect(self.reload)
        bar.addWidget(self.chk_show_inactive)
        bar.addStretch(1)
        root.addLayout(bar)

        self.table = QTableWidget(0, len(self.HEADERS))
        self.table.setHorizontalHeaderLabels(self.HEADERS)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.doubleClicked.connect(self.edit_employee)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(len(self.HEADERS) - 1, QHeaderView.ResizeMode.Stretch)
        root.addWidget(self.table)

        self.lbl_hint = QLabel(
            "Kolejność na liście odpowiada kolejności wierszy w grafiku. "
            "„Zakończ pracę” jest bezpieczniejsze niż usuwanie — zachowuje historię."
        )
        self.lbl_hint.setStyleSheet("color:#555;")
        self.lbl_hint.setWordWrap(True)
        root.addWidget(self.lbl_hint)

    def reload(self) -> None:
        rows = self.db.employees(include_inactive=self.chk_show_inactive.isChecked())
        self._rows = rows
        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            fte = ("1/1" if row["fte_num"] == row["fte_den"]
                   else f"{row['fte_num']}/{row['fte_den']}")
            values = [
                row["last_name"], row["first_name"], row["position"], fte,
                row["hired_on"] or "", row["ended_on"] or "",
                "tak" if row["active"] else "nie", row["notes"],
            ]
            for c, val in enumerate(values):
                item = QTableWidgetItem(str(val))
                if not row["active"]:
                    item.setForeground(Qt.GlobalColor.gray)
                self.table.setItem(r, c, item)

    def _selected_row(self):
        r = self.table.currentRow()
        return self._rows[r] if 0 <= r < len(self._rows) else None

    def add_employee(self) -> None:
        dlg = EmployeeDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        vals = dlg.values()
        emp_id = self.db.add_employee(
            vals["last_name"], vals["first_name"], vals["position"],
            vals["fte_num"], vals["fte_den"], vals["hired_on"],
        )
        self.db.update_employee(emp_id, **vals)
        self.reload()
        self._notify()

    def edit_employee(self) -> None:
        row = self._selected_row()
        if row is None:
            return
        dlg = EmployeeDialog(self, row)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        self.db.update_employee(row["id"], **dlg.values())
        self.reload()
        self._notify()

    def deactivate_employee(self) -> None:
        row = self._selected_row()
        if row is None:
            return
        name = f"{row['last_name']} {row['first_name']}".strip()
        answer = QMessageBox.question(
            self, "Zakończenie pracy",
            f"Oznaczyć „{name}” jako osobę, która już nie pracuje?\n\n"
            "Zniknie z nowych grafików, ale wszystkie dotychczasowe wpisy zostaną zachowane.",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.db.deactivate_employee(row["id"], dt.date.today().isoformat())
        self.reload()
        self._notify()

    def delete_employee(self) -> None:
        row = self._selected_row()
        if row is None:
            return
        name = f"{row['last_name']} {row['first_name']}".strip()
        count = self.db.conn.execute(
            "SELECT COUNT(*) AS n FROM entries WHERE employee_id=?", (row["id"],)
        ).fetchone()["n"]
        answer = QMessageBox.warning(
            self, "Trwałe usunięcie",
            f"Usunąć „{name}” wraz z {count} wpisami we wszystkich grafikach?\n\n"
            "Tej operacji nie można cofnąć. Zwykle lepszym wyborem jest „Zakończ pracę”.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.db.delete_employee(row["id"])
        self.reload()
        self._notify()

    def move_employee(self, delta: int) -> None:
        r = self.table.currentRow()
        if r < 0 or not (0 <= r + delta < len(self._rows)):
            return
        ids = [row["id"] for row in self._rows]
        ids[r], ids[r + delta] = ids[r + delta], ids[r]
        self.db.reorder_employees(ids)
        self.reload()
        self.table.selectRow(r + delta)
        self._notify()

    def _notify(self) -> None:
        if self.on_change:
            self.on_change()
