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
        for last, first, pos, num, den in STAFF:
            db.add_employee(last, first, pos, num, den)

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
                # Sporadyczne dyżury częściowe, żeby pokazać wpisy godzinowe.
                items.append((emp["id"], day, rng.choice(["8-14", "7-15", "R", "P"])))

    # Urlop dla dwóch osób i zwolnienie dla jednej.
    if len(employees) >= 3:
        for day in days[4:12]:
            items.append((employees[1]["id"], day, "U"))
        for day in days[15:20]:
            items.append((employees[4]["id"], day, "L4"))

    db.set_entries_bulk(items)
