"""Ścieżki aplikacji — te same na Windows i macOS."""
from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "Grafik"


def data_dir() -> Path:
    """Katalog na bazę danych i kopie zapasowe."""
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    path = base / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def db_path() -> Path:
    return data_dir() / "grafik.db"


def backup_dir() -> Path:
    path = data_dir() / "kopie"
    path.mkdir(parents=True, exist_ok=True)
    return path


def documents_dir() -> Path:
    candidate = Path.home() / "Documents"
    return candidate if candidate.exists() else Path.home()
