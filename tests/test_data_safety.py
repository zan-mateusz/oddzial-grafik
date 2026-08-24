"""Testy ochrony danych przy aktualizacji programu.

Grafiki są jedynym niezastąpionym zasobem — plik programu można pobrać
ponownie, danych nie. Te testy pilnują, żeby aktualizacja ich nie naruszyła.
"""
import datetime as dt
import os
import sqlite3
import time

import pytest

from app import config
from app.db import Database, DatabaseTooNewError, SCHEMA_VERSION


def _old_database(path, version=1):
    """Baza w formacie sprzed podziału na piętra."""
    con = sqlite3.connect(path)
    con.executescript("""
        CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE employees(id INTEGER PRIMARY KEY AUTOINCREMENT,
          last_name TEXT NOT NULL, first_name TEXT NOT NULL DEFAULT '',
          position TEXT NOT NULL DEFAULT '', fte_num INTEGER NOT NULL DEFAULT 1,
          fte_den INTEGER NOT NULL DEFAULT 1, active INTEGER NOT NULL DEFAULT 1,
          sort_order INTEGER NOT NULL DEFAULT 0, hired_on TEXT, ended_on TEXT,
          notes TEXT NOT NULL DEFAULT '');
        CREATE TABLE entries(employee_id INTEGER NOT NULL, day TEXT NOT NULL,
          raw TEXT NOT NULL, PRIMARY KEY(employee_id, day));
        CREATE TABLE shift_types(id INTEGER PRIMARY KEY AUTOINCREMENT,
          code TEXT NOT NULL UNIQUE, name TEXT NOT NULL DEFAULT '', start_time TEXT,
          end_time TEXT, category TEXT NOT NULL DEFAULT 'praca',
          color TEXT NOT NULL DEFAULT '#E8EDF4', minutes_override INTEGER,
          sort_order INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE months(year INTEGER, month INTEGER, note TEXT DEFAULT '',
          locked INTEGER DEFAULT 0, PRIMARY KEY(year, month));
        INSERT INTO employees(last_name, first_name) VALUES('Kowalska','Anna');
        INSERT INTO entries VALUES(1,'2026-06-01','D'),(1,'2026-06-02','N');
    """)
    con.execute("INSERT INTO meta VALUES('schema_version', ?)", (str(version),))
    con.commit()
    con.close()
    return path


def test_updating_the_program_keeps_every_entry(tmp_path):
    """Nowa wersja programu otwierająca stary plik nie może zgubić grafików."""
    path = _old_database(tmp_path / "grafik.db")
    db = Database(path)
    assert db.month_entries(2026, 6) == {
        (1, dt.date(2026, 6, 1)): "D", (1, dt.date(2026, 6, 2)): "N",
    }
    assert [e["last_name"] for e in db.employees()] == ["Kowalska"]
    db.close()


def test_upgrade_leaves_an_untouched_copy_behind(tmp_path):
    path = _old_database(tmp_path / "grafik.db")
    db = Database(path)
    backup = db.last_upgrade_backup
    assert backup is not None and backup.exists()
    assert backup.parent.name == "kopie"

    # Kopia to nadal stary format, z kompletem danych.
    con = sqlite3.connect(backup)
    version = con.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
    assert version[0] == "1"
    assert con.execute("SELECT COUNT(*) FROM entries").fetchone()[0] == 2
    con.close()
    db.close()


def test_no_backup_is_made_when_nothing_changes(tmp_path):
    """Zwykłe uruchomienie bez zmiany formatu nie tworzy kopii aktualizacyjnej."""
    path = tmp_path / "grafik.db"
    Database(path).close()
    db = Database(path)
    assert db.last_upgrade_backup is None
    db.close()


def test_older_program_refuses_a_newer_file(tmp_path):
    """Starszy program nie może zapisywać do pliku nowszej wersji."""
    path = _old_database(tmp_path / "grafik.db", version=SCHEMA_VERSION + 5)
    with pytest.raises(DatabaseTooNewError) as excinfo:
        Database(path)
    message = str(excinfo.value)
    assert "nowszą wersję" in message
    assert "najnowszą wersję" in message


def test_refusing_a_newer_file_does_not_modify_it(tmp_path):
    path = _old_database(tmp_path / "grafik.db", version=SCHEMA_VERSION + 5)
    before = path.read_bytes()
    with pytest.raises(DatabaseTooNewError):
        Database(path)
    assert path.read_bytes() == before


def test_autobackup_creates_a_copy(tmp_path):
    db = Database(tmp_path / "grafik.db")
    db.add_employee("Kowalska", "Anna")
    backup = db.autobackup()
    assert backup is not None and backup.exists()
    db.close()


def test_autobackup_does_not_run_on_every_launch(tmp_path):
    db = Database(tmp_path / "grafik.db")
    db.add_employee("Kowalska", "Anna")
    assert db.autobackup() is not None
    assert db.autobackup() is None      # za wcześnie na kolejną
    db.close()


def test_autobackup_runs_again_once_the_copy_is_old(tmp_path):
    db = Database(tmp_path / "grafik.db")
    db.add_employee("Kowalska", "Anna")
    first = db.autobackup()
    old = time.time() - 5 * 86400
    os.utime(first, (old, old))
    assert db.autobackup() is not None
    db.close()


def test_autobackup_keeps_only_the_newest_copies(tmp_path):
    db = Database(tmp_path / "grafik.db")
    db.add_employee("Kowalska", "Anna")
    folder = tmp_path / "kopie"
    folder.mkdir(exist_ok=True)
    # Dwadzieścia starych kopii z różnych dni.
    for i in range(20):
        name = folder / f"auto_2020-01-{i + 1:02d}_1200.db"
        name.write_bytes(b"x")
        stamp = time.time() - (100 + i) * 86400
        os.utime(name, (stamp, stamp))

    db.autobackup(keep=15)
    remaining = sorted(folder.glob("auto_*.db"))
    assert len(remaining) == 15
    # Zachowane są najnowsze, łącznie z tą właśnie utworzoną.
    assert any(f.stat().st_size > 100 for f in remaining)
    db.close()


def test_autobackup_skips_an_empty_file(tmp_path):
    db = Database(tmp_path / "grafik.db")
    db.conn.commit()
    (tmp_path / "grafik.db").write_bytes(b"")
    assert db.autobackup() is None
    db.close()


def test_manual_backups_are_never_rotated_away(tmp_path):
    """Kopie robione ręcznie i przedaktualizacyjne muszą przetrwać sprzątanie."""
    db = Database(tmp_path / "grafik.db")
    db.add_employee("Kowalska", "Anna")
    folder = tmp_path / "kopie"
    folder.mkdir(exist_ok=True)
    manual = folder / "grafik_2026-01-01_1000.db"
    upgrade = folder / "przed_aktualizacja_1_2026-01-01_100000.db"
    for f in (manual, upgrade):
        f.write_bytes(b"x")
    for i in range(30):
        name = folder / f"auto_2020-02-{i + 1:02d}_1200.db"
        name.write_bytes(b"x")
        stamp = time.time() - (100 + i) * 86400
        os.utime(name, (stamp, stamp))

    db.autobackup(keep=5)
    assert manual.exists() and upgrade.exists()
    db.close()


def test_data_directory_is_outside_the_program_folder(tmp_path):
    """Dane nie mogą leżeć obok pliku .exe — aktualizacja by je nadpisała."""
    data = config.data_dir()
    assert data.is_absolute()
    assert "AppData" in str(data) or "Application Support" in str(data) \
        or ".local" in str(data)
    assert config.db_path().parent == data
    assert config.backup_dir().parent == data
