"""PetCare data layer - pure stdlib sqlite3 (no SQLAlchemy, no ORM).

Single connection guarded by a lock so FastAPI's default threadpool can share
it safely. All helpers return sqlite3.Row objects (dict-like, support
row["column"] and dict(row)).
"""

from __future__ import annotations

import datetime as dt
import logging
import sqlite3
import threading
import os
from pathlib import Path

logger = logging.getLogger(__name__)

_DEFAULT_PATH = Path(__file__).resolve().parent / "petcare.db"

# The shared connection is created lazily and reused for the process lifetime.
_conn = None
_conn_lock = threading.RLock()

# ---------------------------------------------------------------------------
# Schema / seed
# ---------------------------------------------------------------------------

_SCHEMA = """
-- Pets (owner-isolated via user_id)
CREATE TABLE IF NOT EXISTS pets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    species TEXT NOT NULL DEFAULT 'dog',
    breed TEXT NOT NULL DEFAULT '',
    gender TEXT NOT NULL DEFAULT 'unknown',
    date_of_birth TEXT,
    weight_kg REAL NOT NULL DEFAULT 0.0,
    microchip_id TEXT NOT NULL DEFAULT '',
    avatar_emoji TEXT NOT NULL DEFAULT '🐾',
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_pets_user_id ON pets(user_id);

-- Vaccination records
CREATE TABLE IF NOT EXISTS vaccination_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pet_id INTEGER NOT NULL,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    administered_on TEXT,
    next_due_on TEXT,
    administered_at TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (pet_id) REFERENCES pets (id),
    FOREIGN KEY (user_id) REFERENCES pets (user_id)
);

CREATE INDEX IF NOT EXISTS idx_vaccination_records_user_id ON vaccination_records(user_id);
CREATE INDEX IF NOT EXISTS idx_vaccination_records_pet_id ON vaccination_records(pet_id);

-- Weight log
CREATE TABLE IF NOT EXISTS weight_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pet_id INTEGER NOT NULL,
    user_id TEXT NOT NULL,
    weight_kg REAL NOT NULL,
    logged_on TEXT NOT NULL DEFAULT (date('now')),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (pet_id) REFERENCES pets (id),
    FOREIGN KEY (user_id) REFERENCES pets (user_id)
);

CREATE INDEX IF NOT EXISTS idx_weight_log_user_id ON weight_log(user_id);
CREATE INDEX IF NOT EXISTS idx_weight_log_pet_id ON weight_log(pet_id);

-- Health records
CREATE TABLE IF NOT EXISTS health_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pet_id INTEGER NOT NULL,
    user_id TEXT NOT NULL,
    record_type TEXT NOT NULL DEFAULT 'note',
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    recorded_on TEXT NOT NULL DEFAULT (date('now')),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (pet_id) REFERENCES pets (id),
    FOREIGN KEY (user_id) REFERENCES pets (user_id)
);

CREATE INDEX IF NOT EXISTS idx_health_records_user_id ON health_records(user_id);
CREATE INDEX IF NOT EXISTS idx_health_records_pet_id ON health_records(pet_id);

-- Care schedules
CREATE TABLE IF NOT EXISTS care_schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pet_id INTEGER NOT NULL,
    user_id TEXT NOT NULL,
    task TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'care',
    frequency TEXT NOT NULL DEFAULT 'daily',
    time_of_day TEXT NOT NULL DEFAULT '',
    next_due_on TEXT,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (pet_id) REFERENCES pets (id),
    FOREIGN KEY (user_id) REFERENCES pets (user_id)
);

CREATE INDEX IF NOT EXISTS idx_care_schedules_user_id ON care_schedules(user_id);
CREATE INDEX IF NOT EXISTS idx_care_schedules_pet_id ON care_schedules(pet_id);

-- Vet contacts
CREATE TABLE IF NOT EXISTS vet_contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    phone TEXT NOT NULL DEFAULT '',
    address TEXT NOT NULL DEFAULT '',
    specialty TEXT NOT NULL DEFAULT 'general',
    hours TEXT NOT NULL DEFAULT '',
    emergency INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_vet_contacts_user_id ON vet_contacts(user_id);
"""

