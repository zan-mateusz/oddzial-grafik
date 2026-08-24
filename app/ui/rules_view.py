"""Zakładka: zasady rozliczania czasu pracy."""
from __future__ import annotations

import datetime as dt

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFormLayout, QFrame, QGroupBox, QHBoxLayout, QLabel,
    QMessageBox, QPushButton, QScrollArea, QSpinBox, QTimeEdit, QVBoxLayout,
    QWidget,
)

from app.core.calendar_pl import PL_MONTHS_TITLE, month_norm
from app.core.rules import (
    LEGAL_NOTES, NORM_PRESETS, Rules, load_rules, save_rules,
    validate_night_window,
)
from app.core.shifts import fmt_minutes


def _note(key: str) -> QLabel:
    """Wyjaśnienie z podstawą prawną pod danym ustawieniem."""
    title, text = LEGAL_NOTES[key]
    label = QLabel(f"<b>{title}.</b> {text}")
    label.setWordWrap(True)
    label.setTextFormat(Qt.TextFormat.RichText)
    label.setStyleSheet(
        "color:#3F4753; background:#F4F6F9; border:1px solid #DDE2E8;"
        "border-radius:4px; padding:7px;"
    )
    return label


class RulesView(QWidget):
    """Pokazuje i pozwala zmienić reguły, według których liczone są godziny."""

    def __init__(self, db, on_change=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.on_change = on_change
        self._build_ui()
        self.reload()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        inner = QWidget()
        root = QVBoxLayout(inner)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(12)

        intro = QLabel(
            "Tu ustalasz, według jakich reguł program przelicza wpisy z grafiku "
            "na godziny. Wartości domyślne odpowiadają przepisom dla personelu "
            "medycznego. Zmiany działają od razu na wszystkich grafikach — "
            "także tych z przeszłości."
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        root.addWidget(self._build_norm_box())
        root.addWidget(self._build_night_box())
        root.addWidget(self._build_leave_box())
        root.addWidget(self._build_preview_box())
        root.addStretch(1)

        scroll.setWidget(inner)
        outer.addWidget(scroll)

        bar = QHBoxLayout()
        bar.setContentsMargins(14, 0, 14, 10)
        self.btn_defaults = QPushButton("Przywróć domyślne")
        self.btn_defaults.clicked.connect(self._restore_defaults)
        self.btn_save = QPushButton("Zapisz zasady")
        self.btn_save.setDefault(True)
        self.btn_save.clicked.connect(self._save)
        bar.addWidget(self.btn_defaults)
        bar.addStretch(1)
        bar.addWidget(self.btn_save)
        outer.addLayout(bar)

    # --- sekcje -------------------------------------------------------------

    def _build_norm_box(self) -> QGroupBox:
        box = QGroupBox("Wymiar czasu pracy")
        form = QFormLayout()

        self.cmb_norm = QComboBox()
        for label, minutes in NORM_PRESETS:
            self.cmb_norm.addItem(label, minutes)
        self.cmb_norm.addItem("inna — podaj poniżej", None)
        self.cmb_norm.currentIndexChanged.connect(self._on_norm_choice)

        self.spin_norm_h = QSpinBox()
        self.spin_norm_h.setRange(1, 24)
        self.spin_norm_h.setSuffix(" godz.")
        self.spin_norm_m = QSpinBox()
        self.spin_norm_m.setRange(0, 59)
        self.spin_norm_m.setSuffix(" min")
        custom = QHBoxLayout()
        custom.addWidget(self.spin_norm_h)
        custom.addWidget(self.spin_norm_m)
        custom.addStretch(1)
        custom_wrap = QWidget()
        custom_wrap.setLayout(custom)

        for widget in (self.spin_norm_h, self.spin_norm_m):
            widget.valueChanged.connect(self._refresh_preview)

        form.addRow("Norma dobowa", self.cmb_norm)
        form.addRow("Wartość własna", custom_wrap)

        layout = QVBoxLayout(box)
        layout.addLayout(form)
        layout.addWidget(_note("daily_norm"))
        layout.addWidget(_note("month_norm"))
        return box

    def _build_night_box(self) -> QGroupBox:
        box = QGroupBox("Pora nocna")
        form = QFormLayout()

        self.time_night_start = QTimeEdit()
        self.time_night_start.setDisplayFormat("HH:mm")
        self.time_night_end = QTimeEdit()
        self.time_night_end.setDisplayFormat("HH:mm")
        self.time_night_end.setEnabled(False)
        self.time_night_end.setToolTip(
            "Wyliczane automatycznie — pora nocna trwa dokładnie 8 godzin."
        )
        self.time_night_start.timeChanged.connect(self._on_night_start)

        form.addRow("Od godziny", self.time_night_start)
        form.addRow("Do godziny", self.time_night_end)

        self.lbl_night_example = QLabel()
        self.lbl_night_example.setWordWrap(True)
        self.lbl_night_example.setStyleSheet("color:#3F4753;")

        layout = QVBoxLayout(box)
        layout.addLayout(form)
        layout.addWidget(self.lbl_night_example)
        layout.addWidget(_note("night"))
        return box

    def _build_leave_box(self) -> QGroupBox:
        box = QGroupBox("Urlopy i nieobecności")

        self.chk_leave_working_days = QCheckBox(
            "Urlop zużywa się tylko w dni pracy (pon.–pt., poza świętami)"
        )
        self.chk_leave_working_days.stateChanged.connect(self._refresh_preview)

        self.chk_leave_norm = QCheckBox("Urlop obniża wymiar czasu pracy")
        self.chk_sick_norm = QCheckBox("Zwolnienie lekarskie obniża wymiar czasu pracy")
        for widget in (self.chk_leave_norm, self.chk_sick_norm):
            widget.stateChanged.connect(self._refresh_preview)

        layout = QVBoxLayout(box)
        layout.addWidget(self.chk_leave_working_days)
        layout.addWidget(_note("leave"))
        layout.addWidget(self.chk_leave_norm)
        layout.addWidget(self.chk_sick_norm)
        layout.addWidget(_note("absence"))
        layout.addWidget(_note("holiday"))
        return box

    def _build_preview_box(self) -> QGroupBox:
        box = QGroupBox("Podgląd")
        self.lbl_preview = QLabel()
        self.lbl_preview.setWordWrap(True)
        self.lbl_preview.setTextFormat(Qt.TextFormat.RichText)
        layout = QVBoxLayout(box)
        layout.addWidget(self.lbl_preview)
        return box

    # --- stan ---------------------------------------------------------------

    def reload(self) -> None:
        self._apply(load_rules(self.db))

    def _apply(self, rules: Rules) -> None:
        self._loading = True
        index = self.cmb_norm.findData(rules.daily_norm_minutes)
        self.cmb_norm.setCurrentIndex(index if index >= 0 else self.cmb_norm.count() - 1)
        self.spin_norm_h.setValue(rules.daily_norm_minutes // 60)
        self.spin_norm_m.setValue(rules.daily_norm_minutes % 60)
        self.time_night_start.setTime(rules.night_start)
        self.time_night_end.setTime(rules.night_end)
        self.chk_leave_working_days.setChecked(rules.leave_on_working_days_only)
        self.chk_leave_norm.setChecked(rules.leave_reduces_norm)
        self.chk_sick_norm.setChecked(rules.sick_reduces_norm)
        self._loading = False
        self._on_norm_choice()

    def _on_norm_choice(self) -> None:
        preset = self.cmb_norm.currentData()
        custom = preset is None
        self.spin_norm_h.setEnabled(custom)
        self.spin_norm_m.setEnabled(custom)
        if not custom and not getattr(self, "_loading", False):
            self.spin_norm_h.blockSignals(True)
            self.spin_norm_m.blockSignals(True)
            self.spin_norm_h.setValue(preset // 60)
            self.spin_norm_m.setValue(preset % 60)
            self.spin_norm_h.blockSignals(False)
            self.spin_norm_m.blockSignals(False)
        self._refresh_preview()

    def _on_night_start(self) -> None:
        start = self.time_night_start.time().toPython()
        self.time_night_end.setTime(Rules().with_night_window(start).night_end)
        self._refresh_preview()

    def current_rules(self) -> Rules:
        minutes = self.spin_norm_h.value() * 60 + self.spin_norm_m.value()
        rules = Rules(
            daily_norm_minutes=minutes,
            leave_on_working_days_only=self.chk_leave_working_days.isChecked(),
            leave_reduces_norm=self.chk_leave_norm.isChecked(),
            sick_reduces_norm=self.chk_sick_norm.isChecked(),
        )
        return rules.with_night_window(self.time_night_start.time().toPython())

    def _refresh_preview(self) -> None:
        if getattr(self, "_loading", False):
            return
        rules = self.current_rules()
        today = dt.date.today()
        norm = month_norm(today.year, today.month, rules.daily_norm_minutes)
        window = (f"{rules.night_start.strftime('%H:%M')}–"
                  f"{rules.night_end.strftime('%H:%M')}")

        from app.core.stats import night_minutes
        night_on_shift = night_minutes(dt.time(19, 0), dt.time(7, 0), rules)
        self.lbl_night_example.setText(
            f"Dyżur nocny 19:00–7:00 daje przy tym ustawieniu "
            f"<b>{fmt_minutes(night_on_shift)}</b> godzin pory nocnej."
        )

        leave_rule = (
            "tylko w dni pracy" if rules.leave_on_working_days_only
            else "w każdy dzień kalendarzowy"
        )
        self.lbl_preview.setText(
            f"Norma dobowa: <b>{fmt_minutes(rules.daily_norm_minutes)}</b><br>"
            f"Wymiar na {PL_MONTHS_TITLE[today.month - 1].lower()} {today.year}: "
            f"<b>{fmt_minutes(norm.minutes)}</b> ({norm.working_days} dni roboczych, "
            f"świąt obniżających wymiar: {norm.holidays_reducing})<br>"
            f"Pora nocna: <b>{window}</b><br>"
            f"Urlop liczony {leave_rule}; jeden dzień to "
            f"<b>{fmt_minutes(rules.leave_minutes)}</b>"
        )

    # --- zapis --------------------------------------------------------------

    def _save(self) -> None:
        rules = self.current_rules()
        error = validate_night_window(rules.night_start, rules.night_end)
        if error:
            QMessageBox.warning(self, "Pora nocna", error)
            return
        if rules.daily_norm_minutes <= 0:
            QMessageBox.warning(
                self, "Norma dobowa", "Norma dobowa musi być większa od zera."
            )
            return
        save_rules(self.db, rules)
        if self.on_change:
            self.on_change()
        QMessageBox.information(
            self, "Zapisano",
            "Zasady zostały zapisane. Podsumowania w grafikach zostały "
            "przeliczone od nowa.",
        )

    def _restore_defaults(self) -> None:
        answer = QMessageBox.question(
            self, "Domyślne zasady",
            "Przywrócić ustawienia zgodne z przepisami dla personelu "
            "medycznego?\n\nNorma dobowa 7 godz. 35 min, pora nocna 22:00–6:00, "
            "urlop liczony tylko w dni pracy.",
        )
        if answer == QMessageBox.StandardButton.Yes:
            self._apply(Rules())
            self._refresh_preview()
