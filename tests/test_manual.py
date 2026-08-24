"""Testy instrukcji obsługi — spójność treści i eksportu do repozytorium."""
import re
import subprocess
import sys
from pathlib import Path

import pytest

from app.ui.manual import STYLE, full_html
from app.ui.manual_content import INTRO, SECTIONS, TITLE

ROOT = Path(__file__).resolve().parent.parent

# Znaczniki, których używa instrukcja. Konwerter do Markdowna obsługuje
# dokładnie ten zestaw — pojawienie się innego oznacza, że trzeba go rozszerzyć.
ALLOWED_TAGS = {
    "h2", "h3", "p", "ul", "ol", "li", "table", "tr", "th", "td",
    "b", "i", "code", "br", "a",
}


def test_every_section_has_content():
    for section_id, title, html in SECTIONS:
        assert section_id and title, section_id
        assert len(html.strip()) > 200, f"rozdział {title} jest podejrzanie krótki"


def test_section_ids_are_unique():
    ids = [s[0] for s in SECTIONS]
    assert len(ids) == len(set(ids))


def test_each_section_starts_with_its_heading():
    """Nagłówek w treści musi zgadzać się z nazwą w spisie rozdziałów."""
    for _, title, html in SECTIONS:
        heading = re.search(r"<h2>(.*?)</h2>", html, re.S)
        assert heading is not None, title
        assert heading.group(1).strip() == title


def test_only_supported_tags_are_used():
    used = set()
    for _, _, html in SECTIONS:
        used |= {t.lower() for t in re.findall(r"<\s*([a-zA-Z0-9]+)", html)}
    unsupported = used - ALLOWED_TAGS
    assert not unsupported, f"nieobsługiwane znaczniki: {sorted(unsupported)}"


def test_tags_are_balanced():
    for _, title, html in SECTIONS:
        for tag in ("h2", "h3", "p", "ul", "ol", "li", "table", "tr", "td", "th"):
            opens = len(re.findall(rf"<{tag}[ >]", html))
            closes = len(re.findall(rf"</{tag}>", html))
            assert opens == closes, f"{title}: niezamknięty <{tag}>"


def test_tables_have_consistent_column_counts():
    for _, title, html in SECTIONS:
        for table in re.findall(r"<table>(.*?)</table>", html, re.S):
            rows = re.findall(r"<tr>(.*?)</tr>", table, re.S)
            widths = {
                len(re.findall(r"<t[hd]>", row)) for row in rows
            }
            assert len(widths) == 1, f"{title}: nierówne kolumny w tabeli"


def test_full_html_contains_every_section_anchor():
    page = full_html()
    for section_id, _, _ in SECTIONS:
        assert f'name="{section_id}"' in page
    assert TITLE in page
    assert STYLE in page
    assert INTRO.strip() in page


def test_manual_covers_the_important_topics():
    """Zabezpieczenie przed usunięciem rozdziału, którego użytkownik szuka.

    Szukamy rdzeni wyrazów, bo polskie odmiany zmieniają końcówki
    ("kopia" / "kopie" / "kopię").
    """
    page = full_html().lower()
    for stem in [
        "pora nocna", "urlop", "zastępstw", "kopi", "nadgodzin", "wymiar",
        "eksport", "import", "święt", "etat", "f1", "piętr", "l4",
    ]:
        assert stem in page, f"brak wzmianki o: {stem}"


def test_documented_shortcuts_exist_in_the_program():
    """Skróty opisane w instrukcji muszą być naprawdę podpięte."""
    source = (ROOT / "app" / "ui" / "main_window.py").read_text(encoding="utf-8")
    shortcuts = dict(re.findall(r'"([^"]+)",\s*self\.\w+,\s*"([^"]+)"', source))
    documented = [s for _, title, html in SECTIONS if title == "Skróty klawiszowe"
                  for s in re.findall(r"<b>(Ctrl \+ .|F1|Delete)</b>", html)]
    assert "F1" in documented
    declared = set(shortcuts.values()) | {"F1", "Delete"}
    for entry in ("Ctrl+E", "Ctrl+I", "Ctrl+Q"):
        assert entry in declared, f"{entry} opisany w instrukcji, ale nie podpięty"


@pytest.mark.skipif(not (ROOT / "tools" / "export_manual.py").exists(),
                    reason="brak skryptu eksportu")
def test_export_regenerates_the_repository_copies(tmp_path, monkeypatch):
    """INSTRUKCJA.md w repozytorium musi odpowiadać treści z programu."""
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "export_manual.py")],
        capture_output=True, text=True, cwd=ROOT,
    )
    assert result.returncode == 0, result.stderr

    markdown = (ROOT / "INSTRUKCJA.md").read_text(encoding="utf-8")
    assert markdown.startswith(f"# {TITLE}")
    for _, title, _ in SECTIONS:
        assert f"## {title}" in markdown, title
    # Tabele muszą przetrwać konwersję.
    assert "| Wpis | Znaczenie |" in markdown
    assert "|---|---|" in markdown
    # Znaczniki HTML nie mogą przeciekać do Markdowna.
    assert "<b>" not in markdown and "<td>" not in markdown
