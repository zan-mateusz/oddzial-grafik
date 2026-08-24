"""Kreator importu grafiku z pliku Excel albo ze zdjęcia."""
from __future__ import annotations

import calendar
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QDialog, QDialogButtonBox,
    QFileDialog, QFormLayout, QGroupBox, QHBoxLayout, QHeaderView, QLabel,
    QMessageBox, QPushButton, QSpinBox, QSplitter, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from app import config
from app.core.calendar_pl import PL_MONTHS_TITLE
from app.io import xlsx_import as xi

HIGHLIGHT_HEADER = QColor("#FFE9A8")
HIGHLIGHT_NAME = QColor("#D6E8FF")
HIGHLIGHT_DATA = QColor("#EAF6EC")


def photo_import_available() -> tuple[bool, str]:
    """Sprawdza, czy da się odczytać tabelę ze zdjęcia (wymaga Tesseract OCR)."""
    try:
        from app.io.ocr import check_available
    except ImportError:
        return False, "Moduł OCR nie jest dostępny w tej wersji programu."
    return check_available()


class ImportDialog(QDialog):
    """Wybór pliku, podgląd układu, dopasowanie nazwisk, import."""

    def __init__(self, db, year: int, month: int, parent=None, photo: bool = False,
                 floor_id: int | None = None):
        super().__init__(parent)
        self.db = db
        self.photo_mode = photo
        self.imported_month = (year, month)
        self.imported_floor = floor_id
        self.grids: list[xi.SheetGrid] = []
        self.rows: list[xi.ImportedRow] = []
        self.setWindowTitle("Import grafiku ze zdjęcia" if photo else "Import grafiku z Excela")
        self.resize(1080, 720)

        self._build_ui(year, month, floor_id)
        self._pick_file()

    # --- interfejs ----------------------------------------------------------

    def _build_ui(self, year: int, month: int, floor_id: int | None = None) -> None:
        root = QVBoxLayout(self)

        top = QHBoxLayout()
        self.lbl_file = QLabel("Nie wybrano pliku")
        self.lbl_file.setStyleSheet("font-weight:600;")
        btn_file = QPushButton("Wybierz plik…")
        btn_file.clicked.connect(self._pick_file)
        top.addWidget(self.lbl_file, 1)
        top.addWidget(btn_file)
        root.addLayout(top)

        opts = QGroupBox("Ustawienia importu")
        form = QFormLayout(opts)

        self.cmb_sheet = QComboBox()
        self.cmb_sheet.currentIndexChanged.connect(self._on_sheet_changed)

        self.cmb_floor = QComboBox()
        for floor in self.db.floors():
            self.cmb_floor.addItem(floor["name"], floor["id"])
        if floor_id is not None:
            index = self.cmb_floor.findData(floor_id)
            if index >= 0:
                self.cmb_floor.setCurrentIndex(index)

        month_row = QHBoxLayout()
        self.cmb_month = QComboBox()
        self.cmb_month.addItems(PL_MONTHS_TITLE)
        self.cmb_month.setCurrentIndex(month - 1)
        self.spin_year = QSpinBox()
        self.spin_year.setRange(2000, 2100)
        self.spin_year.setValue(year)
        month_row.addWidget(self.cmb_month)
        month_row.addWidget(self.spin_year)
        month_row.addStretch(1)
        month_wrap = QWidget()
        month_wrap.setLayout(month_row)

        pos_row = QHBoxLayout()
        self.spin_header = QSpinBox()
        self.spin_header.setRange(1, 60)
        self.spin_name_col = QSpinBox()
        self.spin_name_col.setRange(1, 60)
        self.spin_first_row = QSpinBox()
        self.spin_first_row.setRange(1, 60)
        for label, widget in (
            ("wiersz z dniami:", self.spin_header),
            ("kolumna z nazwiskami:", self.spin_name_col),
            ("pierwszy wiersz danych:", self.spin_first_row),
        ):
            pos_row.addWidget(QLabel(label))
            pos_row.addWidget(widget)
            pos_row.addSpacing(10)
        pos_row.addStretch(1)
        pos_wrap = QWidget()
        pos_wrap.setLayout(pos_row)
        for w in (self.spin_header, self.spin_name_col, self.spin_first_row):
            w.valueChanged.connect(self._on_manual_layout_changed)

        self.chk_replace = QCheckBox(
            "Zastąp istniejące wpisy w tym miesiącu (tylko na wybranym piętrze)"
        )
        self.chk_replace.setChecked(True)

        form.addRow("Arkusz", self.cmb_sheet)
        if self.cmb_floor.count() > 1:
            form.addRow("Importuj na piętro", self.cmb_floor)
        form.addRow("Importuj jako miesiąc", month_wrap)
        form.addRow("Położenie danych", pos_wrap)
        form.addRow("", self.chk_replace)
        root.addWidget(opts)

        self.lbl_status = QLabel()
        self.lbl_status.setWordWrap(True)
        root.addWidget(self.lbl_status)

        splitter = QSplitter(Qt.Orientation.Vertical)

        self.preview = QTableWidget()
        self.preview.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.preview.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        preview_box = QGroupBox("Podgląd arkusza")
        pl = QVBoxLayout(preview_box)
        pl.addWidget(self.preview)
        splitter.addWidget(preview_box)

        self.mapping = QTableWidget(0, 4)
        self.mapping.setHorizontalHeaderLabels(
            ["Nazwisko w pliku", "Wpisów", "Przypisz do", "Uwaga"]
        )
        self.mapping.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.mapping.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self.mapping.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )
        self.mapping.verticalHeader().setVisible(False)
        map_box = QGroupBox("Dopasowanie pracowników")
        ml = QVBoxLayout(map_box)
        ml.addWidget(self.mapping)
        splitter.addWidget(map_box)
        splitter.setSizes([340, 300])
        root.addWidget(splitter, 1)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Importuj")
        self.buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Anuluj")
        self.buttons.accepted.connect(self._do_import)
        self.buttons.rejected.connect(self.reject)
        root.addWidget(self.buttons)
        self._set_enabled(False)

    def _set_enabled(self, ok: bool) -> None:
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(ok)

    # --- wczytywanie --------------------------------------------------------

    def _pick_file(self) -> None:
        if self.photo_mode:
            caption = "Wybierz zdjęcie grafiku"
            filt = "Obrazy (*.png *.jpg *.jpeg *.tif *.tiff *.bmp)"
        else:
            caption = "Wybierz plik z grafikiem"
            filt = ("Arkusze (*.xlsx *.xlsm *.ods);;"
                    "Excel (*.xlsx *.xlsm);;LibreOffice / OpenOffice (*.ods)")
        path, _ = QFileDialog.getOpenFileName(
            self, caption, str(config.documents_dir()), filt
        )
        if not path:
            return
        self.source_path = Path(path)
        self.lbl_file.setText(self.source_path.name)
        try:
            if self.photo_mode:
                from app.io.ocr import read_photo_grid
                self.grids = [read_photo_grid(path)]
            else:
                self.grids = xi.read_sheets(path)
        except Exception as exc:  # noqa: BLE001 - komunikat dla użytkownika
            QMessageBox.critical(self, "Nie udało się otworzyć pliku", str(exc))
            return
        self.cmb_sheet.blockSignals(True)
        self.cmb_sheet.clear()
        for grid in self.grids:
            filled = sum(1 for row in grid.cells if any(row))
            label = grid.name if filled else f"{grid.name}  (pusty)"
            self.cmb_sheet.addItem(label)
        # Skoroszyt zwykle zawiera puste arkusze przed właściwym grafikiem.
        self.cmb_sheet.setCurrentIndex(
            xi.best_sheet_index(self.grids, self._days_in_target_month())
        )
        self.cmb_sheet.blockSignals(False)
        self.cmb_sheet.setEnabled(len(self.grids) > 1)
        self._on_sheet_changed()

    def _current_grid(self) -> xi.SheetGrid | None:
        i = self.cmb_sheet.currentIndex()
        return self.grids[i] if 0 <= i < len(self.grids) else None

    def _days_in_target_month(self) -> int:
        return calendar.monthrange(self.spin_year.value(), self.cmb_month.currentIndex() + 1)[1]

    def _apply_month_guess(self, grid) -> None:
        """Ustawia miesiąc na podstawie nazwy arkusza (pewniejsza) lub pliku."""
        filename = getattr(self, "source_path", None)
        year, month = xi.guess_month(grid.name, filename.stem if filename else "")
        if month is not None:
            self.cmb_month.setCurrentIndex(month - 1)
        if year is not None:
            self.spin_year.setValue(year)

    def _on_sheet_changed(self) -> None:
        grid = self._current_grid()
        if grid is None:
            return
        self._apply_month_guess(grid)
        self.layout_info = xi.detect_layout(grid, self._days_in_target_month())
        for widget, value in (
            (self.spin_header, self.layout_info.header_row + 1),
            (self.spin_name_col, self.layout_info.name_col + 1),
            (self.spin_first_row, self.layout_info.first_data_row + 1),
        ):
            widget.blockSignals(True)
            widget.setValue(max(1, value))
            widget.blockSignals(False)
        self._refresh(auto=True)

    def _on_manual_layout_changed(self) -> None:
        grid = self._current_grid()
        if grid is None:
            return
        header = self.spin_header.value() - 1
        name_col = self.spin_name_col.value() - 1
        # Numery dni odczytujemy z wiersza wskazanego ręcznie.
        day_cols = {}
        for c in range(grid.n_cols):
            day = xi._day_number(grid.value(header, c))
            if day is not None and day not in day_cols and c > name_col:
                day_cols[day] = c
        self.layout_info = xi.Layout(
            header_row=header,
            first_data_row=self.spin_first_row.value() - 1,
            name_col=name_col,
            day_cols=xi._longest_increasing_run(day_cols),
            confidence=0.0,
        )
        self._refresh(auto=False)

    # --- podgląd i dopasowanie ---------------------------------------------

    def _refresh(self, auto: bool) -> None:
        grid = self._current_grid()
        if grid is None:
            return
        lay = self.layout_info
        self._fill_preview(grid, lay)

        if not lay.ok:
            empty = not any(any(row) for row in grid.cells)
            if empty:
                hint = (
                    f"Arkusz „{grid.name}” jest pusty. "
                    "Wybierz z listy powyżej arkusz z grafikiem."
                )
            else:
                hint = (
                    "Nie rozpoznano układu tabeli. Wskaż ręcznie wiersz "
                    "z numerami dni oraz kolumnę z nazwiskami — numery wierszy "
                    "i kolumn widać w nagłówkach podglądu."
                )
            self.lbl_status.setText(f"<span style='color:#B00020'>{hint}</span>")
            self.mapping.setRowCount(0)
            self._set_enabled(False)
            return

        self.rows = xi.extract_rows(grid, lay)
        xi.match_employees(self.rows, self.db.employees(include_inactive=True))
        self._fill_mapping()

        found = "automatycznie" if auto else "ręcznie"
        matched = sum(1 for r in self.rows if r.employee_id)
        self.lbl_status.setText(
            f"Układ rozpoznany {found}: <b>{len(lay.day_cols)}</b> dni, "
            f"<b>{len(self.rows)}</b> wierszy z nazwiskami, "
            f"dopasowano <b>{matched}</b> do istniejących pracowników."
        )
        self._set_enabled(bool(self.rows))

    def _fill_preview(self, grid: xi.SheetGrid, lay: xi.Layout) -> None:
        n_rows = min(grid.n_rows, 30)
        n_cols = min(grid.n_cols, 40)
        self.preview.setRowCount(n_rows)
        self.preview.setColumnCount(n_cols)
        self.preview.setHorizontalHeaderLabels([str(c + 1) for c in range(n_cols)])
        self.preview.setVerticalHeaderLabels([str(r + 1) for r in range(n_rows)])
        day_cols = set(lay.day_cols.values())
        for r in range(n_rows):
            for c in range(n_cols):
                # Nagłówki dni bywają dwuwierszowe ("1\nPn") — w podglądzie
                # pokazujemy je w jednej linii, żeby nie zamieniły się w wielokropek.
                item = QTableWidgetItem(" ".join(grid.value(r, c).split()))
                if r == lay.header_row and c in day_cols:
                    item.setBackground(QBrush(HIGHLIGHT_HEADER))
                elif c == lay.name_col and r >= lay.first_data_row:
                    item.setBackground(QBrush(HIGHLIGHT_NAME))
                elif r >= lay.first_data_row and c in day_cols:
                    item.setBackground(QBrush(HIGHLIGHT_DATA))
                self.preview.setItem(r, c, item)
        # Scalone komórki tytułu potrafią rozepchnąć kolumnę na całą szerokość,
        # a kolumny dni ścisnąć do nieczytelnej wstążki — stąd widełki.
        self.preview.resizeColumnsToContents()
        for c in range(n_cols):
            self.preview.setColumnWidth(c, max(46, min(self.preview.columnWidth(c), 120)))
        self.preview.verticalHeader().setDefaultSectionSize(22)

    def _fill_mapping(self) -> None:
        employees = self.db.employees(include_inactive=True)
        self.mapping.setRowCount(len(self.rows))
        self._combos: list[QComboBox] = []
        for r, row in enumerate(self.rows):
            self.mapping.setItem(r, 0, QTableWidgetItem(row.source_name))
            count = QTableWidgetItem(str(row.filled))
            count.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.mapping.setItem(r, 1, count)

            combo = QComboBox()
            combo.addItem("➕ Utwórz nowego pracownika", None)
            combo.addItem("— pomiń ten wiersz —", "skip")
            for emp in employees:
                label = f"{emp['last_name']} {emp['first_name']}".strip()
                if not emp["active"]:
                    label += "  (już nie pracuje)"
                combo.addItem(label, emp["id"])
            if row.employee_id is not None:
                idx = combo.findData(row.employee_id)
                if idx >= 0:
                    combo.setCurrentIndex(idx)
            self.mapping.setCellWidget(r, 2, combo)
            self._combos.append(combo)

            note = "" if row.employee_id else "nowy pracownik"
            item = QTableWidgetItem(note)
            if note:
                item.setForeground(QBrush(QColor("#B45309")))
            self.mapping.setItem(r, 3, item)

    # --- zapis --------------------------------------------------------------

    def _do_import(self) -> None:
        year = self.spin_year.value()
        month = self.cmb_month.currentIndex() + 1
        selected: list[xi.ImportedRow] = []
        for row, combo in zip(self.rows, self._combos):
            data = combo.currentData()
            if data == "skip":
                continue
            row.employee_id = data if isinstance(data, int) else None
            row.create_new = row.employee_id is None
            selected.append(row)

        if not selected:
            QMessageBox.information(self, "Nic do zaimportowania",
                                    "Wszystkie wiersze zostały pominięte.")
            return

        floor_id = self.cmb_floor.currentData()
        new_count = sum(1 for r in selected if r.create_new)
        warning = ""
        if self.chk_replace.isChecked() and self.db.month_entries(year, month, floor_id):
            warning = ("\n\nUwaga: obecne wpisy w tym miesiącu zostaną usunięte "
                       "i zastąpione danymi z pliku.")
        answer = QMessageBox.question(
            self, "Potwierdzenie importu",
            f"Zaimportować {len(selected)} wierszy do "
            f"{PL_MONTHS_TITLE[month - 1].lower()} {year}"
            + (f" — {self.db.floor_name(floor_id)}?" if self.cmb_floor.count() > 1 else "?")
            + (f"\nZostanie utworzonych nowych pracowników: {new_count}." if new_count else "")
            + warning,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Yes,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        entries, created = xi.apply_import(
            self.db, year, month, selected,
            replace=self.chk_replace.isChecked(), floor_id=floor_id,
        )
        self.imported_month = (year, month)
        self.imported_floor = floor_id
        QMessageBox.information(
            self, "Import zakończony",
            f"Zaimportowano {entries} wpisów.\n"
            f"Utworzono nowych pracowników: {created}.\n\n"
            "Sprawdź grafik — wpisy, których program nie rozpoznał, są "
            "zaznaczone na czerwono.",
        )
        self.accept()
