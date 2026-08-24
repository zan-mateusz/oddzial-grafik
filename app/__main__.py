"""Punkt wejścia aplikacji."""
from __future__ import annotations

import sys

from PySide6.QtCore import QLocale
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

from app import config
from app.db import Database
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


def main() -> int:
    QLocale.setDefault(QLocale(QLocale.Language.Polish, QLocale.Country.Poland))
    qt_app = QApplication(sys.argv)
    qt_app.setApplicationName("Grafik")
    qt_app.setOrganizationName("Grafik")
    qt_app.setStyle("Fusion")
    qt_app.setPalette(_light_palette())

    db = Database(config.db_path())
    window = MainWindow(db)
    window.show()
    return qt_app.exec()


if __name__ == "__main__":
    sys.exit(main())
