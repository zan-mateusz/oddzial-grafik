"""Odczyt tabeli grafiku ze zdjęcia (OCR).

Funkcja opcjonalna — wymaga zainstalowanego silnika Tesseract. Zdjęcie nigdy nie
będzie odczytane bezbłędnie, dlatego wynik trafia do zwykłego kreatora importu,
gdzie wszystko widać i można poprawić przed zapisaniem.
"""
from __future__ import annotations

import shutil
import statistics
from pathlib import Path

from app.io.xlsx_import import SheetGrid

# Segmentacja automatyczna (--psm 3). Wymuszanie trybu "jednolity blok" (--psm 6)
# sprawdzono i daje gorsze wyniki: wiersze tabeli zlewają się ze sobą.
# preserve_interword_spaces pomaga rozdzielić wąskie komórki grafiku.
OCR_CONFIG = "-c preserve_interword_spaces=1"

INSTALL_HINT_WINDOWS = (
    "Aby wczytywać grafik ze zdjęcia, zainstaluj program Tesseract OCR:\n\n"
    "1. Pobierz instalator ze strony\n"
    "   https://github.com/UB-Mannheim/tesseract/wiki\n"
    "2. Podczas instalacji zaznacz język polski (Polish).\n"
    "3. Uruchom ponownie ten program.\n\n"
    "Import z pliku Excel działa bez tego dodatku."
)
INSTALL_HINT_MAC = (
    "Aby wczytywać grafik ze zdjęcia, zainstaluj Tesseract:\n\n"
    "    brew install tesseract tesseract-lang\n\n"
    "Import z pliku Excel działa bez tego dodatku."
)


def check_available() -> tuple[bool, str]:
    """Czy import ze zdjęcia jest gotowy do użycia."""
    try:
        import pytesseract  # noqa: F401
    except ImportError:
        return False, _hint("Brak modułu pytesseract.")
    if shutil.which("tesseract") is None and not _windows_tesseract():
        return False, _hint("Nie znaleziono silnika Tesseract OCR.")
    return True, "Import ze zdjęcia jest dostępny."


def _hint(reason: str) -> str:
    import sys
    tail = INSTALL_HINT_WINDOWS if sys.platform == "win32" else INSTALL_HINT_MAC
    return f"{reason}\n\n{tail}"


def _windows_tesseract() -> str | None:
    """Typowa lokalizacja instalatora na Windows — ustawiana automatycznie."""
    import sys
    if sys.platform != "win32":
        return None
    candidates = [
        Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
        Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
    ]
    for path in candidates:
        if path.exists():
            import pytesseract

            pytesseract.pytesseract.tesseract_cmd = str(path)
            return str(path)
    return None


def _preprocess(image):
    """Skala szarości, wyostrzenie i podbicie kontrastu — OCR z telefonu."""
    from PIL import ImageEnhance, ImageOps
    image = ImageOps.exif_transpose(image)
    image = image.convert("L")
    image = ImageOps.autocontrast(image, cutoff=2)
    image = ImageEnhance.Sharpness(image).enhance(1.6)
    # Tesseract działa najlepiej przy wysokości znaku ok. 30 px.
    if image.width < 2000:
        scale = 2000 / image.width
        image = image.resize(
            (int(image.width * scale), int(image.height * scale))
        )
    return image


def read_photo_grid(path: str | Path, lang: str = "pol+eng") -> SheetGrid:
    """Rozpoznaje tekst na zdjęciu i układa go z powrotem w siatkę wierszy i kolumn."""
    import pytesseract
    from PIL import Image

    _windows_tesseract()
    image = _preprocess(Image.open(path))

    try:
        data = pytesseract.image_to_data(
            image, lang=lang, config=OCR_CONFIG, output_type=pytesseract.Output.DICT
        )
    except pytesseract.TesseractError:
        # Brak polskiego pakietu językowego — próbujemy domyślnym.
        data = pytesseract.image_to_data(
            image, config=OCR_CONFIG, output_type=pytesseract.Output.DICT
        )

    words = _collect_words(data)
    if not words:
        raise ValueError(
            "Nie rozpoznano żadnego tekstu na zdjęciu.\n\n"
            "Zrób zdjęcie prosto z góry, w dobrym świetle, tak aby cała tabela "
            "była ostra i mieściła się w kadrze."
        )

    rows = _cluster_rows(words)
    cells = _build_grid(rows)
    return SheetGrid(name=f"Zdjęcie: {Path(path).name}", cells=cells)


# Linie siatki tabeli Tesseract odczytuje jako te znaki — trzeba je odciąć,
# inaczej trafiają do treści komórek ("[U", "D|D").
# Uwaga: myślnik NIE jest tu wymieniony — rozdziela godziny w zapisach "8-14".
_BORDER_CHARS = "|[]{}()_=<>*\\¦│┃"


