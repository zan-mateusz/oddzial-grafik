"""Warstwa danych — SQLite. Jeden plik = cała historia grafików."""
from __future__ import annotations

import datetime as dt
import sqlite3
from pathlib import Path

from app.core.shifts import DEFAULT_SHIFT_TYPES, Category, ShiftType

SCHEMA_VERSION = 1

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
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
    notes       TEXT NOT NULL DEFAULT ''
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


class Database:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript(SCHEMA)
        self._init_meta()
        self.conn.commit()

    def _init_meta(self) -> None:
        cur = self.conn.execute("SELECT value FROM meta WHERE key='schema_version'")
        if cur.fetchone() is None:
            self.conn.execute(
                "INSERT INTO meta(key, value) VALUES('schema_version', ?)",
                (str(SCHEMA_VERSION),),
            )
            self.seed_shift_types()

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

    def employees(self, include_inactive: bool = False) -> list[sqlite3.Row]:
        sql = "SELECT * FROM employees"
        if not include_inactive:
            sql += " WHERE active=1"
        sql += " ORDER BY sort_order, last_name, first_name"
        return list(self.conn.execute(sql).fetchall())

    def employees_for_month(self, year: int, month: int) -> list[sqlite3.Row]:
        """Pracownicy zatrudnieni w danym miesiącu — z historią, więc dawne
        grafiki nadal pokazują osoby, które już nie pracują."""
        first = dt.date(year, month, 1).isoformat()
        last = (dt.date(year + 1, 1, 1) if month == 12
                else dt.date(year, month + 1, 1)) - dt.timedelta(days=1)
        last_s = last.isoformat()
        return list(self.conn.execute(
            "SELECT * FROM employees WHERE "
            "(hired_on IS NULL OR hired_on <= ?) AND (ended_on IS NULL OR ended_on >= ?) "
            "AND (active=1 OR id IN (SELECT employee_id FROM entries WHERE day BETWEEN ? AND ?)) "
            "ORDER BY sort_order, last_name, first_name",
            (last_s, first, first, last_s),
        ).fetchall())

    def add_employee(self, last_name: str, first_name: str = "", position: str = "",
                     fte_num: int = 1, fte_den: int = 1, hired_on: str | None = None) -> int:
        cur = self.conn.execute(
            "INSERT INTO employees(last_name, first_name, position, fte_num, fte_den, "
            "hired_on, sort_order) VALUES(?,?,?,?,?,?, "
            "(SELECT COALESCE(MAX(sort_order)+1,0) FROM employees))",
            (last_name, first_name, position, fte_num, fte_den, hired_on),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def update_employee(self, emp_id: int, **fields) -> None:
        allowed = {"last_name", "first_name", "position", "fte_num", "fte_den",
                   "active", "sort_order", "hired_on", "ended_on", "notes"}
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

    def month_entries(self, year: int, month: int) -> dict[tuple[int, dt.date], str]:
        first = dt.date(year, month, 1)
        last = (dt.date(year + 1, 1, 1) if month == 12
                else dt.date(year, month + 1, 1)) - dt.timedelta(days=1)
        rows = self.conn.execute(
            "SELECT employee_id, day, raw FROM entries WHERE day BETWEEN ? AND ?",
            (first.isoformat(), last.isoformat()),
        ).fetchall()
        return {
            (r["employee_id"], dt.date.fromisoformat(r["day"])): r["raw"] for r in rows
        }

    def set_entry(self, employee_id: int, day: dt.date, raw: str) -> None:
        raw = (raw or "").strip()
        if not raw:
            self.conn.execute(
                "DELETE FROM entries WHERE employee_id=? AND day=?",
                (employee_id, day.isoformat()),
            )
        else:
            self.conn.execute(
                "INSERT INTO entries(employee_id, day, raw) VALUES(?,?,?) "
                "ON CONFLICT(employee_id, day) DO UPDATE SET raw=excluded.raw",
                (employee_id, day.isoformat(), raw),
            )
        self.conn.commit()

    def set_entries_bulk(self, items: list[tuple[int, dt.date, str]]) -> None:
        for emp_id, day, raw in items:
            raw = (raw or "").strip()
            if not raw:
                self.conn.execute(
                    "DELETE FROM entries WHERE employee_id=? AND day=?",
                    (emp_id, day.isoformat()),
                )
            else:
                self.conn.execute(
                    "INSERT INTO entries(employee_id, day, raw) VALUES(?,?,?) "
                    "ON CONFLICT(employee_id, day) DO UPDATE SET raw=excluded.raw",
                    (emp_id, day.isoformat(), raw),
                )
        self.conn.commit()

    def clear_month(self, year: int, month: int) -> None:
        first = dt.date(year, month, 1)
        last = (dt.date(year + 1, 1, 1) if month == 12
                else dt.date(year, month + 1, 1)) - dt.timedelta(days=1)
        self.conn.execute(
            "DELETE FROM entries WHERE day BETWEEN ? AND ?",
            (first.isoformat(), last.isoformat()),
        )
        self.conn.commit()

    def months_with_data(self) -> list[tuple[int, int]]:
        rows = self.conn.execute(
            "SELECT DISTINCT substr(day,1,4) AS y, substr(day,6,2) AS m "
            "FROM entries ORDER BY y DESC, m DESC"
        ).fetchall()
        return [(int(r["y"]), int(r["m"])) for r in rows]
