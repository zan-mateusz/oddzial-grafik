"""Główne okno aplikacji."""
from __future__ import annotations

import datetime as dt
import shutil

from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QMainWindow, QMessageBox, QTabWidget,
)

from app import config
from app.core.calendar_pl import PL_MONTHS_TITLE, month_days
from app.io.xlsx_export import export_month
from app.ui.employees_view import EmployeesView
from app.ui.rota_view import RotaView
from app.ui.settings_dialog import SettingsDialog
from app.ui.shift_types_view import ShiftTypesView

ABOUT = """
<h3>Grafik dyżurów</h3>
<p>Program do układania miesięcznych grafików pracy na oddziale.</p>
<p><b>Jak wpisywać dyżury</b><br>
Kliknij komórkę i wpisz kod zmiany (np. <b>D</b>, <b>N</b>, <b>U</b>) albo godziny
w dowolnej postaci: <b>8-14</b>, <b>7:30-19:30</b>, <b>0700-1900</b>.
Możesz też wpisać samą liczbę godzin, np. <b>7,5</b>.</p>
<p><b>Szybkie wypełnianie</b><br>
Zaznacz kilka komórek myszką i kliknij przycisk zmiany nad tabelą — albo
kliknij zaznaczenie prawym przyciskiem. Klawisz <b>Delete</b> czyści zaznaczenie.</p>
<p><b>Kolory dni</b><br>
Soboty i niedziele mają niebieskie nagłówki, święta ustawowe — różowe.
Dyżury w te dni są normalnie planowane i liczone.</p>
<p>Dane zapisują się automatycznie po każdej zmianie.</p>
"""


