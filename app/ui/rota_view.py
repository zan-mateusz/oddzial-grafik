"""Zakładka z grafikiem miesięcznym."""
from __future__ import annotations

import datetime as dt

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QBrush, QColor, QFont, QKeySequence
from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QHBoxLayout,
    QHeaderView, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMenu,
    QMessageBox, QPushButton, QSpinBox, QTableView, QToolButton, QVBoxLayout,
    QWidget,
)

from app.core.calendar_pl import PL_MONTHS_TITLE, day_kind, month_norm
from app.core.shifts import fmt_minutes
from app.core.stats import daily_coverage
from app.ui.delegates import ShiftCellDelegate
from app.ui.rota_model import RotaModel

DAY_COL_MIN = 26
DAY_COL_MAX = 44
SUMMARY_COL_WIDTH = 82
NARROW_SUMMARY = {"wymiar", "bilans", "kwartal"}
NARROW_COL_WIDTH = 64
NAME_COL_WIDTH = 186


COMBINED_LABEL = "Wszystkie piętra"


class AddToRotaDialog(QDialog):
    """Wybór osób, które mają się pojawić w grafiku tego piętra."""

    def __init__(self, candidates, floor_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Dodaj do grafiku")
        self.setMinimumWidth(430)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Szukaj nazwiska…")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self._filter)

        self.list = QListWidget()
        self.list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        for emp in candidates:
            name = f"{emp['last_name']} {emp['first_name']}".strip()
            if emp["position"]:
                name += f" — {emp['position']}"
            item = QListWidgetItem(name)
            item.setData(Qt.ItemDataRole.UserRole, emp["id"])
            self.list.addItem(item)
        self.list.itemDoubleClicked.connect(lambda _: self.accept())

        hint = QLabel(
            f"Wybrane osoby pojawią się w grafiku piętra {floor_name} — także "
            "zanim dostaną pierwszy dyżur. Można zaznaczyć kilka naraz."
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
        layout.addWidget(self.search)
        layout.addWidget(self.list)
        layout.addWidget(hint)
        layout.addWidget(buttons)

    def _filter(self, text: str) -> None:
        needle = text.strip().lower()
        for row in range(self.list.count()):
            item = self.list.item(row)
            item.setHidden(bool(needle) and needle not in item.text().lower())

    def selected_ids(self) -> list[int]:
        return [i.data(Qt.ItemDataRole.UserRole) for i in self.list.selectedItems()]


class RemoveFromRotaDialog(QDialog):
    """Zdjęcie osób ze składu piętra — pojedynczo albo kilku naraz."""

    def __init__(self, employees, shift_counts, floor_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Usuń z grafiku")
        self.setMinimumWidth(450)
        self._counts = shift_counts

        self.list = QListWidget()
        for emp in employees:
            name = f"{emp['last_name']} {emp['first_name']}".strip()
            shifts = shift_counts.get(emp["id"], 0)
            if shifts:
                name += f"  — {shifts} dyż."
            item = QListWidgetItem(name)
            item.setData(Qt.ItemDataRole.UserRole, emp["id"])
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            if shifts:
                item.setForeground(QBrush(QColor("#B45309")))
            self.list.addItem(item)
        self.list.itemChanged.connect(lambda _: self._refresh_summary())

        buttons_row = QHBoxLayout()
        btn_all = QPushButton("Zaznacz wszystkich")
        btn_all.clicked.connect(lambda: self._set_all(Qt.CheckState.Checked))
        btn_none = QPushButton("Odznacz wszystkich")
        btn_none.clicked.connect(lambda: self._set_all(Qt.CheckState.Unchecked))
        buttons_row.addWidget(btn_all)
        buttons_row.addWidget(btn_none)
        buttons_row.addStretch(1)

        self.lbl_summary = QLabel()
        self.lbl_summary.setWordWrap(True)

        hint = QLabel(
            f"Zaznaczone osoby znikną z grafiku piętra {floor_name}. "
            "Pozostaną w programie i w grafikach innych miesięcy."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#555;")

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Usuń")
        self.buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Anuluj")
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(self.list)
        layout.addLayout(buttons_row)
        layout.addWidget(self.lbl_summary)
        layout.addWidget(hint)
        layout.addWidget(self.buttons)
        self._refresh_summary()

    def _set_all(self, state) -> None:
        for row in range(self.list.count()):
            self.list.item(row).setCheckState(state)

    def _checked_items(self):
        return [
            self.list.item(row) for row in range(self.list.count())
            if self.list.item(row).checkState() == Qt.CheckState.Checked
        ]

    def selected_ids(self) -> list[int]:
        return [i.data(Qt.ItemDataRole.UserRole) for i in self._checked_items()]

    def selected_shift_count(self) -> int:
        return sum(self._counts.get(i, 0) for i in self.selected_ids())

    def _refresh_summary(self) -> None:
        chosen = self.selected_ids()
        shifts = self.selected_shift_count()
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
            bool(chosen)
        )
        if not chosen:
            self.lbl_summary.setText("")
            return
        text = f"Zaznaczono osób: <b>{len(chosen)}</b>."
        if shifts:
            text += (f" <span style='color:#B00020'>Razem z nimi zostanie "
                     f"usuniętych <b>{shifts}</b> wpisanych dyżurów.</span>")
        self.lbl_summary.setText(text)


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
        self.model.hide_without_shifts = (
            db.get_setting("hide_rows_without_shifts", "0") == "1"
        )
        self.model.reload()
        self.model.entryChanged.connect(self._on_edited)

        self._build_ui()
        self.chk_hide_empty.setChecked(self.model.hide_without_shifts)
        self._apply_month_to_controls()
        self._refresh_palette()
        self._refresh_footer()

    # --- budowa interfejsu --------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 8, 10, 8)
        root.setSpacing(6)

        # Pasek kodów zmian musi istnieć przed budową paska narzędzi — ten
        # ustawia stan edycji, który obejmuje także przyciski kodów.
        self.palette_bar = QHBoxLayout()
        self.palette_bar.setSpacing(4)

        root.addLayout(self._build_toolbar())
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
        vh.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        vh.customContextMenuRequested.connect(self._show_employee_menu)
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        hh.setFixedHeight(38)
        root.addWidget(self.table, 1)

        # Pusty miesiąc to stan normalny — podpowiadamy, jak go wypełnić,
        # zamiast pokazywać samą pustą siatkę.
        self.empty_hint = self._build_empty_hint()

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

    def _build_empty_hint(self) -> QWidget:
        panel = QWidget(self.table.viewport())
        panel.setAutoFillBackground(True)
        panel.setStyleSheet(
            "QWidget#pustyGrafik { background: #FFFFFF; border: 1px solid #D3D8DF;"
            " border-radius: 8px; }"
        )
        panel.setObjectName("pustyGrafik")

        self.hint_title = QLabel("Ten grafik jest jeszcze pusty")
        font = QFont()
        font.setPointSize(13)
        font.setBold(True)
        self.hint_title.setFont(font)
        self.hint_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.hint_subtitle = QLabel("Wybierz, od czego zacząć:")
        self.hint_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hint_subtitle.setStyleSheet("color:#555;")

        # Osobny przycisk na wypadek, gdy tabela jest pusta tylko dlatego,
        # że wszystkie osoby zostały ukryte.
        self.btn_show_hidden = QPushButton("Pokaż osoby bez dyżurów")
        self.btn_show_hidden.clicked.connect(
            lambda: self.chk_hide_empty.setChecked(False)
        )
        self.btn_show_hidden.hide()

        actions = QHBoxLayout()
        actions.addStretch(1)
        for text, slot in (
            ("Skład z poprzedniego miesiąca", self._copy_previous_team),
            ("Dodaj pracowników…", self._add_to_rota),
            ("Wczytaj z pliku…", self._request_import),
        ):
            button = QPushButton(text)
            button.clicked.connect(slot)
            actions.addWidget(button)
        actions.addStretch(1)

        self.hint_actions = QWidget()
        self.hint_actions.setLayout(actions)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(24, 18, 24, 18)
        layout.addWidget(self.hint_title)
        layout.addWidget(self.hint_subtitle)
        layout.addSpacing(8)
        layout.addWidget(self.hint_actions)
        layout.addWidget(self.btn_show_hidden)
        panel.hide()
        return panel

    def _request_import(self) -> None:
        """Import obsługuje okno główne — stąd tylko prośba."""
        window = self.window()
        if hasattr(window, "import_xlsx"):
            window.import_xlsx()

    def _update_empty_hint(self) -> None:
        empty = self.model.rowCount() == 0 and self.floor_id is not None
        self.empty_hint.setVisible(empty)
        if not empty:
            return

        hidden = self.model.hidden_count
        if hidden:
            # Tabela jest pusta wyłącznie przez ukrycie — mówimy o tym wprost,
            # zamiast pokazywać pustą siatkę i propozycję dodania ludzi.
            self.hint_title.setText(
                f"Wszystkie osoby w składzie ({hidden}) nie mają jeszcze dyżurów"
            )
            self.hint_subtitle.setText("Są ukryte, bo włączono „Ukryj bez dyżurów”.")
            self.hint_actions.hide()
            self.btn_show_hidden.show()
        else:
            self.hint_title.setText("Ten grafik jest jeszcze pusty")
            self.hint_subtitle.setText("Wybierz, od czego zacząć:")
            self.hint_actions.show()
            self.btn_show_hidden.hide()
        self._centre_empty_hint()

    def _centre_empty_hint(self) -> None:
        viewport = self.table.viewport()
        hint = self.empty_hint
        hint.adjustSize()
        size = hint.sizeHint()
        hint.move(
            max(0, (viewport.width() - size.width()) // 2),
            max(0, (viewport.height() - size.height()) // 3),
        )

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

        self.btn_add = QPushButton("Dodaj do grafiku…")
        self.btn_add.setToolTip(
            "Dopisz osobę do grafiku tego piętra, zanim dostanie pierwszy dyżur"
        )
        self.btn_add.clicked.connect(self._add_to_rota)

        self.btn_remove = QPushButton("Usuń z grafiku…")
        self.btn_remove.setToolTip(
            "Zdejmij osoby ze składu tego piętra — można zaznaczyć kilka naraz"
        )
        self.btn_remove.clicked.connect(self._remove_from_rota_dialog)

        self.chk_hide_empty = QCheckBox("Ukryj bez dyżurów")
        self.chk_hide_empty.setToolTip(
            "Chowa osoby, które są w składzie, ale nie mają jeszcze "
            "przydzielonego żadnego dyżuru"
        )
        self.chk_hide_empty.stateChanged.connect(self._on_hide_toggled)

        self.btn_copy_team = QPushButton("Skład z poprzedniego miesiąca")
        self.btn_copy_team.setToolTip(
            "Przenieś do tego grafiku te same osoby co miesiąc wcześniej, "
            "bez ich dyżurów"
        )
        self.btn_copy_team.clicked.connect(self._copy_previous_team)

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
        bar.addWidget(self.btn_add)
        bar.addWidget(self.btn_remove)
        bar.addWidget(self.btn_copy_team)
        bar.addWidget(self.chk_hide_empty)
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
        self._update_editing_state()

    def _selected_cells(self) -> list[tuple[int, int]]:
        return [
            (i.row(), i.column())
            for i in self.table.selectionModel().selectedIndexes()
            if not self.model.is_summary_column(i.column())
        ]

    def _fill_selection(self, code: str) -> None:
        if self.floor_id is None:
            return
        cells = self._selected_cells()
        if cells:
            self.model.set_range(cells, code)

    def _show_employee_menu(self, pos) -> None:
        """Menu przy nazwisku — usunięcie osoby ze składu tego piętra."""
        if self.floor_id is None:
            return
        row = self.table.verticalHeader().logicalIndexAt(pos)
        emp = self.model.employee_at(row)
        if emp is None:
            return
        name = f"{emp['last_name']} {emp['first_name']}".strip()
        menu = QMenu(self)
        action = menu.addAction(f"Usuń z grafiku tego piętra: {name}")
        action.triggered.connect(lambda: self._remove_from_rota(row))
        menu.exec(self.table.verticalHeader().mapToGlobal(pos))

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
        if len(floors) > 1:
            # Widok łączny pokazuje wszystkie piętra naraz, bez możliwości edycji.
            self.cmb_floor.addItem(COMBINED_LABEL, None)
        index = self.cmb_floor.findData(self.floor_id)
        if index >= 0:
            self.cmb_floor.setCurrentIndex(index)
        self.cmb_floor.blockSignals(False)
        multi = len(floors) > 1
        self.cmb_floor.setVisible(multi)
        self._update_editing_state()

    def _on_floor_changed(self) -> None:
        floor_id = self.cmb_floor.currentData()
        if floor_id == self.floor_id and self.cmb_floor.currentIndex() >= 0:
            return
        self.floor_id = floor_id
        self.model.set_floor(floor_id)
        self._update_editing_state()
        self._resize_columns()
        self._refresh_footer()

    def _update_editing_state(self) -> None:
        """W widoku łącznym grafik jest tylko do oglądania."""
        combined = self.floor_id is None
        for button in (self.btn_add, self.btn_remove, self.btn_copy_team):
            button.setEnabled(not combined)
        for i in range(self.palette_bar.count()):
            widget = self.palette_bar.itemAt(i).widget()
            if isinstance(widget, QToolButton):
                widget.setEnabled(not combined)

    def _add_to_rota(self) -> None:
        """Dopisuje osoby do składu tego piętra na ten miesiąc."""
        if self.floor_id is None:
            return
        shown = {e["id"] for e in self.model.employees}
        candidates = [
            e for e in self.db.employees_for_month(self.model.year, self.model.month)
            if e["id"] not in shown
        ]
        if not candidates:
            QMessageBox.information(
                self, "Dodaj do grafiku",
                "Wszyscy pracownicy są już w grafiku tego piętra.\n\n"
                "Nowe osoby dodasz na zakładce Pracownicy.",
            )
            return
        dialog = AddToRotaDialog(
            candidates, self.db.floor_name(self.floor_id) or "", self
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        chosen = dialog.selected_ids()
        if not chosen:
            return
        self.db.add_to_roster(
            self.model.year, self.model.month, self.floor_id, chosen
        )
        self.model.reload()
        self._resize_columns()
        self._refresh_footer()

    def _on_hide_toggled(self) -> None:
        hide = self.chk_hide_empty.isChecked()
        self.db.set_setting("hide_rows_without_shifts", "1" if hide else "0")
        self.model.set_hide_without_shifts(hide)
        self._resize_columns()
        self._refresh_footer()

    def _previous_month(self) -> tuple[int, int]:
        year, month = self.model.year, self.model.month
        return (year - 1, 12) if month == 1 else (year, month - 1)

    def _copy_previous_team(self) -> None:
        """Przenosi skład piętra z poprzedniego miesiąca — bez dyżurów."""
        if self.floor_id is None:
            return
        source = self._previous_month()
        added = self.db.copy_roster(
            source, (self.model.year, self.model.month), self.floor_id
        )
        month_name = PL_MONTHS_TITLE[source[1] - 1].lower()
        if not added:
            QMessageBox.information(
                self, "Skład z poprzedniego miesiąca",
                f"Nie ma kogo przenieść z {month_name} {source[0]} — grafik "
                "tego piętra był wtedy pusty albo wszystkie te osoby są już "
                "w składzie.",
            )
            return
        self.model.reload()
        self._resize_columns()
        self._refresh_footer()
        self.statusBar_message(
            f"Przeniesiono {added} osób ze składu z {month_name} {source[0]}"
        )

    def statusBar_message(self, text: str) -> None:
        window = self.window()
        if hasattr(window, "statusBar"):
            window.statusBar().showMessage(text, 5000)

    def _remove_from_rota_dialog(self) -> None:
        """Zdejmuje ze składu wybrane osoby — pojedynczo albo kilka naraz."""
        if self.floor_id is None:
            return
        employees = list(self.model.employees)
        if not employees:
            QMessageBox.information(
                self, "Usuń z grafiku", "Grafik tego piętra jest pusty."
            )
            return
        counts = self.db.shift_counts_on_floor(
            self.model.year, self.model.month, self.floor_id
        )
        dialog = RemoveFromRotaDialog(
            employees, counts, self.db.floor_name(self.floor_id) or "", self
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        chosen = dialog.selected_ids()
        if not chosen:
            return

        shifts = dialog.selected_shift_count()
        if shifts:
            answer = QMessageBox.warning(
                self, "Usunięcie wraz z dyżurami",
                f"Zaznaczone osoby mają na tym piętrze {shifts} wpisanych "
                "dyżurów. Zostaną one usunięte razem z nimi.\n\n"
                "Dyżury na innych piętrach pozostaną nietknięte. Kontynuować?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return

        self.db.remove_from_rota(
            self.model.year, self.model.month, self.floor_id, chosen,
            drop_shifts=bool(shifts),
        )
        self.model.reload()
        self._resize_columns()
        self._refresh_footer()
        self.dataEdited.emit()

    def _remove_from_rota(self, row: int) -> None:
        """Usuwa osobę ze składu piętra — tylko gdy nie ma tu dyżurów."""
        emp = self.model.employee_at(row)
        if emp is None or self.floor_id is None:
            return
        name = f"{emp['last_name']} {emp['first_name']}".strip()
        has_shifts = any(
            key[0] == emp["id"] for key in self.model._entries
        )
        if has_shifts:
            QMessageBox.information(
                self, "Usunięcie z grafiku",
                f"{name} ma dyżury na tym piętrze. Usuń najpierw jej wpisy, "
                "a zniknie z grafiku sama.",
            )
            return
        self.db.remove_from_roster(
            self.model.year, self.model.month, self.floor_id, emp["id"]
        )
        self.model.reload()
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
        summary_width = sum(
            NARROW_COL_WIDTH if key in NARROW_SUMMARY else SUMMARY_COL_WIDTH
            for key, _, _ in self.model.summary_columns
        )
        available = self.table.viewport().width() - summary_width - 4
        day_width = max(DAY_COL_MIN, min(DAY_COL_MAX, available // n_days))
        for col in range(self.model.columnCount()):
            if self.model.is_summary_column(col):
                key = self.model.summary_columns[col - n_days][0]
                width = NARROW_COL_WIDTH if key in NARROW_SUMMARY else SUMMARY_COL_WIDTH
            else:
                width = day_width
            self.table.setColumnWidth(col, width)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._resize_columns()
        if self.empty_hint.isVisible():
            self._centre_empty_hint()

    def _refresh_footer(self) -> None:
        self._update_empty_hint()
        norm = month_norm(self.model.year, self.model.month,
                          self.model.rules.daily_norm_minutes)
        floor_txt = ""
        if self.cmb_floor.isVisible():
            where = self.db.floor_name(self.floor_id) or COMBINED_LABEL
            floor_txt = f"{where}   •   "
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
        hidden_txt = ""
        if self.model.hidden_count:
            hidden_txt = (f" &nbsp;•&nbsp; <span style='color:#8C4A00'>ukryto "
                          f"bez dyżurów: <b>{self.model.hidden_count}</b></span>")
        mode_txt = ""
        if self.floor_id is None:
            mode_txt = (" &nbsp;•&nbsp; <span style='color:#8C4A00'>widok łączny "
                        "— dyżury wpisujesz w grafiku konkretnego piętra</span>")
        self.footer.setText(
            f"<span style='color:#444'>Pracowników w grafiku: <b>{staff}</b>"
            f"{hidden_txt}{mode_txt} &nbsp;•&nbsp; "
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
