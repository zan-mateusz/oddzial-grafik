"""Okno instrukcji obsługi."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMessageBox, QPushButton, QSplitter, QTextBrowser,
    QVBoxLayout,
)

from app import config
from app.ui.manual_content import INTRO, SECTIONS, TITLE

STYLE = """
<style>
  body { font-family: 'Segoe UI', 'Helvetica Neue', sans-serif; font-size: 14px;
         color: #1F2328; line-height: 1.55; }
  h1 { font-size: 22px; margin: 0 0 4px 0; }
  h2 { font-size: 19px; margin: 22px 0 8px 0; color: #12385E;
       border-bottom: 2px solid #DCE7F5; padding-bottom: 4px; }
  h3 { font-size: 15px; margin: 16px 0 4px 0; color: #1E4B7A; }
  p  { margin: 7px 0; }
  ul, ol { margin: 7px 0 7px 22px; }
  li { margin: 3px 0; }
  code { background: #F0F2F5; border: 1px solid #DDE2E8; border-radius: 3px;
         padding: 1px 5px; font-family: 'Consolas', 'Menlo', 'DejaVu Sans Mono', monospace; }
  table { border-collapse: collapse; margin: 10px 0; }
  th { background: #E5EAF1; text-align: left; padding: 5px 10px;
       border: 1px solid #C4D2E4; font-size: 13px; }
  td { padding: 5px 10px; border: 1px solid #DDE2E8; font-size: 13px;
       vertical-align: top; }
  .warn { background: #FFF6E5; border-left: 4px solid #E0A030;
          padding: 8px 12px; margin: 10px 0; }
</style>
"""


def full_html() -> str:
    """Cała instrukcja jako jeden dokument — do wyświetlenia i do zapisu."""
    parts = [STYLE, f"<h1>{TITLE}</h1>", INTRO]
    for section_id, _, html in SECTIONS:
        parts.append(f'<a name="{section_id}"></a>')
        parts.append(html)
    return "\n".join(parts)


class ManualWindow(QDialog):
    """Instrukcja: spis rozdziałów po lewej, treść po prawej."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(TITLE)
        self.resize(1000, 720)
        self._build_ui()
        self.browser.setHtml(full_html())
        self.contents.setCurrentRow(0)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)

        top = QHBoxLayout()
        self.ed_search = QLineEdit()
        self.ed_search.setPlaceholderText("Szukaj w instrukcji…")
        self.ed_search.setClearButtonEnabled(True)
        self.ed_search.returnPressed.connect(self._find_next)
        self.ed_search.textChanged.connect(self._on_search_changed)
        btn_find = QPushButton("Znajdź następne")
        btn_find.clicked.connect(self._find_next)
        self.lbl_found = QLabel()
        self.lbl_found.setStyleSheet("color:#B00020;")
        top.addWidget(self.ed_search, 1)
        top.addWidget(btn_find)
        top.addWidget(self.lbl_found)
        root.addLayout(top)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.contents = QListWidget()
        self.contents.setMaximumWidth(250)
        font = QFont()
        font.setPointSize(11)
        for section_id, title, _ in SECTIONS:
            item = QListWidgetItem(title)
            item.setData(Qt.ItemDataRole.UserRole, section_id)
            item.setFont(font)
            self.contents.addItem(item)
        self.contents.currentItemChanged.connect(self._go_to_section)
        splitter.addWidget(self.contents)

        self.browser = QTextBrowser()
        self.browser.setOpenExternalLinks(False)
        self.browser.setStyleSheet("QTextBrowser { padding: 6px 14px; }")
        splitter.addWidget(self.browser)
        splitter.setSizes([240, 760])
        root.addWidget(splitter, 1)

        bottom = QHBoxLayout()
        btn_save = QPushButton("Zapisz do pliku…")
        btn_save.setToolTip(
            "Zapisuje instrukcję jako stronę, którą można otworzyć "
            "w przeglądarce i wydrukować"
        )
        btn_save.clicked.connect(self._save_to_file)
        btn_close = QPushButton("Zamknij")
        btn_close.clicked.connect(self.accept)
        bottom.addWidget(btn_save)
        bottom.addStretch(1)
        bottom.addWidget(btn_close)
        root.addLayout(bottom)

    # --- nawigacja ----------------------------------------------------------

    def _go_to_section(self, current, _previous=None) -> None:
        if current is None:
            return
        self.browser.scrollToAnchor(current.data(Qt.ItemDataRole.UserRole))

    def show_section(self, section_id: str) -> None:
        """Otwiera instrukcję na wskazanym rozdziale."""
        for row in range(self.contents.count()):
            item = self.contents.item(row)
            if item.data(Qt.ItemDataRole.UserRole) == section_id:
                self.contents.setCurrentRow(row)
                return

    # --- szukanie -----------------------------------------------------------

    def _on_search_changed(self) -> None:
        self.lbl_found.clear()
        # Nowe szukanie zaczynamy od początku dokumentu.
        cursor = self.browser.textCursor()
        cursor.setPosition(0)
        self.browser.setTextCursor(cursor)

    def _find_next(self) -> None:
        text = self.ed_search.text().strip()
        if not text:
            return
        if self.browser.find(text):
            self.lbl_found.clear()
            return
        # Nie znaleziono dalej — próbujemy od początku.
        cursor = self.browser.textCursor()
        cursor.setPosition(0)
        self.browser.setTextCursor(cursor)
        if self.browser.find(text):
            self.lbl_found.setText("(szukanie od początku)")
        else:
            self.lbl_found.setText("Nie znaleziono")

    # --- zapis --------------------------------------------------------------

    def _save_to_file(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Zapisz instrukcję",
            str(config.documents_dir() / "Grafik - instrukcja obslugi.html"),
            "Strona HTML (*.html)",
        )
        if not path:
            return
        try:
            document = (
                "<!doctype html>\n<html lang='pl'>\n<head>\n"
                "<meta charset='utf-8'>\n"
                f"<title>{TITLE}</title>\n</head>\n<body>\n"
                f"{full_html()}\n</body>\n</html>\n"
            )
            Path(path).write_text(document, encoding="utf-8")
        except OSError as exc:
            QMessageBox.critical(self, "Błąd zapisu", str(exc))
            return
        QMessageBox.information(
            self, "Zapisano",
            f"Instrukcja została zapisana:\n{path}\n\n"
            "Otwórz ten plik dwukrotnym kliknięciem — pojawi się w przeglądarce, "
            "skąd można ją wydrukować.",
        )
