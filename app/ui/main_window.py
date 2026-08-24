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
from app.ui.rules_view import RulesView
from app.ui.settings_dialog import SettingsDialog
from app.ui.shift_types_view import ShiftTypesView

ABOUT = """
<h3>Grafik dyżurów</h3>
<p>Program do układania miesięcznych grafików pracy na oddziale.</p>

<p><b>Dyżury całodobowe</b><br>
Wpisz <b>D</b> (dzienny, 7:00–19:00) albo <b>N</b> (nocny, 19:00–7:00).</p>

<p><b>Dyżury krótsze</b><br>
Wpisz sam czas trwania — <b>7:30</b>, <b>10</b>, <b>6:45</b>. Przecinek i kropka
działają tak samo jak dwukropek, więc <b>7,3</b> również znaczy 7 godzin
30 minut, a <b>7,35</b> — 7 godzin 35 minut. Program zapisuje odczytaną wartość
w komórce, więc od razu widać, czy zrozumiał tak, jak trzeba.</p>

<p><b>Nieobecności</b><br>
<b>U</b> — urlop, <b>L4</b> — zwolnienie lekarskie, <b>OP</b> — opieka.
Dzień wolny zostaw pusty.</p>

<p><b>Szybkie wypełnianie</b><br>
Zaznacz kilka komórek myszką i kliknij przycisk zmiany nad tabelą — albo
kliknij zaznaczenie prawym przyciskiem. Klawisz <b>Delete</b> czyści zaznaczenie.</p>

<p><b>Dwa piętra</b><br>
Każde piętro ma własny grafik — przełączasz je listą <b>Piętro</b> u góry.
Jeśli ktoś ma podmienić kogoś na drugim piętrze, kliknij
<b>Dodaj zastępstwo…</b>, wybierz osobę i wpisz jej dyżur.
Osoby na zastępstwie są wypisane kursywą ze strzałką i nazwą swojego piętra.</p>

<p>Dyżur, który ktoś pełni na drugim piętrze, widać tu na szaro — dzięki temu
nie zaplanujesz komuś dwóch dyżurów tego samego dnia. Kolumny <b>Godz. tu</b>
i <b>Dyż. tu</b> dotyczą oglądanego piętra, a <b>Godziny</b>, <b>Wymiar</b>
i <b>Bilans</b> — całego miesiąca, bo wymiar czasu pracy jest jeden.</p>

<p><b>Kolory dni</b><br>
Soboty i niedziele mają niebieskie nagłówki, święta ustawowe — różowe.
Dyżury w te dni planuje się normalnie.</p>

<p><b>Zasady liczenia</b><br>
Zakładka <b>Zasady</b> pokazuje, według jakich reguł liczone są godziny —
norma dobowa, pora nocna, sposób liczenia urlopu — wraz z podstawą prawną.
Wszystko można tam zmienić, jeśli na oddziale obowiązują inne ustalenia.</p>

<p>Wpis, którego program nie rozpoznał, jest <b>czerwony</b> — te godziny nie są
liczone, więc sprawdź pisownię. Dane zapisują się automatycznie.</p>

<p><i>Pełna instrukcja obsługi: menu <b>Pomoc → Instrukcja obsługi</b>
albo klawisz <b>F1</b>.</i></p>
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
        self.rules_view = RulesView(db, on_change=self._on_structure_changed)

        self.tabs.addTab(self.rota_view, "Grafik")
        self.tabs.addTab(self.employees_view, "Pracownicy")
        self.tabs.addTab(self.shift_types_view, "Zmiany")
        self.tabs.addTab(self.rules_view, "Zasady")
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
        self._add(menu_help, "Instrukcja obsługi", self.show_manual, "F1")
        menu_help.addSeparator()
        self._add(menu_help, "Krótka ściągawka", self.show_about)

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
        self.rules_view.reload()
        self._update_status()

    def _update_status(self) -> None:
        m = self.rota_view.model
        ward = self.db.get_setting("ward_name", "")
        prefix = f"{ward}  •  " if ward else ""
        self.statusBar().showMessage(
            f"{prefix}{PL_MONTHS_TITLE[m.month - 1]} {m.year}  •  "
            f"plik danych: {config.db_path()}"
        )

    def notify_upgrade_backup(self, path) -> None:
        """Informuje, że aktualizacja przebudowała plik danych."""
        QMessageBox.information(
            self, "Zaktualizowano plik z grafikami",
            "Ta wersja programu używa nowszego formatu danych, więc plik "
            "z grafikami został przebudowany.\n\n"
            "Wszystkie dane zostały zachowane. Kopia sprzed aktualizacji leży "
            f"na wszelki wypadek tutaj:\n{path}",
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
        dlg = ImportDialog(
            self.db, self.rota_view.model.year, self.rota_view.model.month, self,
            floor_id=self.rota_view.floor_id,
        )
        if dlg.exec() == dlg.DialogCode.Accepted:
            self._show_imported(dlg)

    def import_photo(self) -> None:
        from app.ui.import_dialog import photo_import_available, ImportDialog
        available, message = photo_import_available()
        if not available:
            QMessageBox.information(self, "Import ze zdjęcia", message)
            return
        dlg = ImportDialog(
            self.db, self.rota_view.model.year, self.rota_view.model.month, self,
            photo=True, floor_id=self.rota_view.floor_id,
        )
        if dlg.exec() == dlg.DialogCode.Accepted:
            self._show_imported(dlg)

    def _show_imported(self, dlg) -> None:
        """Po imporcie pokazujemy dokładnie ten grafik, który wczytano."""
        if dlg.imported_floor is not None:
            index = self.rota_view.cmb_floor.findData(dlg.imported_floor)
            if index >= 0:
                self.rota_view.cmb_floor.setCurrentIndex(index)
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
        floor_id = self.rota_view.floor_id
        source = self.db.month_entries(prev_y, prev_m, floor_id)
        if not source:
            QMessageBox.information(
                self, "Brak danych",
                f"{PL_MONTHS_TITLE[prev_m - 1]} {prev_y} nie zawiera żadnych wpisów.",
            )
            return
        if self.db.month_entries(m.year, m.month, floor_id):
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
                    items.append((emp_id, day, raw, floor_id))
        self.db.clear_month(m.year, m.month, floor_id)
        self.db.set_entries_bulk(items)
        self.rota_view.refresh()
        QMessageBox.information(
            self, "Skopiowano",
            f"Przeniesiono {len(items)} wpisów. Pamiętaj, że dni tygodnia wypadają "
            "inaczej niż w poprzednim miesiącu — sprawdź weekendy i święta.",
        )

    def clear_month(self) -> None:
        m = self.rota_view.model
        floor_id = self.rota_view.floor_id
        where = ""
        if len(self.db.floors()) > 1:
            where = f" na piętrze {self.db.floor_name(floor_id)}"
        answer = QMessageBox.warning(
            self, "Czyszczenie grafiku",
            f"Usunąć wszystkie wpisy z {PL_MONTHS_TITLE[m.month - 1].lower()} "
            f"{m.year}{where}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.db.clear_month(m.year, m.month, floor_id)
        self.rota_view.refresh()

    def open_settings(self) -> None:
        if SettingsDialog(self.db, self).exec() == SettingsDialog.DialogCode.Accepted:
            self.rota_view.refresh()
            self._update_status()

    def show_manual(self, section: str | None = None) -> None:
        """Otwiera pełną instrukcję. Okno jest jedno — kolejne wywołania
        przenoszą je na wierzch zamiast otwierać duplikat."""
        from app.ui.manual import ManualWindow

        if getattr(self, "_manual", None) is None:
            self._manual = ManualWindow(self)
        if section:
            self._manual.show_section(section)
        self._manual.show()
        self._manual.raise_()
        self._manual.activateWindow()

    def show_about(self) -> None:
        QMessageBox.about(self, "Krótka ściągawka", ABOUT)

    def closeEvent(self, event) -> None:
        self.db.conn.commit()
        super().closeEvent(event)
