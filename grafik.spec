# -*- mode: python ; coding: utf-8 -*-
"""Konfiguracja PyInstallera.

Buduje dwie postacie programu:
  * dist/Grafik/Grafik.exe        — katalog aplikacji, pod instalator (szybki start)
  * dist/Grafik-przenosny.exe     — jeden plik, do uruchomienia bez instalacji
"""

import os

ICON = os.path.join("packaging", "grafik.ico")
VERSION_FILE = os.path.join("packaging", "version_info.txt")

# Moduły Qt, których program nie używa — ich wycięcie znacząco zmniejsza paczkę.
EXCLUDED_QT = [
    "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtQuick3D", "PySide6.QtQuickWidgets",
    "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtWebChannel",
    "PySide6.QtMultimedia", "PySide6.QtMultimediaWidgets", "PySide6.Qt3DCore",
    "PySide6.Qt3DRender", "PySide6.QtCharts", "PySide6.QtDataVisualization",
    "PySide6.QtBluetooth", "PySide6.QtNfc", "PySide6.QtPositioning",
    "PySide6.QtSql", "PySide6.QtTest", "PySide6.QtDesigner", "PySide6.QtHelp",
    "PySide6.QtOpenGL", "PySide6.QtOpenGLWidgets", "PySide6.QtSerialPort",
]

a = Analysis(
    ["app/__main__.py"],
    pathex=[],
    binaries=[],
    datas=[],
    # OCR jest opcjonalny — dociągamy go, jeśli jest dostępny w środowisku budowania.
    hiddenimports=["app.io.ocr", "odf.opendocument", "odf.table", "odf.text"],
    hookspath=[],
    runtime_hooks=[],
    excludes=EXCLUDED_QT + ["tkinter", "matplotlib", "numpy", "scipy", "pandas", "pytest"],
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data)

common = dict(
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,                       # bez okna konsoli
    icon=ICON if os.path.exists(ICON) else None,
    version=VERSION_FILE if os.path.exists(VERSION_FILE) else None,
)

# 1) Wersja katalogowa — trafia do instalatora. Uruchamia się od razu.
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="Grafik",
    **common,
)
coll = COLLECT(
    exe, a.binaries, a.zipfiles, a.datas,
    strip=False, upx=False, upx_exclude=[],
    name="Grafik",
)

# 2) Wersja przenośna — wszystko w jednym pliku .exe, bez instalacji.
#    Startuje wolniej, bo przy każdym uruchomieniu rozpakowuje się do katalogu
#    tymczasowego, ale można ją trzymać na pulpicie albo na pendrivie.
exe_portable = EXE(
    pyz, a.scripts, a.binaries, a.zipfiles, a.datas, [],
    name="Grafik-przenosny",
    runtime_tmpdir=None,
    **common,
)