_SEED = {
    "pets": [
        {
            "user_id": "demo_user_001",
            "name": "Buddy",
            "species": "dog",
            "breed": "Golden Retriever",
            "gender": "male",
            "date_of_birth": "2021-06-14",
            "weight_kg": 27.5,
            "microchip_id": "981000001234567",
            "avatar_emoji": "🐶",
            "notes": "Energetic family dog. Loves fetch and swimming.",
        },
        {
            "user_id": "demo_user_001",
            "name": "Mia",
            "species": "cat",
            "breed": "Domestic Shorthair",
            "gender": "female",
            "date_of_birth": "2023-02-01",
            "weight_kg": 4.2,
            "microchip_id": "981000009876543",
            "avatar_emoji": "🐱",
            "notes": "Indoor cat. Slightly shy with strangers.",
        },
    ],
    "vaccination_records": [
        {
            "pet_name": "Buddy",
            "name": "Rabies",
            "administered_on": "2025-01-10",
            "next_due_on": "2026-01-10",
        },
        {
            "pet_name": "Buddy",
            "name": "DHPP",
            "administered_on": "2025-01-10",
            "next_due_on": "2026-01-10",
        },
        {
            "pet_name": "Buddy",
            "name": "Bordetella",
            "administered_on": "2025-06-20",
            "next_due_on": "2025-12-17",
        },
        {
            "pet_name": "Mia",
            "name": "FVRCP",
            "administered_on": "2025-03-05",
            "next_due_on": "2026-03-05",
        },
        {
            "pet_name": "Mia",
            "name": "Rabies",
            "administered_on": "2025-03-05",
            "next_due_on": "2026-03-05",
        },
    ],
    "care_schedules": [
        {
            "pet_name": "Buddy",
            "task": "Evening walk",
            "category": "exercise",
            "frequency": "daily",
            "time_of_day": "18:00",
        },
        {
            "pet_name": "Buddy",
            "task": "Heartworm prevention",
            "category": "medication",
            "frequency": "monthly",
            "time_of_day": "08:00",
        },
        {
            "pet_name": "Mia",
            "task": "Litter box clean",
            "category": "hygiene",
            "frequency": "daily",
            "time_of_day": "07:30",
        },
        {
            "pet_name": "Mia",
            "task": "Brush teeth",
            "category": "grooming",
            "frequency": "weekly",
            "time_of_day": "",
        },
    ],
    "vet_contacts": [
        {
            "name": "CityVet Emergency",
            "phone": "(555) 010-0911",
            "specialty": "emergency",
            "hours": "24/7",
            "emergency": 1,
        },
        {
            "name": "Happy Paws Clinic",
            "phone": "(555) 010-2020",
            "address": "12 Meadow Lane",
            "specialty": "general",
            "hours": "Mon-Sat 9-6",
            "emergency": 0,
        },
    ],
}


def _pet_id_for(pet_name: str, user_id: str) -> int | None:
    """Look up pet ID by name and user_id (owner isolation)."""
    row = query_one(
        "SELECT id FROM pets WHERE name = ? AND user_id = ?",
        (pet_name, user_id),
    )
    return row["id"] if row else None


