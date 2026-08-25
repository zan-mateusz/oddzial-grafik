"""Okno aktualizacji programu."""
from __future__ import annotations

import datetime as dt
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QMessageBox, QProgressBar,
    QPushButton, QTextBrowser, QVBoxLayout,
)

from app import config
from app.core import updates
from app.version import __version__

CHECK_INTERVAL_DAYS = 1


# --- sprawdzanie w tle ------------------------------------------------------

class UpdateChecker(QObject):
    """Odpytuje serwis w osobnym wątku, żeby nie blokować okna programu."""

    finished = Signal(object)      # updates.Release albo None
    failed = Signal(str)

    def __init__(self, repo: str):
        super().__init__()
        self.repo = repo

    def run(self) -> None:
        try:
            self.finished.emit(updates.check_for_update(self.repo))
        except updates.UpdateError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:                      # noqa: BLE001
            self.failed.emit(f"Nieoczekiwany błąd: {exc}")


def start_check(parent, repo: str, on_found, on_failed=None):
    """Uruchamia sprawdzanie w tle. Zwraca (wątek, obiekt) do przechowania."""
    thread = QThread(parent)
    checker = UpdateChecker(repo)
    checker.moveToThread(thread)
    thread.started.connect(checker.run)
    checker.finished.connect(on_found)
    if on_failed is not None:
        checker.failed.connect(on_failed)
    for signal in (checker.finished, checker.failed):
        signal.connect(thread.quit)
    thread.finished.connect(checker.deleteLater)
    thread.start()
    return thread, checker


def should_check_today(db) -> bool:
    """Ogranicza odpytywanie serwisu do raz na dobę."""
    if db.get_setting("update_check_enabled", "1") == "0":
        return False
    last = db.get_setting("update_last_check", "")
    if not last:
        return True
    try:
        when = dt.date.fromisoformat(last)
    except ValueError:
        return True
    return (dt.date.today() - when).days >= CHECK_INTERVAL_DAYS


def mark_checked(db, outcome: str = "") -> None:
    """Zapisuje datę sprawdzenia. Wywoływane dopiero po jego zakończeniu —
    inaczej nieudana próba blokowałaby kolejne na całą dobę."""
    db.set_setting("update_last_check", dt.date.today().isoformat())
    db.set_setting(
        "update_last_result",
        f"{dt.datetime.now().strftime('%Y-%m-%d %H:%M')} — {outcome}" if outcome else "",
    )


def last_check_description(db) -> str:
    """Opis ostatniego sprawdzenia — do okna „O programie"."""
    return db.get_setting("update_last_result", "")


def forget_checks(db) -> None:
    """Kasuje ślady po sprawdzaniu, żeby kolejne uruchomienie sprawdziło od nowa.

    Wywoływane po zmianie adresu aktualizacji: poprzednie wyniki dotyczyły
    innego źródła i nie mają już znaczenia.
    """
    db.set_setting("update_last_check", "")
    db.set_setting("update_dismissed_version", "")
    db.set_setting("update_last_result", "")


def was_dismissed(db, version: str) -> bool:
    return db.get_setting("update_dismissed_version", "") == version


def dismiss(db, version: str) -> None:
    db.set_setting("update_dismissed_version", version)


# --- pobieranie -------------------------------------------------------------

class Downloader(QObject):
    progress = Signal(int, int)
    finished = Signal(object)      # Path
    failed = Signal(str)

    def __init__(self, release: updates.Release, target_dir: Path):
        super().__init__()
        self.release = release
        self.target_dir = target_dir
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        try:
            path = updates.download(
                self.release, self.target_dir,
                progress=lambda done, total: self.progress.emit(done, total),
                cancelled=lambda: self._cancelled,
            )
            self.finished.emit(path)
        except updates.UpdateError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:                      # noqa: BLE001
            self.failed.emit(f"Nieoczekiwany błąd: {exc}")


