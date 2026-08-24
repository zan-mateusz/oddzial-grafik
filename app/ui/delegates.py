"""Edytor komórki grafiku — pole tekstowe z podpowiedziami kodów zmian."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCompleter, QLineEdit, QStyledItemDelegate


class ShiftCellDelegate(QStyledItemDelegate):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self._codes: list[str] = []
        self.refresh_codes()

    def refresh_codes(self) -> None:
        self._codes = [st.code for st in self.db.shift_types()]

    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        editor.setAlignment(Qt.AlignmentFlag.AlignCenter)
        completer = QCompleter(self._codes, editor)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setCompletionMode(QCompleter.CompletionMode.InlineCompletion)
        editor.setCompleter(completer)
        return editor

    def setEditorData(self, editor, index):
        editor.setText(index.data(Qt.ItemDataRole.EditRole) or "")
        editor.selectAll()

    def setModelData(self, editor, model, index):
        model.setData(index, editor.text(), Qt.ItemDataRole.EditRole)
