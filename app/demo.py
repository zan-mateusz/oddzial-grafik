"""Dane demonstracyjne — realistyczny oddział, do testów i pierwszego uruchomienia."""
from __future__ import annotations

import datetime as dt
import random

from app.core.calendar_pl import month_days

STAFF = [
    ("Kowalska", "Anna", "oddziałowa", 1, 1),
    ("Nowak", "Maria", "pielęgniarka", 1, 1),
    ("Wiśniewska", "Katarzyna", "pielęgniarka", 1, 1),
    ("Wójcik", "Agnieszka", "pielęgniarka", 1, 1),
    ("Kowalczyk", "Barbara", "pielęgniarka", 1, 1),
    ("Kamińska", "Ewa", "pielęgniarka", 3, 4),
    ("Lewandowska", "Zofia", "pielęgniarka", 1, 1),
    ("Zielińska", "Joanna", "pielęgniarka", 1, 2),
    ("Szymańska", "Magdalena", "pielęgniarka", 1, 1),
    ("Woźniak", "Teresa", "opiekunka medyczna", 1, 1),
]


def seed_demo(db, year: int, month: int, seed: int = 7) -> None:
    """Tworzy pracowników (jeśli brak) i wypełnia miesiąc przykładowym grafikiem."""
    rng = random.Random(seed)
    if not db.employees():
        floors = db.floors()
        for i, (last, first, pos, num, den) in enumerate(STAFF):
            # Pierwsza połowa zespołu na I piętrze, druga na II.
            floor_id = floors[0]["id"] if i < len(STAFF) // 2 else floors[-1]["id"]
            db.add_employee(last, first, pos, num, den, floor_id=floor_id)

    employees = db.employees()
    days = month_days(year, month)
    items: list[tuple[int, dt.date, str]] = []

    # Rotacja 7-dniowa: dwie dniówki, nocka, cztery dni wolne — daje ok. 13-14
    # dyżurów w miesiącu, czyli mniej więcej pełny wymiar przy 12-godzinnych zmianach.
    CYCLE = ["D", "D", "N", "", "", "", ""]
    for i, emp in enumerate(employees):
        for j, day in enumerate(days):
            code = CYCLE[(j + i * 2) % len(CYCLE)]
            if code:
                items.append((emp["id"], day, code))
            elif rng.random() < 0.08:
                # Sporadyczne dyżury częściowe zapisane samym czasem trwania.
                items.append((emp["id"], day, rng.choice(["7,3", "10", "8", "7,35"])))

    # Urlop dla dwóch osób i zwolnienie dla jednej.
    if len(employees) >= 3:
        for day in days[4:12]:
            items.append((employees[1]["id"], day, "U"))
        for day in days[15:20]:
            items.append((employees[4]["id"], day, "L4"))

    db.set_entries_bulk(items)

    # Kilka zastępstw na drugim piętrze, żeby pokazać, jak są oznaczane.
    floors = db.floors()
    if len(floors) > 1 and len(employees) >= 3:
        other = floors[-1]["id"]
        for offset, day in enumerate(days[6:18:4]):
            emp = employees[offset % 3]
            if emp["floor_id"] != other:
                db.set_entry(emp["id"], day, "D", other)