def _split_token(text: str) -> list[tuple[str, float, float]]:
    """Dzieli odczytane słowo na fragmenty rozdzielone liniami tabeli.

    Tesseract często zwraca dwie sąsiednie komórki jako jedno słowo ("D|D").
    Zwraca listę (tekst, początek, koniec) — położenia jako ułamek szerokości
    pierwotnego prostokąta, żeby dało się odtworzyć pozycję każdego fragmentu.
    """
    if not text:
        return []
    parts: list[tuple[str, float, float]] = []
    n = len(text)
    start = None
    for i, ch in enumerate(text + " "):
        if i < n and ch not in _BORDER_CHARS and not ch.isspace():
            if start is None:
                start = i
        elif start is not None:
            piece = text[start:i]
            if any(c.isalnum() for c in piece):
                parts.append((piece, start / n, i / n))
            start = None
    return parts


def _collect_words(data: dict) -> list[dict]:
    words = []
    for i, raw in enumerate(data["text"]):
        try:
            conf = float(data["conf"][i])
        except (TypeError, ValueError):
            conf = -1.0
        if conf < 30:
            continue
        left, top = data["left"][i], data["top"][i]
        width, height = data["width"][i], data["height"][i]
        for text, frac_a, frac_b in _split_token((raw or "").strip()):
            part_left = left + width * frac_a
            part_width = max(1.0, width * (frac_b - frac_a))
            words.append({
                "text": text,
                "left": part_left,
                "top": top,
                "width": part_width,
                "height": height,
                "center_x": part_left + part_width / 2,
                "center_y": top + height / 2,
            })
    return words


def _cluster_rows(words: list[dict]) -> list[list[dict]]:
    """Grupuje słowa w wiersze na podstawie pionowego położenia."""
    heights = [w["height"] for w in words]
    tolerance = max(8, statistics.median(heights) * 0.6)
    rows: list[list[dict]] = []
    for word in sorted(words, key=lambda w: w["center_y"]):
        for row in reversed(rows):
            if abs(row[0]["center_y"] - word["center_y"]) <= tolerance:
                row.append(word)
                break
        else:
            rows.append([word])
    for row in rows:
        row.sort(key=lambda w: w["left"])
    return rows


def _build_grid(rows: list[list[dict]]) -> list[list[str]]:
    """Wyznacza wspólne kolumny dla wszystkich wierszy i wypełnia siatkę.

    Najpierw szukamy wiersza z numerami dni (1, 2, 3...). Jego pozycje wyznaczają
    kolumny znacznie pewniej niż odstępy między słowami, bo w tabeli grafiku
    sąsiednie komórki bywają odległe zaledwie o kilka pikseli.
    """
    anchors = _anchors_from_day_row(rows) or _anchors_from_spacing(rows)

    grid: list[list[str]] = []
    for row in rows:
        cells = [""] * len(anchors)
        for word in row:
            idx = min(
                range(len(anchors)), key=lambda i: abs(anchors[i] - word["center_x"])
            )
            cells[idx] = f"{cells[idx]} {word['text']}".strip()
        grid.append(cells)
    return grid


def _anchors_from_day_row(rows: list[list[dict]]) -> list[float] | None:
    """Kolumny odczytane z wiersza zawierającego kolejne numery dni miesiąca."""
    best: list[dict] | None = None
    for row in rows:
        days = []
        for word in row:
            text = word["text"].strip()
            if text.isdigit() and 1 <= int(text) <= 31:
                days.append((int(text), word))
        # Numery muszą rosnąć od lewej do prawej i pokrywać większość miesiąca.
        ascending = [w for i, (n, w) in enumerate(days) if n == i + 1]
        if len(ascending) >= 15 and (best is None or len(ascending) > len(best)):
            best = ascending
    if best is None:
        return None

    anchors = [w["center_x"] for w in best]
    # Kolumny na lewo od pierwszego dnia mieszczą nazwiska — dokładamy je,
    # zachowując typowy odstęp kolumn.
    step = statistics.median(
        [b - a for a, b in zip(anchors, anchors[1:])] or [40]
    )
    left = anchors[0] - step
    extra = []
    while left > step / 2:
        extra.append(left)
        left -= step * 3
    return sorted(extra) + anchors


def _anchors_from_spacing(rows: list[list[dict]]) -> list[float]:
    """Awaryjne grupowanie kolumn po odstępach — gdy nie ma wiersza z dniami."""
    all_words = [w for row in rows for w in row]
    widths = [w["width"] for w in all_words]
    gap = max(12, statistics.median(widths) * 0.9)

    centers = sorted(w["center_x"] for w in all_words)
    columns: list[list[float]] = []
    for x in centers:
        if columns and x - columns[-1][-1] <= gap:
            columns[-1].append(x)
        else:
            columns.append([x])
    return [statistics.mean(c) for c in columns]