class MainWindow(QMainWindow):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.setWindowTitle("Grafik dyżurów")
        self.resize(1500, 780)

        self.tabs = QTabWidget()
        self.rota_view = RotaView(db)
        self.employees_view = EmployeesView(db, on_change=self._on_structure_changed)
        self.shift_types_view = ShiftTypesView(db, on_change=self._on_structure_changed)

        self.tabs.addTab(self.rota_view, "Grafik")
        self.tabs.addTab(self.employees_view, "Pracownicy")
        self.tabs.addTab(self.shift_types_view, "Zmiany")
        self.setCentralWidget(self.tabs)

        self._build_menu()
        self.rota_view.dataEdited.connect(self._show_saved)
        self.rota_view.monthChanged.connect(lambda *_: self._update_status())
        self._update_status()

    # --- menu ---------------------------------------------------------------

    def _build_menu(self) -> None:
        menu_file = self.menuBar().addMenu("&Plik")
        self._add(menu_file, "Eksportuj do Excela…", self.export_xlsx, "Ctrl+E")
        self._add(menu_file, "Importuj z pliku Excel…", self.import_xlsx, "Ctrl+I")
        self._add(menu_file, "Importuj ze zdjęcia…", self.import_photo)
        menu_file.addSeparator()
        self._add(menu_file, "Utwórz kopię zapasową…", self.backup_now)
        self._add(menu_file, "Przywróć z kopii…", self.restore_backup)
        menu_file.addSeparator()
        self._add(menu_file, "Zakończ", self.close, "Ctrl+Q")

        menu_rota = self.menuBar().addMenu("&Grafik")
        self._add(menu_rota, "Kopiuj układ z poprzedniego miesiąca", self.copy_previous_month)
        self._add(menu_rota, "Wyczyść bieżący miesiąc", self.clear_month)
        menu_rota.addSeparator()
        self._add(menu_rota, "Poprzedni miesiąc", lambda: self.rota_view._step_month(-1), "Ctrl+Left")
        self._add(menu_rota, "Następny miesiąc", lambda: self.rota_view._step_month(1), "Ctrl+Right")

        menu_tools = self.menuBar().addMenu("&Narzędzia")
        self._add(menu_tools, "Ustawienia…", self.open_settings)

        menu_help = self.menuBar().addMenu("Pomo&c")
        self._add(menu_help, "Jak używać programu", self.show_about)

    def _add(self, menu, text: str, slot, shortcut: str | None = None) -> QAction:
        action = QAction(text, self)
        if shortcut:
            action.setShortcut(QKeySequence(shortcut))
        action.triggered.connect(slot)
        menu.addAction(action)
        return action

    # --- stan ---------------------------------------------------------------

    def _on_structure_changed(self) -> None:
        self.rota_view.refresh()
        self._update_status()

    def _update_status(self) -> None:
        m = self.rota_view.model
        ward = self.db.get_setting("ward_name", "")
        prefix = f"{ward}  •  " if ward else ""
        self.statusBar().showMessage(
            f"{prefix}{PL_MONTHS_TITLE[m.month - 1]} {m.year}  •  "
            f"plik danych: {config.db_path()}"
        )

    def _show_saved(self) -> None:
        self.statusBar().showMessage("Zapisano", 1500)

    # --- eksport / import ---------------------------------------------------

    def _default_filename(self) -> str:
        m = self.rota_view.model
        return f"grafik_{PL_MONTHS_TITLE[m.month - 1].lower()}_{m.year}.xlsx"

    def export_xlsx(self) -> None:
        m = self.rota_view.model
        path, _ = QFileDialog.getSaveFileName(
            self, "Zapisz grafik jako",
            str(config.documents_dir() / self._default_filename()),
            "Arkusz Excel (*.xlsx)",
        )
        if not path:
            return
        try:
            export_month(path, self.db, m.year, m.month, self.db.get_setting("ward_name", ""))
        except Exception as exc:  # noqa: BLE001 - komunikat dla użytkownika
            QMessageBox.critical(self, "Błąd zapisu", f"Nie udało się zapisać pliku:\n{exc}")
            return
        QMessageBox.information(
            self, "Gotowe",
            f"Grafik został zapisany:\n{path}\n\n"
            "Plik otworzysz w Excelu i w LibreOffice/OpenOffice.",
        )

    def import_xlsx(self) -> None:
        from app.ui.import_dialog import ImportDialog
        dlg = ImportDialog(self.db, self.rota_view.model.year, self.rota_view.model.month, self)
        if dlg.exec() == dlg.DialogCode.Accepted:
            self.rota_view.set_month(*dlg.imported_month)
            self.rota_view.refresh()
            self.employees_view.reload()

    def import_photo(self) -> None:
        from app.ui.import_dialog import photo_import_available, ImportDialog
        available, message = photo_import_available()
        if not available:
            QMessageBox.information(self, "Import ze zdjęcia", message)
            return
        dlg = ImportDialog(
            self.db, self.rota_view.model.year, self.rota_view.model.month, self, photo=True
        )
        if dlg.exec() == dlg.DialogCode.Accepted:
            self.rota_view.set_month(*dlg.imported_month)
            self.rota_view.refresh()
            self.employees_view.reload()

    # --- kopie zapasowe -----------------------------------------------------

    def backup_now(self) -> None:
        stamp = dt.datetime.now().strftime("%Y-%m-%d_%H%M")
        target = config.backup_dir() / f"grafik_{stamp}.db"
        self.db.conn.commit()
        shutil.copy2(config.db_path(), target)
        QMessageBox.information(
            self, "Kopia zapasowa", f"Kopia została zapisana:\n{target}"
        )

    def restore_backup(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Wybierz kopię zapasową", str(config.backup_dir()), "Baza danych (*.db)"
        )
        if not path:
            return
        answer = QMessageBox.warning(
            self, "Przywracanie kopii",
            "Wszystkie obecne dane zostaną zastąpione zawartością kopii.\n"
            "Program zamknie się po przywróceniu — uruchom go ponownie.\n\nKontynuować?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        safety = config.backup_dir() / f"przed_przywroceniem_{dt.datetime.now():%Y-%m-%d_%H%M}.db"
        self.db.conn.commit()
        shutil.copy2(config.db_path(), safety)
        self.db.close()
        shutil.copy2(path, config.db_path())
        QMessageBox.information(self, "Gotowe", "Kopia przywrócona. Uruchom program ponownie.")
        QApplication.quit()

    # --- operacje na miesiącu ----------------------------------------------

    def copy_previous_month(self) -> None:
        m = self.rota_view.model
        prev_y, prev_m = (m.year - 1, 12) if m.month == 1 else (m.year, m.month - 1)
        source = self.db.month_entries(prev_y, prev_m)
        if not source:
            QMessageBox.information(
                self, "Brak danych",
                f"{PL_MONTHS_TITLE[prev_m - 1]} {prev_y} nie zawiera żadnych wpisów.",
            )
            return
        if self.db.month_entries(m.year, m.month):
            answer = QMessageBox.question(
                self, "Kopiowanie grafiku",
                f"Bieżący miesiąc zawiera już wpisy — zostaną nadpisane wpisami "
                f"z {PL_MONTHS_TITLE[prev_m - 1].lower()} {prev_y}.\n\nKontynuować?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return

        target_days = month_days(m.year, m.month)
        prev_days = month_days(prev_y, prev_m)
        items = []
        # Kopiujemy według pozycji dnia w miesiącu; nadmiarowe dni pomijamy.
        for i, day in enumerate(target_days):
            if i >= len(prev_days):
                break
            for (emp_id, src_day), raw in source.items():
                if src_day == prev_days[i]:
                    items.append((emp_id, day, raw))
        self.db.clear_month(m.year, m.month)
        self.db.set_entries_bulk(items)
        self.rota_view.refresh()
        QMessageBox.information(
            self, "Skopiowano",
            f"Przeniesiono {len(items)} wpisów. Pamiętaj, że dni tygodnia wypadają "
            "inaczej niż w poprzednim miesiącu — sprawdź weekendy i święta.",
        )

    def clear_month(self) -> None:
        m = self.rota_view.model
        answer = QMessageBox.warning(
            self, "Czyszczenie grafiku",
            f"Usunąć wszystkie wpisy z {PL_MONTHS_TITLE[m.month - 1].lower()} {m.year}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.db.clear_month(m.year, m.month)
        self.rota_view.refresh()

    def open_settings(self) -> None:
        if SettingsDialog(self.db, self).exec() == SettingsDialog.DialogCode.Accepted:
            self.rota_view.refresh()
            self._update_status()

    def show_about(self) -> None:
        QMessageBox.about(self, "Jak używać programu", ABOUT)

    def closeEvent(self, event) -> None:
        self.db.conn.commit()
        super().closeEvent(event)
