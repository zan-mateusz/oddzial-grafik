"""Testy przetwarzania wyniku OCR — bez uruchamiania silnika Tesseract."""
import pytest

from app.io import ocr
from app.io.xlsx_import import _fill_missing_days, _longest_increasing_run


def test_split_token_separates_cells_joined_by_table_border():
    parts = ocr._split_token("D|D")
    assert [p[0] for p in parts] == ["D", "D"]
    # Fragmenty muszą leżeć w rozłącznych częściach pierwotnego prostokąta.
    assert parts[0][1] < parts[0][2] <= parts[1][1] < parts[1][2]


def test_split_token_keeps_hyphen_in_hour_ranges():
    """Myślnik rozdziela godziny — nie wolno go traktować jak linii tabeli."""
    assert [p[0] for p in ocr._split_token("8-14")] == ["8-14"]
    assert [p[0] for p in ocr._split_token("|7:30-19:30|")] == ["7:30-19:30"]


def test_split_token_drops_pure_border_fragments():
    assert ocr._split_token("|") == []
    assert ocr._split_token("[]") == []
    assert [p[0] for p in ocr._split_token("[U")] == ["U"]


def test_split_token_handles_empty_input():
    assert ocr._split_token("") == []


def test_day_run_tolerates_a_missing_number():
    """Jeden numer zgubiony przez OCR nie może uciąć reszty miesiąca."""
    cols = {d: d * 10 for d in range(1, 32) if d != 11}
    run = _longest_increasing_run(cols)
    assert len(run) == 31
    assert run[11] == 110  # kolumna odtworzona z równego rozstawu


def test_day_run_rejects_numbers_in_decreasing_columns():
    cols = {1: 100, 2: 50, 3: 120}
    run = _longest_increasing_run(cols)
    assert 2 not in run


def test_fill_missing_days_leaves_short_runs_alone():
    assert _fill_missing_days({1: 10, 5: 50}) == {1: 10, 5: 50}


def test_fill_missing_days_interpolates_regular_spacing():
    filled = _fill_missing_days({1: 0, 2: 10, 3: 20, 5: 40, 6: 50})
    assert filled[4] == 30


def test_check_available_reports_clearly():
    ok, message = ocr.check_available()
    assert isinstance(ok, bool)
    assert message
    if not ok:
        assert "Tesseract" in message


@pytest.mark.parametrize("text,expected", [
    ("D", ["D"]), ("L4", ["L4"]), ("UŻ", ["UŻ"]),
    ("D N", ["D", "N"]), ("_D_", ["D"]),
])
def test_split_token_common_cell_contents(text, expected):
    assert [p[0] for p in ocr._split_token(text)] == expected
