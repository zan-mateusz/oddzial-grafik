"""Testy budowy interfejsu — sprawdzają, że okna w ogóle dają się utworzyć.

Uruchamiane bez ekranu (offscreen). Nie zastępują testów logiki, ale wyłapują
błędy składania widoków, których nie widać w testach warstwy danych.
"""
import datetime as dt
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication  # noqa: E402

from app.db import Database  # noqa: E402
from app.demo import seed_demo  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def db(tmp_path):
    database = Database(tmp_path / "ui.db")
    yield database
    database.close()


def test_main_window_builds_on_empty_database(qapp, db):
    from app.ui.main_window import MainWindow

    window = MainWindow(db)
    assert window.rota_view.model.rowCount() == 0
    window.close()


def test_main_window_builds_with_data(qapp, db):
    from app.ui.main_window import MainWindow

    today = dt.date.today()
    seed_demo(db, today.year, today.month)
    window = MainWindow(db)
    assert window.rota_view.model.rowCount() > 0
    assert window.rota_view.cmb_floor.count() == len(db.floors())
    window.close()


def test_switching_floors_changes_the_roster(qapp, db):
    from app.ui.main_window import MainWindow

    today = dt.date.today()
    seed_demo(db, today.year, today.month)
    window = MainWindow(db)
    view = window.rota_view

    first = {e["id"] for e in view.model.employees}
    view.cmb_floor.setCurrentIndex(1)
    second = {e["id"] for e in view.model.employees}
    assert first != second
    assert view.floor_id == db.floors()[1]["id"]
    window.close()


def test_floor_columns_appear_only_with_several_floors(qapp, db):
    from app.ui.rota_model import FLOOR_COLUMNS, MONTH_COLUMNS, RotaModel

    today = dt.date.today()
    model = RotaModel(db, today.year, today.month, db.floors()[0]["id"])
    assert len(model.summary_columns) == len(FLOOR_COLUMNS) + len(MONTH_COLUMNS)

    for floor in db.floors()[1:]:
        db.delete_floor(floor["id"])
    model.set_floor(db.floors()[0]["id"])
    assert len(model.summary_columns) == len(MONTH_COLUMNS)


def test_employees_and_shift_type_tabs_build(qapp, db):
    from app.ui.employees_view import EmployeesView
    from app.ui.shift_types_view import ShiftTypesView

    db.add_employee("Kowalska", "Anna")
    employees = EmployeesView(db)
    assert employees.table.rowCount() == 1
    shifts = ShiftTypesView(db)
    assert shifts.table.rowCount() == len(db.shift_types())


def test_settings_and_import_dialogs_build(qapp, db):
    from app.ui.import_dialog import ImportDialog
    from app.ui.settings_dialog import SettingsDialog

    settings = SettingsDialog(db)
    assert settings.list_floors.count() == len(db.floors())

    # Kreator importu otwiera okno wyboru pliku — pomijamy je.
    ImportDialog._pick_file = lambda self: None
    dialog = ImportDialog(db, 2026, 6, floor_id=db.floors()[0]["id"])
    assert dialog.cmb_floor.count() == len(db.floors())


def test_manual_window_builds_and_navigates(qapp):
    from PySide6.QtCore import Qt

    from app.ui.manual import ManualWindow
    from app.ui.manual_content import SECTIONS

    window = ManualWindow()
    assert window.contents.count() == len(SECTIONS)
    window.show_section("zasady")
    chosen = window.contents.currentItem().data(Qt.ItemDataRole.UserRole)
    assert chosen == "zasady"
    window.close()


def test_manual_search_reports_missing_text(qapp):
    from app.ui.manual import ManualWindow

    window = ManualWindow()
    window.ed_search.setText("pora nocna")
    window._find_next()
    assert window.lbl_found.text() == ""

    window.ed_search.setText("zzzznieistniejące")
    window._find_next()
    assert "Nie znaleziono" in window.lbl_found.text()
    window.close()


def test_help_menu_opens_the_manual_once(qapp, db):
    from app.ui.main_window import MainWindow

    window = MainWindow(db)
    window.show_manual()
    first = window._manual
    window.show_manual("kopie")
    assert window._manual is first        # jedno okno, nie kolejne kopie
    window.close()
