"""Warstwa danych — SQLite. Jeden plik = cała historia grafików."""
from __future__ import annotations

import datetime as dt
import shutil
import sqlite3
from pathlib import Path

from app.core.shifts import DEFAULT_SHIFT_TYPES, Category, ShiftType

SCHEMA_VERSION = 2

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- Piętra (oddziały) prowadzone w jednym pliku. Pracownik ma piętro macierzyste,
-- ale pojedynczy dyżur może być odbyty na innym — to zastępstwo.
CREATE TABLE IF NOT EXISTS floors (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS employees (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    last_name   TEXT NOT NULL,
    first_name  TEXT NOT NULL DEFAULT '',
    position    TEXT NOT NULL DEFAULT '',
    fte_num     INTEGER NOT NULL DEFAULT 1,
    fte_den     INTEGER NOT NULL DEFAULT 1,
    active      INTEGER NOT NULL DEFAULT 1,
    sort_order  INTEGER NOT NULL DEFAULT 0,
    hired_on    TEXT,
    ended_on    TEXT,
    notes       TEXT NOT NULL DEFAULT '',
    floor_id    INTEGER REFERENCES floors(id)
);

CREATE TABLE IF NOT EXISTS shift_types (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    code             TEXT NOT NULL UNIQUE,
    name             TEXT NOT NULL DEFAULT '',
    start_time       TEXT,
    end_time         TEXT,
    category         TEXT NOT NULL DEFAULT 'praca',
    color            TEXT NOT NULL DEFAULT '#E8EDF4',
    minutes_override INTEGER,
    sort_order       INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS entries (
    employee_id INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    day         TEXT NOT NULL,
    raw         TEXT NOT NULL,
    -- Piętro, na którym dyżur został faktycznie odbyty.
    floor_id    INTEGER REFERENCES floors(id),
    PRIMARY KEY (employee_id, day)
);

CREATE INDEX IF NOT EXISTS idx_entries_day ON entries(day);

-- Miesiące zatwierdzone / opisane przez użytkownika.
CREATE TABLE IF NOT EXISTS months (
    year   INTEGER NOT NULL,
    month  INTEGER NOT NULL,
    note   TEXT NOT NULL DEFAULT '',
    locked INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (year, month)
);
"""


def _adapt_time(t: dt.time | None) -> str | None:
    return t.strftime("%H:%M") if t is not None else None


def _parse_time(s: str | None) -> dt.time | None:
    if not s:
        return None
    hh, mm = s.split(":")
    return dt.time(int(hh), int(mm))


class DatabaseTooNewError(RuntimeError):
    """Plik danych pochodzi z nowszej wersji programu."""

    def __init__(self, found: int, supported: int):
        self.found = found
        self.supported = supported
        super().__init__(
            f"Plik z grafikami został zapisany przez nowszą wersję programu "
            f"(format {found}, ta wersja obsługuje {supported}).\n\n"
            "Zainstaluj najnowszą wersję Grafiku. Otwarcie pliku starszym "
            "programem mogłoby uszkodzić zapisane dane."
        )


class Database:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.last_upgrade_backup: Path | None = None
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        # Wersję sprawdzamy przed jakimkolwiek zapisem — starszy program nie może
        # nawet dotknąć pliku zapisanego przez nowszą wersję.
        existing = self._stored_version()
        if existing is not None and existing > SCHEMA_VERSION:
            self.conn.close()
            raise DatabaseTooNewError(existing, SCHEMA_VERSION)
        self.conn.executescript(SCHEMA)
        self._init_meta(existing)
        self.conn.commit()

    def _stored_version(self) -> int | None:
        """Wersja formatu zapisana w pliku; None dla nowego lub pustego pliku."""
        try:
            row = self.conn.execute(
                "SELECT value FROM meta WHERE key='schema_version'"
            ).fetchone()
        except sqlite3.OperationalError:
            return None            # brak tabeli meta — plik jeszcze nie istnieje
        if row is None:
            return None
        try:
            return int(row["value"])
        except (TypeError, ValueError):
            return None

    def _init_meta(self, existing: int | None) -> None:
        if existing is None:
            self.conn.execute(
                "INSERT INTO meta(key, value) VALUES('schema_version', ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (str(SCHEMA_VERSION),),
            )
            self.seed_shift_types()
            self.seed_floors()
        else:
            self._migrate(existing)

    def backup_before_upgrade(self, version: int) -> Path | None:
        """Kopiuje plik danych przed zmianą jego formatu.

        Aktualizacja programu potrafi przebudować bazę. Gdyby coś poszło nie
        tak, nietknięta kopia sprzed zmiany zostaje obok.
        """
        if not self.path.exists() or self.path.stat().st_size == 0:
            return None
        stamp = dt.datetime.now().strftime("%Y-%m-%d_%H%M%S")
        target = self.path.parent / "kopie" / f"przed_aktualizacja_{version}_{stamp}.db"
        target.parent.mkdir(parents=True, exist_ok=True)
        self.conn.commit()
        shutil.copy2(self.path, target)
        return target

    def autobackup(self, keep: int = 15, min_interval_days: int = 2) -> Path | None:
        """Okresowa kopia zapasowa robiona przy uruchomieniu programu.

        Użytkownik nie musi o niczym pamiętać, a w razie pomyłki jest do czego
        wrócić. Starsze kopie są kasowane, żeby katalog nie rósł bez końca.
        """
        if not self.path.exists() or self.path.stat().st_size == 0:
            return None
        folder = self.path.parent / "kopie"
        folder.mkdir(parents=True, exist_ok=True)

        existing = sorted(folder.glob("auto_*.db"))
        if existing:
            newest = max(f.stat().st_mtime for f in existing)
            age_days = (dt.datetime.now().timestamp() - newest) / 86400
            if age_days < min_interval_days:
                return None

        stamp = dt.datetime.now().strftime("%Y-%m-%d_%H%M")
        target = folder / f"auto_{stamp}.db"
        self.conn.commit()
        shutil.copy2(self.path, target)

        for old in sorted(folder.glob("auto_*.db"))[:-keep]:
            old.unlink(missing_ok=True)
        return target

    def _migrate(self, version: int) -> None:
        """Uaktualnia starszą bazę bez utraty danych."""
        if version == SCHEMA_VERSION:
            return
        self.last_upgrade_backup = self.backup_before_upgrade(version)
        if version < 2:
            self._add_column("employees", "floor_id", "INTEGER REFERENCES floors(id)")
            self._add_column("entries", "floor_id", "INTEGER REFERENCES floors(id)")
            self.seed_floors()
            default = self.floors()[0]["id"]
            # Dotychczasowe dane pochodzą sprzed podziału na piętra.
            self.conn.execute(
                "UPDATE employees SET floor_id=? WHERE floor_id IS NULL", (default,)
            )
            self.conn.execute(
                "UPDATE entries SET floor_id=(SELECT floor_id FROM employees "
                "WHERE employees.id = entries.employee_id) WHERE floor_id IS NULL"
            )
        self.conn.execute(
            "UPDATE meta SET value=? WHERE key='schema_version'", (str(SCHEMA_VERSION),)
        )
        self.conn.commit()

    def _add_column(self, table: str, column: str, definition: str) -> None:
        existing = {
            r["name"] for r in self.conn.execute(f"PRAGMA table_info({table})")
        }
        if column not in existing:
            self.conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    # --- piętra -------------------------------------------------------------

    def seed_floors(self) -> None:
        if self.conn.execute("SELECT 1 FROM floors LIMIT 1").fetchone():
            return
        for i, name in enumerate(("I piętro", "II piętro")):
            self.conn.execute(
                "INSERT INTO floors(name, sort_order) VALUES(?,?)", (name, i)
            )
        self.conn.commit()

    def floors(self) -> list[sqlite3.Row]:
        return list(self.conn.execute(
            "SELECT * FROM floors ORDER BY sort_order, id"
        ).fetchall())

    def floor_name(self, floor_id: int | None) -> str:
        if floor_id is None:
            return ""
        row = self.conn.execute(
            "SELECT name FROM floors WHERE id=?", (floor_id,)
        ).fetchone()
        return row["name"] if row else ""

    def add_floor(self, name: str) -> int:
        cur = self.conn.execute(
            "INSERT INTO floors(name, sort_order) VALUES(?, "
            "(SELECT COALESCE(MAX(sort_order)+1,0) FROM floors))",
            (name,),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def rename_floor(self, floor_id: int, name: str) -> None:
        self.conn.execute("UPDATE floors SET name=? WHERE id=?", (name, floor_id))
        self.conn.commit()

    def delete_floor(self, floor_id: int) -> None:
        """Usuwa piętro; pracownicy i dyżury zostają bez przypisania."""
        self.conn.execute(
            "UPDATE employees SET floor_id=NULL WHERE floor_id=?", (floor_id,)
        )
        self.conn.execute(
            "UPDATE entries SET floor_id=NULL WHERE floor_id=?", (floor_id,)
        )
        self.conn.execute("DELETE FROM floors WHERE id=?", (floor_id,))
        self.conn.commit()

    def close(self) -> None:
        self.conn.commit()
        self.conn.close()

    # --- ustawienia ---------------------------------------------------------

    def get_setting(self, key: str, default: str = "") -> str:
        row = self.conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default

    def set_setting(self, key: str, value: str) -> None:
        self.conn.execute(
            "INSERT INTO meta(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )
        self.conn.commit()

    # --- typy zmian ---------------------------------------------------------

    def seed_shift_types(self) -> None:
        for i, st in enumerate(DEFAULT_SHIFT_TYPES):
            self.conn.execute(
                "INSERT OR IGNORE INTO shift_types"
                "(code, name, start_time, end_time, category, color, minutes_override, sort_order)"
                " VALUES(?,?,?,?,?,?,?,?)",
                (st.code, st.name, _adapt_time(st.start), _adapt_time(st.end),
                 st.category.value, st.color, st.minutes_override, i),
            )

    def shift_types(self) -> list[ShiftType]:
        rows = self.conn.execute(
            "SELECT * FROM shift_types ORDER BY sort_order, code"
        ).fetchall()
        return [
            ShiftType(
                id=r["id"],
                code=r["code"],
                name=r["name"],
                start=_parse_time(r["start_time"]),
                end=_parse_time(r["end_time"]),
                category=Category(r["category"]),
                color=r["color"],
                minutes_override=r["minutes_override"],
            )
            for r in rows
        ]

    def shift_types_by_code(self) -> dict[str, ShiftType]:
        return {st.code.upper(): st for st in self.shift_types()}

    def save_shift_type(self, st: ShiftType) -> int:
        if st.id is None:
            cur = self.conn.execute(
                "INSERT INTO shift_types"
                "(code, name, start_time, end_time, category, color, minutes_override, sort_order)"
                " VALUES(?,?,?,?,?,?,?, (SELECT COALESCE(MAX(sort_order)+1,0) FROM shift_types))",
                (st.code, st.name, _adapt_time(st.start), _adapt_time(st.end),
                 st.category.value, st.color, st.minutes_override),
            )
            self.conn.commit()
            return int(cur.lastrowid)
        self.conn.execute(
            "UPDATE shift_types SET code=?, name=?, start_time=?, end_time=?, "
            "category=?, color=?, minutes_override=? WHERE id=?",
            (st.code, st.name, _adapt_time(st.start), _adapt_time(st.end),
             st.category.value, st.color, st.minutes_override, st.id),
        )
        self.conn.commit()
        return st.id

    def delete_shift_type(self, type_id: int) -> None:
        self.conn.execute("DELETE FROM shift_types WHERE id=?", (type_id,))
        self.conn.commit()

    # --- pracownicy ---------------------------------------------------------

    def employees(
        self, include_inactive: bool = False, floor_id: int | None = None
    ) -> list[sqlite3.Row]:
        clauses, params = [], []
        if not include_inactive:
            clauses.append("active=1")
        if floor_id is not None:
            clauses.append("floor_id=?")
            params.append(floor_id)
        sql = "SELECT * FROM employees"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY sort_order, last_name, first_name"
        return list(self.conn.execute(sql, params).fetchall())

    def employees_for_month(
        self, year: int, month: int, floor_id: int | None = None
    ) -> list[sqlite3.Row]:
        """Pracownicy widoczni w grafiku danego miesiąca.

        Zachowuje historię — dawne grafiki nadal pokazują osoby, które już nie
        pracują. Przy wskazanym piętrze dochodzą osoby z innych pięter, które
        mają tu dyżur (zastępstwo).
        """
        first, last_s = self._month_bounds(year, month)
        base = (
            "(hired_on IS NULL OR hired_on <= ?) AND (ended_on IS NULL OR ended_on >= ?) "
            "AND (active=1 OR id IN (SELECT employee_id FROM entries "
            "WHERE day BETWEEN ? AND ?))"
        )
        params = [last_s, first, first, last_s]
        if floor_id is not None:
            base += (
                " AND (floor_id=? OR id IN (SELECT employee_id FROM entries "
                "WHERE day BETWEEN ? AND ? AND floor_id=?))"
            )
            params += [floor_id, first, last_s, floor_id]
        return list(self.conn.execute(
            f"SELECT * FROM employees WHERE {base} "
            "ORDER BY sort_order, last_name, first_name",
            params,
        ).fetchall())

    def _month_bounds(self, year: int, month: int) -> tuple[str, str]:
        first = dt.date(year, month, 1)
        last = (dt.date(year + 1, 1, 1) if month == 12
                else dt.date(year, month + 1, 1)) - dt.timedelta(days=1)
        return first.isoformat(), last.isoformat()

    def add_employee(self, last_name: str, first_name: str = "", position: str = "",
                     fte_num: int = 1, fte_den: int = 1, hired_on: str | None = None,
                     floor_id: int | None = None) -> int:
        if floor_id is None:
            floors = self.floors()
            floor_id = floors[0]["id"] if floors else None
        cur = self.conn.execute(
            "INSERT INTO employees(last_name, first_name, position, fte_num, fte_den, "
            "hired_on, floor_id, sort_order) VALUES(?,?,?,?,?,?,?, "
            "(SELECT COALESCE(MAX(sort_order)+1,0) FROM employees))",
            (last_name, first_name, position, fte_num, fte_den, hired_on, floor_id),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def update_employee(self, emp_id: int, **fields) -> None:
        allowed = {"last_name", "first_name", "position", "fte_num", "fte_den",
                   "active", "sort_order", "hired_on", "ended_on", "notes", "floor_id"}
        sets = {k: v for k, v in fields.items() if k in allowed}
        if not sets:
            return
        clause = ", ".join(f"{k}=?" for k in sets)
        self.conn.execute(
            f"UPDATE employees SET {clause} WHERE id=?", (*sets.values(), emp_id)
        )
        self.conn.commit()

    def delete_employee(self, emp_id: int) -> None:
        """Trwale usuwa pracownika wraz z wpisami. Zwykle lepiej dezaktywować."""
        self.conn.execute("DELETE FROM employees WHERE id=?", (emp_id,))
        self.conn.commit()

    def deactivate_employee(self, emp_id: int, ended_on: str | None = None) -> None:
        self.conn.execute(
            "UPDATE employees SET active=0, ended_on=COALESCE(?, ended_on) WHERE id=?",
            (ended_on, emp_id),
        )
        self.conn.commit()

    def reorder_employees(self, ordered_ids: list[int]) -> None:
        self.conn.executemany(
            "UPDATE employees SET sort_order=? WHERE id=?",
            [(i, e) for i, e in enumerate(ordered_ids)],
        )
        self.conn.commit()

    # --- wpisy grafiku ------------------------------------------------------

    def month_entries(
        self, year: int, month: int, floor_id: int | None = None
    ) -> dict[tuple[int, dt.date], str]:
        """Treść komórek. Bez wskazania piętra zwraca dyżury ze wszystkich."""
        first, last = self._month_bounds(year, month)
        sql = "SELECT employee_id, day, raw FROM entries WHERE day BETWEEN ? AND ?"
        params: list = [first, last]
        if floor_id is not None:
            sql += " AND floor_id=?"
            params.append(floor_id)
        rows = self.conn.execute(sql, params).fetchall()
        return {
            (r["employee_id"], dt.date.fromisoformat(r["day"])): r["raw"] for r in rows
        }

    def month_entry_floors(
        self, year: int, month: int
    ) -> dict[tuple[int, dt.date], int | None]:
        """Piętro każdego dyżuru — do rozpoznania zastępstw."""
        first, last = self._month_bounds(year, month)
        rows = self.conn.execute(
            "SELECT employee_id, day, floor_id FROM entries WHERE day BETWEEN ? AND ?",
            (first, last),
        ).fetchall()
        return {
            (r["employee_id"], dt.date.fromisoformat(r["day"])): r["floor_id"]
            for r in rows
        }

    def set_entry(
        self, employee_id: int, day: dt.date, raw: str, floor_id: int | None = None
    ) -> None:
        self.set_entries_bulk([(employee_id, day, raw, floor_id)])

    def set_entries_bulk(self, items: list[tuple]) -> None:
        """Zapisuje wpisy. Element to (pracownik, dzień, treść) lub
        (pracownik, dzień, treść, piętro)."""
        for item in items:
            emp_id, day, raw = item[0], item[1], item[2]
            floor_id = item[3] if len(item) > 3 else None
            raw = (raw or "").strip()
            if not raw:
                # Pusta komórka na grafiku piętra znaczy „nie pracuje tutaj",
                # a nie „nie pracuje nigdzie" — dyżur na innym piętrze zostaje.
                if floor_id is None:
                    self.conn.execute(
                        "DELETE FROM entries WHERE employee_id=? AND day=?",
                        (emp_id, day.isoformat()),
                    )
                else:
                    self.conn.execute(
                        "DELETE FROM entries WHERE employee_id=? AND day=? "
                        "AND (floor_id=? OR floor_id IS NULL)",
                        (emp_id, day.isoformat(), floor_id),
                    )
                continue
            if floor_id is None:
                # Domyślnie dyżur odbywa się na macierzystym piętrze pracownika.
                row = self.conn.execute(
                    "SELECT floor_id FROM employees WHERE id=?", (emp_id,)
                ).fetchone()
                floor_id = row["floor_id"] if row else None
            self.conn.execute(
                "INSERT INTO entries(employee_id, day, raw, floor_id) VALUES(?,?,?,?) "
                "ON CONFLICT(employee_id, day) DO UPDATE SET "
                "raw=excluded.raw, floor_id=excluded.floor_id",
                (emp_id, day.isoformat(), raw, floor_id),
            )
        self.conn.commit()

    def clear_month(self, year: int, month: int, floor_id: int | None = None) -> None:
        first, last = self._month_bounds(year, month)
        sql = "DELETE FROM entries WHERE day BETWEEN ? AND ?"
        params: list = [first, last]
        if floor_id is not None:
            sql += " AND floor_id=?"
            params.append(floor_id)
        self.conn.execute(sql, params)
        self.conn.commit()

    def months_with_data(self) -> list[tuple[int, int]]:
        rows = self.conn.execute(
            "SELECT DISTINCT substr(day,1,4) AS y, substr(day,6,2) AS m "
            "FROM entries ORDER BY y DESC, m DESC"
        ).fetchall()
        return [(int(r["y"]), int(r["m"])) for r in rows]
