"""Ustawienia aplikacji."""
from __future__ import annotations

from PySide6.QtCore import Qt

from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QGroupBox,
    QHBoxLayout, QInputDialog, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QMessageBox, QPushButton, QVBoxLayout,
)

from app.core.calendar_pl import NORM_MEDICAL_MINUTES, NORM_STANDARD_MINUTES

NORM_CHOICES = [
    ("7 godz. 35 min — personel medyczny", NORM_MEDICAL_MINUTES),
    ("8 godz. — norma podstawowa", NORM_STANDARD_MINUTES),
]


class SettingsDialog(QDialog):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Ustawienia")
        self.setMinimumWidth(420)

        self.ed_ward = QLineEdit(db.get_setting("ward_name", ""))
        self.ed_ward.setPlaceholderText("np. Oddział Wewnętrzny")

        self.cmb_norm = QComboBox()
        current = int(db.get_setting("daily_norm_minutes", str(NORM_MEDICAL_MINUTES)))
        for label, minutes in NORM_CHOICES:
            self.cmb_norm.addItem(label, minutes)
        for i in range(self.cmb_norm.count()):
            if self.cmb_norm.itemData(i) == current:
                self.cmb_norm.setCurrentIndex(i)
                break

        self.ed_repo = QLineEdit(db.get_setting("update_repo", ""))
        self.ed_repo.setPlaceholderText("np. nazwa-uzytkownika/grafik")
        self.chk_updates = QCheckBox("Sprawdzaj aktualizacje przy uruchomieniu")
        self.chk_updates.setChecked(db.get_setting("update_check_enabled", "1") != "0")

        form = QFormLayout()
        form.addRow("Nazwa oddziału", self.ed_ward)
        form.addRow("Dobowa norma czasu pracy", self.cmb_norm)
        form.addRow("Adres aktualizacji", self.ed_repo)
        form.addRow("", self.chk_updates)

        self.floors_box = self._build_floors_box()

        hint = QLabel(
            "Norma dobowa służy do wyliczenia miesięcznego wymiaru czasu pracy "
            "oraz nadgodzin; pozostałe reguły znajdziesz na zakładce Zasady. "
            "Adres aktualizacji to nazwa repozytorium, w którym publikowane są "
            "nowe wersje programu — zostaw puste, jeśli aktualizacje mają być "
            "wyłączone."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#555;")

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Zapisz")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Anuluj")
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(hint)
        layout.addWidget(self.floors_box)
        layout.addWidget(buttons)

    def _build_floors_box(self) -> QGroupBox:
        box = QGroupBox("Piętra")
        self.list_floors = QListWidget()
        self.list_floors.setMaximumHeight(110)
        self._reload_floors()

        buttons = QHBoxLayout()
        for text, slot in (
            ("Dodaj", self._add_floor),
            ("Zmień nazwę", self._rename_floor),
            ("Usuń", self._delete_floor),
        ):
            btn = QPushButton(text)
            btn.clicked.connect(slot)
            buttons.addWidget(btn)
        buttons.addStretch(1)

        note = QLabel(
            "Każde piętro ma własny grafik i własny skład. Pracownik z jednego "
            "piętra może mieć wpisany dyżur na drugim — to zastępstwo, a jego "
            "godziny i tak liczą się do jego miesięcznego wymiaru."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color:#555;")

        layout = QVBoxLayout(box)
        layout.addWidget(self.list_floors)
        layout.addLayout(buttons)
        layout.addWidget(note)
        return box

    def _reload_floors(self) -> None:
        self.list_floors.clear()
        for floor in self.db.floors():
            item = QListWidgetItem(floor["name"])
            item.setData(Qt.ItemDataRole.UserRole, floor["id"])
            self.list_floors.addItem(item)

    def _selected_floor(self):
        item = self.list_floors.currentItem()
        return (item.data(Qt.ItemDataRole.UserRole), item.text()) if item else (None, "")

    def _add_floor(self) -> None:
        name, ok = QInputDialog.getText(self, "Nowe piętro", "Nazwa:")
        if ok and name.strip():
            self.db.add_floor(name.strip())
            self._reload_floors()

    def _rename_floor(self) -> None:
        floor_id, current = self._selected_floor()
        if floor_id is None:
            return
        name, ok = QInputDialog.getText(
            self, "Zmiana nazwy", "Nazwa:", text=current
        )
        if ok and name.strip():
            self.db.rename_floor(floor_id, name.strip())
            self._reload_floors()

    def _delete_floor(self) -> None:
        floor_id, name = self._selected_floor()
        if floor_id is None:
            return
        if self.list_floors.count() <= 1:
            QMessageBox.information(
                self, "Piętra", "Musi zostać przynajmniej jedno piętro."
            )
            return
        staff = len(self.db.employees(include_inactive=True, floor_id=floor_id))
        answer = QMessageBox.warning(
            self, "Usunięcie piętra",
            f"Usunąć piętro „{name}”?\n\n"
            f"Przypisanych pracowników: {staff}. Ich dane i dyżury zostaną "
            "zachowane, ale trzeba będzie przypisać ich do innego piętra.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.db.delete_floor(floor_id)
        self._reload_floors()

    def _save(self) -> None:
        repo = self.ed_repo.text().strip().strip("/")
        if repo and repo.count("/") != 1:
            QMessageBox.warning(
                self, "Adres aktualizacji",
                "Adres podaje się w postaci nazwa-uzytkownika/nazwa-repozytorium, "
                "np. kowalski/grafik.",
            )
            return
        self.db.set_setting("ward_name", self.ed_ward.text().strip())
        self.db.set_setting("daily_norm_minutes", str(self.cmb_norm.currentData()))
        self.db.set_setting("update_repo", repo)
        self.db.set_setting(
            "update_check_enabled", "1" if self.chk_updates.isChecked() else "0"
        )
        self.accept()
