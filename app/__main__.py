"""Punkt wejścia aplikacji."""
from __future__ import annotations

import argparse
import datetime as dt
import sqlite3
import sys
from pathlib import Path

from PySide6.QtCore import QLocale
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

from app import config
from app.db import Database, DatabaseTooNewError
from app.ui.main_window import MainWindow


def _light_palette() -> QPalette:
    """Stała jasna paleta.

    Kolory zmian w grafiku są dobrane pod białe tło i muszą wyglądać tak samo
    niezależnie od tego, czy system pracuje w trybie jasnym czy ciemnym.
    """
    pal = QPalette()
    pal.setColor(QPalette.ColorRole.Window, QColor("#F2F3F5"))
    pal.setColor(QPalette.ColorRole.WindowText, QColor("#1F2328"))
    pal.setColor(QPalette.ColorRole.Base, QColor("#FFFFFF"))
    pal.setColor(QPalette.ColorRole.AlternateBase, QColor("#F7F8FA"))
    pal.setColor(QPalette.ColorRole.Text, QColor("#1F2328"))
    pal.setColor(QPalette.ColorRole.Button, QColor("#ECEEF1"))
    pal.setColor(QPalette.ColorRole.ButtonText, QColor("#1F2328"))
    pal.setColor(QPalette.ColorRole.ToolTipBase, QColor("#FFFFE1"))
    pal.setColor(QPalette.ColorRole.ToolTipText, QColor("#1F2328"))
    pal.setColor(QPalette.ColorRole.Highlight, QColor("#2F6FBF"))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
    pal.setColor(QPalette.ColorRole.PlaceholderText, QColor("#8A9099"))
    disabled = QPalette.ColorGroup.Disabled
    pal.setColor(disabled, QPalette.ColorRole.Text, QColor("#9AA0A6"))
    pal.setColor(disabled, QPalette.ColorRole.ButtonText, QColor("#9AA0A6"))
    pal.setColor(disabled, QPalette.ColorRole.WindowText, QColor("#9AA0A6"))
    return pal


def _show_error(title: str, message: str) -> None:
    """Komunikat dla użytkownika, gdy program nie może wystartować."""
    from PySide6.QtWidgets import QMessageBox

    box = QMessageBox()
    box.setIcon(QMessageBox.Icon.Critical)
    box.setWindowTitle(title)
    box.setText(message)
    box.exec()


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="grafik", description="Program do układania grafików dyżurów."
    )
    parser.add_argument(
        "--db", metavar="PLIK",
        help="użyj wskazanego pliku bazy zamiast domyślnego "
             "(przydatne do testów, żeby nie ruszać prawdziwych danych)",
    )
    parser.add_argument(
        "--demo", action="store_true",
        help="uruchom na osobnej bazie wypełnionej przykładowym grafikiem",
    )
    parser.add_argument(
        "--month", metavar="RRRR-MM",
        help="otwórz od razu wskazany miesiąc, np. 2026-06",
    )
    return parser.parse_args(argv)


def _open_database(args: argparse.Namespace):
    """Wybiera plik bazy: --db, tryb demo albo dane użytkownika."""
    if args.db:
        return Database(Path(args.db)), None
    if args.demo:
        from app.demo import seed_demo

        path = config.data_dir() / "demo.db"
        fresh = not path.exists()
        db = Database(path)
        if fresh:
            today = dt.date.today()
            db.set_setting("ward_name", "Oddział Wewnętrzny (dane przykładowe)")
            seed_demo(db, today.year, today.month)
        return db, "demo"
    return Database(config.db_path()), None


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)

    QLocale.setDefault(QLocale(QLocale.Language.Polish, QLocale.Country.Poland))
    qt_app = QApplication(sys.argv[:1])
    qt_app.setApplicationName("Grafik")
    qt_app.setOrganizationName("Grafik")
    qt_app.setStyle("Fusion")
    qt_app.setPalette(_light_palette())

    try:
        db, mode = _open_database(args)
    except DatabaseTooNewError as exc:
        _show_error("Nowszy format danych", str(exc))
        return 1
    except sqlite3.DatabaseError as exc:
        _show_error(
            "Nie można otworzyć pliku z grafikami",
            f"{exc}\n\nKopie zapasowe znajdziesz w katalogu:\n{config.backup_dir()}",
        )
        return 1

    backup = db.autobackup()
    window = MainWindow(db)
    if db.last_upgrade_backup is not None:
        window.notify_upgrade_backup(db.last_upgrade_backup)
    elif backup is not None:
        window.statusBar().showMessage(
            f"Utworzono automatyczną kopię zapasową: {backup.name}", 4000
        )
    if mode == "demo":
        window.setWindowTitle("Grafik dyżurów — DANE PRZYKŁADOWE")

    if args.month:
        try:
            year, month = (int(part) for part in args.month.split("-", 1))
            window.rota_view.set_month(year, month)
        except (ValueError, TypeError):
            print(f"Nieprawidłowy miesiąc: {args.month} (oczekiwano RRRR-MM)",
                  file=sys.stderr)

    window.show()
    return qt_app.exec()


if __name__ == "__main__":
    sys.exit(main())
