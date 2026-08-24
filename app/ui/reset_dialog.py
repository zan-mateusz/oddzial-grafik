"""Okno usuwania danych — po testach albo przed oddaniem programu do użytku."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QPushButton, QRadioButton, QVBoxLayout,
)


class ResetDialog(QDialog):
    """Wybór zakresu czyszczenia. Kopia zapasowa powstaje zawsze."""

    KEEP_PEOPLE = "grafiki"
    EVERYTHING = "wszystko"

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Usunięcie danych")
        self.setMinimumWidth(500)

        counts = db.data_summary()
        summary = QLabel(
            f"W programie jest teraz: <b>{counts['employees']}</b> pracowników, "
            f"<b>{counts['entries']}</b> wpisów w grafikach "
            f"z <b>{counts['months']}</b> miesięcy."
        )
        summary.setTextFormat(Qt.TextFormat.RichText)
        summary.setWordWrap(True)

        self.opt_rotas = QRadioButton(
            "Usuń tylko grafiki — pracownicy, piętra i ustawienia zostają"
        )
        self.opt_rotas.setChecked(True)
        self.opt_all = QRadioButton(
            "Usuń wszystko — program wróci do stanu jak zaraz po instalacji"
        )

        hint = QLabel(
            "Przed usunięciem program zapisze kopię zapasową wszystkich danych, "
            "więc operację da się cofnąć przez <b>Plik → Przywróć z kopii</b>."
        )
        hint.setTextFormat(Qt.TextFormat.RichText)
        hint.setWordWrap(True)
        hint.setStyleSheet(
            "color:#3F4753; background:#F4F6F9; border:1px solid #DDE2E8;"
            "border-radius:4px; padding:8px;"
        )

        warn = QLabel(
            "Tej operacji nie da się cofnąć inaczej niż z kopii zapasowej."
        )
        warn.setWordWrap(True)
        warn.setStyleSheet("color:#B00020; font-weight:600;")

        buttons = QHBoxLayout()
        btn_cancel = QPushButton("Anuluj")
        btn_cancel.setDefault(True)
        btn_cancel.clicked.connect(self.reject)
        self.btn_ok = QPushButton("Usuń dane")
        self.btn_ok.clicked.connect(self.accept)
        buttons.addStretch(1)
        buttons.addWidget(btn_cancel)
        buttons.addWidget(self.btn_ok)

        layout = QVBoxLayout(self)
        layout.addWidget(summary)
        layout.addSpacing(6)
        layout.addWidget(self.opt_rotas)
        layout.addWidget(self.opt_all)
        layout.addSpacing(6)
        layout.addWidget(hint)
        layout.addWidget(warn)
        layout.addLayout(buttons)

    def scope(self) -> str:
        return self.EVERYTHING if self.opt_all.isChecked() else self.KEEP_PEOPLE