class UpdateDialog(QDialog):
    """Pokazuje, co nowego, i przeprowadza przez pobranie oraz instalację."""

    def __init__(self, release: updates.Release, parent=None):
        super().__init__(parent)
        self.release = release
        self.downloaded: Path | None = None
        self._thread = None
        self._worker = None
        self.setWindowTitle("Dostępna aktualizacja")
        self.setMinimumWidth(520)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)

        headline = QLabel(
            f"<span style='font-size:15px'><b>Dostępna jest nowa wersja "
            f"{self.release.version}</b></span><br>"
            f"<span style='color:#555'>Zainstalowana wersja: {__version__}</span>"
        )
        headline.setTextFormat(Qt.TextFormat.RichText)
        root.addWidget(headline)

        if self.release.notes:
            notes = QTextBrowser()
            notes.setPlainText(self.release.notes)
            notes.setMaximumHeight(190)
            root.addWidget(QLabel("Co się zmieniło:"))
            root.addWidget(notes)

        size = (f"  ({self.release.size_mb:.0f} MB)" if self.release.size else "")
        self.lbl_status = QLabel(f"Plik do pobrania: {self.release.filename}{size}")
        self.lbl_status.setWordWrap(True)
        root.addWidget(self.lbl_status)

        self.bar = QProgressBar()
        self.bar.setVisible(False)
        root.addWidget(self.bar)

        self.hint = QLabel(
            "Grafiki, pracownicy i ustawienia zostaną zachowane — aktualizacja "
            "zmienia tylko sam program."
        )
        self.hint.setWordWrap(True)
        self.hint.setStyleSheet("color:#555;")
        root.addWidget(self.hint)

        buttons = QHBoxLayout()
        self.btn_action = QPushButton("Pobierz i zainstaluj")
        self.btn_action.setDefault(True)
        self.btn_action.clicked.connect(self._start_download)
        self.btn_later = QPushButton("Nie teraz")
        self.btn_later.clicked.connect(self.reject)
        buttons.addStretch(1)
        buttons.addWidget(self.btn_later)
        buttons.addWidget(self.btn_action)
        root.addLayout(buttons)

    # --- pobieranie ---------------------------------------------------------

    def _start_download(self) -> None:
        self.btn_action.setEnabled(False)
        self.btn_later.setText("Przerwij")
        self.btn_later.clicked.disconnect()
        self.btn_later.clicked.connect(self._cancel)
        self.bar.setVisible(True)
        self.bar.setRange(0, 100)
        self.lbl_status.setText("Pobieranie…")

        self._thread = QThread(self)
        self._worker = Downloader(self.release, config.data_dir() / "pobrane")
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.failed.connect(self._on_failed)
        for signal in (self._worker.finished, self._worker.failed):
            signal.connect(self._thread.quit)
        self._thread.start()

    def _cancel(self) -> None:
        if self._worker is not None:
            self._worker.cancel()

    def _on_progress(self, done: int, total: int) -> None:
        if total:
            self.bar.setValue(int(done * 100 / total))
            self.lbl_status.setText(
                f"Pobieranie… {done / 1048576:.0f} z {total / 1048576:.0f} MB"
            )
        else:
            self.bar.setRange(0, 0)

    def _on_failed(self, message: str) -> None:
        self.bar.setVisible(False)
        self.btn_action.setEnabled(True)
        self.btn_later.setText("Zamknij")
        self.lbl_status.setText("Pobieranie nie powiodło się.")
        QMessageBox.warning(self, "Aktualizacja", message)

    def _on_finished(self, path) -> None:
        self.downloaded = Path(path)
        self.bar.setValue(100)
        kind = updates.install_kind()

        if kind == "portable":
            self.lbl_status.setText("Pobrano nową wersję.")
            self.hint.setText(
                "Używasz wersji przenośnej, więc plik trzeba podmienić ręcznie:\n"
                "zamknij program i zastąp stary plik pobranym. Dane pozostaną "
                "nietknięte."
            )
            self.btn_action.setText("Pokaż pobrany plik")
            self.btn_action.setEnabled(True)
            self.btn_action.clicked.disconnect()
            self.btn_action.clicked.connect(self._reveal)
            self.btn_later.setText("Zamknij")
            return

        self.lbl_status.setText("Pobrano. Można zainstalować.")
        self.hint.setText(
            "Program zamknie się, a instalator wykona resztę i uruchomi nową "
            "wersję. Zajmie to kilkanaście sekund."
        )
        self.btn_action.setText("Zainstaluj i uruchom ponownie")
        self.btn_action.setEnabled(True)
        self.btn_action.clicked.disconnect()
        self.btn_action.clicked.connect(self._install)
        self.btn_later.setText("Później")

    def _reveal(self) -> None:
        if self.downloaded:
            updates.reveal(self.downloaded)
        self.accept()

    def _install(self) -> None:
        if not self.downloaded:
            return
        try:
            updates.run_installer(self.downloaded)
        except updates.UpdateError as exc:
            QMessageBox.warning(self, "Aktualizacja", str(exc))
            return
        self.accept()
        # Instalator musi zastąpić pliki programu, więc trzeba go zamknąć.
        from PySide6.QtWidgets import QApplication
        QApplication.quit()

    def closeEvent(self, event) -> None:
        self._cancel()
        if self._thread is not None:
            self._thread.quit()
            self._thread.wait(3000)
        super().closeEvent(event)
