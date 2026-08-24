"""Sprawdzanie i pobieranie aktualizacji programu.

Nowe wersje publikowane są jako wydania na GitHubie. Program odpytuje publiczne
API — bez logowania i bez żadnych danych dostępowych zaszytych w pliku .exe.
Pobrany plik jest sprawdzany sumą kontrolną, zanim zostanie uruchomiony.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from app.version import __version__

TIMEOUT = 15
USER_AGENT = f"Grafik/{__version__}"
CHECKSUM_ASSET = "SHA256SUMS.txt"
DEFAULT_REPO = ""          # np. "mati/grafik" — ustawiane w ustawieniach programu

# Wzorce nazw plików w wydaniu.
INSTALLER_PATTERN = re.compile(r"instalator.*\.exe$", re.I)
PORTABLE_PATTERN = re.compile(r"przenosny.*\.exe$", re.I)


class UpdateError(RuntimeError):
    """Błąd, którego treść można pokazać użytkownikowi."""


# --- wersje ----------------------------------------------------------------

def parse_version(text: str) -> tuple[int, ...]:
    """"v1.2.3" -> (1, 2, 3). Człony nieliczbowe są pomijane."""
    cleaned = (text or "").strip().lstrip("vV")
    parts: list[int] = []
    for chunk in cleaned.split("."):
        match = re.match(r"\d+", chunk)
        if not match:
            break
        parts.append(int(match.group()))
    return tuple(parts) or (0,)


def is_newer(candidate: str, current: str = __version__) -> bool:
    """Czy `candidate` jest nowszy niż `current`."""
    a, b = parse_version(candidate), parse_version(current)
    length = max(len(a), len(b))
    a += (0,) * (length - len(a))
    b += (0,) * (length - len(b))
    return a > b


# --- rodzaj instalacji ------------------------------------------------------

def install_kind() -> str:
    """Zwraca "installer", "portable" albo "source"."""
    if not getattr(sys, "frozen", False):
        return "source"
    bundle = getattr(sys, "_MEIPASS", None)
    if bundle is None:
        return "installer"
    # W wersji jednoplikowej zasoby lądują w katalogu tymczasowym, oddzielnie
    # od samego pliku .exe; w wersji katalogowej leżą tuż obok niego.
    try:
        return (
            "installer"
            if Path(bundle).parent == Path(sys.executable).parent
            else "portable"
        )
    except (OSError, ValueError):
        return "portable"


def can_self_update() -> bool:
    return install_kind() in ("installer", "portable")


# --- odpytanie serwisu ------------------------------------------------------

@dataclass(frozen=True)
class Release:
    version: str
    notes: str
    download_url: str
    filename: str
    size: int = 0
    checksum_url: str = ""

    @property
    def size_mb(self) -> float:
        return self.size / (1024 * 1024)


def _fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise UpdateError(
                "Nie znaleziono żadnego wydania programu pod podanym adresem.\n"
                "Sprawdź ustawienia aktualizacji."
            ) from exc
        if exc.code == 403:
            raise UpdateError(
                "Serwis chwilowo odmówił odpowiedzi (zbyt wiele zapytań).\n"
                "Spróbuj ponownie za kilkanaście minut."
            ) from exc
        raise UpdateError(f"Serwer odpowiedział błędem {exc.code}.") from exc
    except urllib.error.URLError as exc:
        raise UpdateError(
            "Nie udało się połączyć z internetem.\n"
            "Sprawdź połączenie i spróbuj ponownie."
        ) from exc
    except TimeoutError as exc:
        raise UpdateError("Serwer nie odpowiedział na czas.") from exc


def latest_release(repo: str, kind: str | None = None) -> Release | None:
    """Pobiera opis najnowszego wydania z GitHuba."""
    repo = (repo or "").strip().strip("/")
    if not repo or "/" not in repo:
        raise UpdateError(
            "Nie ustawiono, skąd pobierać aktualizacje.\n"
            "Uzupełnij pole w Narzędzia → Ustawienia."
        )
    kind = kind or install_kind()
    url = f"https://api.github.com/repos/{repo}/releases/latest"
    try:
        data = json.loads(_fetch(url))
    except json.JSONDecodeError as exc:
        raise UpdateError("Serwer zwrócił nieczytelną odpowiedź.") from exc

    version = str(data.get("tag_name") or "").lstrip("vV")
    if not version:
        return None

    wanted = PORTABLE_PATTERN if kind == "portable" else INSTALLER_PATTERN
    chosen = checksums = None
    for asset in data.get("assets") or []:
        name = str(asset.get("name") or "")
        if name == CHECKSUM_ASSET:
            checksums = asset.get("browser_download_url") or ""
        elif chosen is None and wanted.search(name):
            chosen = asset
    if chosen is None:
        raise UpdateError(
            f"Wydanie {version} nie zawiera pliku pasującego do tej wersji "
            "programu. Pobierz aktualizację ręcznie."
        )
    return Release(
        version=version,
        notes=str(data.get("body") or "").strip(),
        download_url=str(chosen.get("browser_download_url") or ""),
        filename=str(chosen.get("name") or "aktualizacja.exe"),
        size=int(chosen.get("size") or 0),
        checksum_url=checksums or "",
    )


def check_for_update(repo: str) -> Release | None:
    """Zwraca opis wydania, jeśli jest nowsze od bieżącego. Inaczej None."""
    release = latest_release(repo)
    if release is None or not is_newer(release.version):
        return None
    return release


# --- pobieranie -------------------------------------------------------------

def expected_checksum(checksum_url: str, filename: str) -> str | None:
    """Odczytuje sumę kontrolną pliku z listy SHA256SUMS.txt."""
    if not checksum_url:
        return None
    try:
        text = _fetch(checksum_url).decode("utf-8", "replace")
    except UpdateError:
        return None
    for line in text.splitlines():
        parts = line.split()
        if len(parts) >= 2 and Path(parts[-1].lstrip("*")).name == filename:
            return parts[0].lower()
    return None


def download(
    release: Release, target_dir: Path, progress=None, cancelled=None
) -> Path:
    """Pobiera plik wydania i sprawdza jego sumę kontrolną.

    `progress` dostaje (pobrane_bajty, wszystkie_bajty); `cancelled` to funkcja
    zwracająca True, gdy użytkownik przerwał pobieranie.
    """
    target_dir = Path(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / release.filename
    partial = target.with_suffix(target.suffix + ".part")

    request = urllib.request.Request(
        release.download_url, headers={"User-Agent": USER_AGENT}
    )
    digest = hashlib.sha256()
    downloaded = 0
    aborted = False
    # Windows nie pozwala usunąć pliku, dopóki jest otwarty, więc plik
    # tymczasowy kasujemy dopiero po zamknięciu uchwytu.
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            total = int(response.headers.get("Content-Length") or release.size or 0)
            with open(partial, "wb") as handle:
                while True:
                    if cancelled is not None and cancelled():
                        aborted = True
                        break
                    chunk = response.read(256 * 1024)
                    if not chunk:
                        break
                    handle.write(chunk)
                    digest.update(chunk)
                    downloaded += len(chunk)
                    if progress is not None:
                        progress(downloaded, total)
    except urllib.error.URLError as exc:
        partial.unlink(missing_ok=True)
        raise UpdateError(
            "Pobieranie nie powiodło się — sprawdź połączenie z internetem."
        ) from exc

    if aborted:
        partial.unlink(missing_ok=True)
        raise UpdateError("Pobieranie zostało przerwane.")

    wanted = expected_checksum(release.checksum_url, release.filename)
    if wanted and digest.hexdigest().lower() != wanted:
        partial.unlink(missing_ok=True)
        raise UpdateError(
            "Pobrany plik nie zgadza się z sumą kontrolną wydania i nie "
            "zostanie uruchomiony.\n\nSpróbuj ponownie; jeśli błąd się "
            "powtórzy, pobierz aktualizację ręcznie."
        )

    target.unlink(missing_ok=True)
    partial.replace(target)
    return target


# --- uruchomienie instalatora ----------------------------------------------

def run_installer(path: Path) -> None:
    """Uruchamia instalator i pozostawia go działającego po zamknięciu programu."""
    path = Path(path)
    if not path.exists():
        raise UpdateError("Nie znaleziono pobranego pliku instalatora.")
    if sys.platform != "win32":
        raise UpdateError(
            "Automatyczna instalacja działa tylko w systemie Windows.\n"
            f"Pobrany plik: {path}"
        )
    creation_flags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(
        subprocess, "CREATE_NEW_PROCESS_GROUP", 0
    )
    try:
        subprocess.Popen(
            [str(path), "/SILENT", "/NOCANCEL", "/RESTARTAPPLICATIONS"],
            close_fds=True,
            creationflags=creation_flags,
        )
    except OSError as exc:
        raise UpdateError(f"Nie udało się uruchomić instalatora:\n{exc}") from exc


def reveal(path: Path) -> None:
    """Otwiera katalog z pobranym plikiem — dla wersji przenośnej."""
    folder = Path(path).parent
    try:
        if sys.platform == "win32":
            subprocess.Popen(["explorer", str(folder)])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(folder)])
        else:
            subprocess.Popen(["xdg-open", str(folder)])
    except OSError:
        pass