def seed_if_empty() -> None:
    """Populate demo pets + data on first run (idempotent)."""
    count = query_one("SELECT COUNT(*) AS n FROM pets")
    if count and count["n"] > 0:
        return
    with _conn_lock:
        cur = get_conn().cursor()
        try:
            for p in _SEED["pets"]:
                cur.execute(
                    "INSERT INTO pets (user_id, name, species, breed, gender, date_of_birth, weight_kg, "
                    "microchip_id, avatar_emoji, notes) VALUES (?,?,?,?,?,?,?,?,?)",
                    (
                        p["user_id"],
                        p["name"],
                        p["species"],
                        p["breed"],
                        p["gender"],
                        p["date_of_birth"],
                        p["weight_kg"],
                        p["microchip_id"],
                        p["avatar_emoji"],
                        p["notes"],
                    ),
                )
            for v in _SEED["vaccination_records"]:
                cur.execute(
                    "INSERT INTO vaccination_records (pet_id, user_id, name, administered_on, next_due_on) "
                    "VALUES (?,?,?,?,?)",
                    (
                        _pet_id_for(v["pet_name"], "demo_user_001"),
                        "demo_user_001",
                        v["name"],
                        v["administered_on"],
                        v["next_due_on"],
                    ),
                )
            for w in _SEED["weight_log"]:
                cur.execute(
                    "INSERT INTO weight_log (pet_id, user_id, weight_kg, logged_on) VALUES (?,?,?,?)",
                    (
                        _pet_id_for(w["pet_name"], "demo_user_001"),
                        "demo_user_001",
                        w["weight_kg"],
                        w["logged_on"],
                    ),
                )
            for h in _SEED["health_records"]:
                cur.execute(
                    "INSERT INTO health_records (pet_id, user_id, record_type, title, description, recorded_on) "
                    "VALUES (?,?,?,?,?,?)",
                    (
                        _pet_id_for(h["pet_name"], "demo_user_001"),
                        "demo_user_001",
                        h["record_type"],
                        h["title"],
                        h["description"],
                        h["recorded_on"],
                    ),
                )
            for c in _SEED["care_schedules"]:
                cur.execute(
                    "INSERT INTO care_schedules (pet_id, user_id, task, category, frequency, time_of_day) "
                    "VALUES (?,?,?,?,?,?)",
                    (
                        _pet_id_for(c["pet_name"], "demo_user_001"),
                        "demo_user_001",
                        c["task"],
                        c["category"],
                        c["frequency"],
                        c["time_of_day"],
                    ),
                )
            for vc in _SEED["vet_contacts"]:
                cur.execute(
                    "INSERT INTO vet_contacts (user_id, name, phone, address, specialty, hours, emergency) "
                    "VALUES (?,?,?,?,?,?,?)",
                    (
                        "demo_user_001",
                        vc["name"],
                        vc["phone"],
                        vc.get("address", ""),
                        vc["specialty"],
                        vc["hours"],
                        vc["emergency"],
                    ),
                )
            get_conn().commit()
        except Exception:
            get_conn().rollback()
            raise
        logger.info("Seeded petcare demo data (Buddy + Mia)")


def init_db() -> None:
    """Create tables + seed (call once at app startup)."""
    with _conn_lock:
        conn = get_conn()
        _init_schema()
        seed_if_empty()


def _migrate_schema(conn: sqlite3.Connection) -> None:
    """Add missing columns to existing tables (migration helper)."""
    # Pets table
    existing = {row[1] for row in conn.execute("PRAGMA table_info(pets)").fetchall()}
    required_pets = {"id", "user_id", "name", "species", "breed", "gender", "date_of_birth", "weight_kg", "microchip_id", "avatar_emoji", "notes", "created_at", "updated_at"}
    for col in required_pets:
        if col not in existing:
            conn.execute(f"ALTER TABLE pets ADD COLUMN {col} TEXT")

    # Vaccination records table
    existing = {row[1] for row in conn.execute("PRAGMA table_info(vaccination_records)").fetchall()}
    required_vax = {"pet_id", "user_id", "name", "administered_on", "next_due_on", "administered_at", "notes", "created_at"}
    for col in required_vax:
        if col not in existing:
            conn.execute(f"ALTER TABLE vaccination_records ADD COLUMN {col} TEXT")

    # Care schedules table
    existing = {row[1] for row in conn.execute("PRAGMA table_info(care_schedules)").fetchall()}
    required_care = {"id", "pet_id", "user_id", "task", "category", "frequency", "time_of_day", "next_due_on", "active", "created_at", "updated_at"}
    for col in required_care:
        if col not in existing:
            conn.execute(f"ALTER TABLE care_schedules ADD COLUMN {col} TEXT")