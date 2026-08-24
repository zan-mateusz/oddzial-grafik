"""Ustawienia aplikacji."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLabel, QLineEdit,
    QVBoxLayout,
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

        form = QFormLayout()
        form.addRow("Nazwa oddziału", self.ed_ward)
        form.addRow("Dobowa norma czasu pracy", self.cmb_norm)

        hint = QLabel(
            "Norma dobowa służy do wyliczenia miesięcznego wymiaru czasu pracy "
            "oraz nadgodzin. Dla pielęgniarek i pozostałego personelu medycznego "
            "wynosi 7 godz. 35 min."
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
        layout.addWidget(buttons)

    def _save(self) -> None:
        self.db.set_setting("ward_name", self.ed_ward.text().strip())
        self.db.set_setting("daily_norm_minutes", str(self.cmb_norm.currentData()))
        self.accept()
