"""PetCare data layer — pure stdlib ``sqlite3`` (no SQLAlchemy, no ORM).

Single connection guarded by a lock so FastAPI's default threadpool can share
it safely. All helpers return ``sqlite3.Row`` objects (dict-like, support
``row["column"]`` and ``dict(row)``).
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
CREATE TABLE IF NOT EXISTS pets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    species TEXT NOT NULL DEFAULT 'dog',
    breed TEXT NOT NULL DEFAULT '',
    gender TEXT NOT NULL DEFAULT 'unknown',
    date_of_birth TEXT,
    weight_kg REAL NOT NULL DEFAULT 0.0,
    microchip_id TEXT NOT NULL DEFAULT '',
    avatar_emoji TEXT NOT NULL DEFAULT '🐾',
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS vaccination_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pet_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    administered_on TEXT,
    next_due_on TEXT,
    administered_at TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    FOREIGN KEY (pet_id) REFERENCES pets (id)
);

CREATE TABLE IF NOT EXISTS weight_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pet_id INTEGER NOT NULL,
    weight_kg REAL NOT NULL,
    logged_on TEXT NOT NULL DEFAULT (date('now')),
    FOREIGN KEY (pet_id) REFERENCES pets (id)
);

CREATE TABLE IF NOT EXISTS health_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pet_id INTEGER NOT NULL,
    record_type TEXT NOT NULL DEFAULT 'note',
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    recorded_on TEXT NOT NULL DEFAULT (date('now')),
    FOREIGN KEY (pet_id) REFERENCES pets (id)
);

CREATE TABLE IF NOT EXISTS care_schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pet_id INTEGER NOT NULL,
    task TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'care',
    frequency TEXT NOT NULL DEFAULT 'daily',
    time_of_day TEXT NOT NULL DEFAULT '',
    next_due_on TEXT,
    active INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (pet_id) REFERENCES pets (id)
);

CREATE TABLE IF NOT EXISTS vet_contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone TEXT NOT NULL DEFAULT '',
    address TEXT NOT NULL DEFAULT '',
    specialty TEXT NOT NULL DEFAULT 'general',
    hours TEXT NOT NULL DEFAULT '',
    emergency INTEGER NOT NULL DEFAULT 0
);
"""

_SEED = {
    "pets": [
        {
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
    "weight_log": [
        {"pet_name": "Buddy", "weight_kg": 27.1, "logged_on": "2025-10-01"},
        {"pet_name": "Buddy", "weight_kg": 27.5, "logged_on": "2025-11-01"},
        {"pet_name": "Mia", "weight_kg": 4.0, "logged_on": "2025-10-01"},
        {"pet_name": "Mia", "weight_kg": 4.2, "logged_on": "2025-11-01"},
    ],
    "health_records": [
        {
            "pet_name": "Buddy",
            "record_type": "visit",
            "title": "Annual wellness exam",
            "description": "Healthy. Dental scale done.",
            "recorded_on": "2025-01-10",
        },
        {
            "pet_name": "Mia",
            "record_type": "surgery",
            "title": "Spay",
            "description": "Recovered fully.",
            "recorded_on": "2024-08-15",
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


def _pet_id_for(pet_name: str) -> int | None:
    row = query_one("SELECT id FROM pets WHERE name = ?", (pet_name,))
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
                    "INSERT INTO pets (name, species, breed, gender, date_of_birth, weight_kg, "
                    "microchip_id, avatar_emoji, notes) VALUES (?,?,?,?,?,?,?,?,?)",
                    (
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
                    "INSERT INTO vaccination_records (pet_id, name, administered_on, next_due_on) "
                    "VALUES (?,?,?,?)",
                    (
                        _pet_id_for(v["pet_name"]),
                        v["name"],
                        v["administered_on"],
                        v["next_due_on"],
                    ),
                )
            for w in _SEED["weight_log"]:
                cur.execute(
                    "INSERT INTO weight_log (pet_id, weight_kg, logged_on) VALUES (?,?,?)",
                    (_pet_id_for(w["pet_name"]), w["weight_kg"], w["logged_on"]),
                )
            for h in _SEED["health_records"]:
                cur.execute(
                    "INSERT INTO health_records (pet_id, record_type, title, description, recorded_on) "
                    "VALUES (?,?,?,?,?)",
                    (
                        _pet_id_for(h["pet_name"]),
                        h["record_type"],
                        h["title"],
                        h["description"],
                        h["recorded_on"],
                    ),
                )
            for c in _SEED["care_schedules"]:
                cur.execute(
                    "INSERT INTO care_schedules (pet_id, task, category, frequency, time_of_day) "
                    "VALUES (?,?,?,?,?)",
                    (
                        _pet_id_for(c["pet_name"]),
                        c["task"],
                        c["category"],
                        c["frequency"],
                        c["time_of_day"],
                    ),
                )
            for vc in _SEED["vet_contacts"]:
                cur.execute(
                    "INSERT INTO vet_contacts (name, phone, address, specialty, hours, emergency) "
                    "VALUES (?,?,?,?,?,?)",
                    (
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


# ---------------------------------------------------------------------------
# Connection management
# ---------------------------------------------------------------------------


def _resolve_db_target() -> str:
    """Pick the sqlite target for this runtime.

    Order: PETCARE_DATABASE_URL env override -> Vercel/:memory: (read-only FS)
    -> local file next to this module.
    """
    override = os.environ.get("PETCARE_DATABASE_URL")
    if override:
        return override
    if (
        os.environ.get("VERCEL") == "1"
        or os.environ.get("AWS_LAMBDA_FUNCTION_NAME")
        or os.environ.get("RENDER")
    ):
        return ":memory:"
    return str(_DEFAULT_PATH)


def get_conn() -> sqlite3.Connection:
    """Return the process-shared connection, creating it on first use."""
    global _conn
    if _conn is None:
        with _conn_lock:
            if _conn is None:
                db_target = _resolve_db_target()
                conn = sqlite3.connect(db_target, check_same_thread=False)
                conn.row_factory = sqlite3.Row
                conn.execute("PRAGMA foreign_keys = ON")
                _conn = conn
                with _conn_lock:
                    pass
                _init_schema()
                seed_if_empty()
    return _conn


def init_db() -> None:
    """Create tables + seed (call once at app startup)."""
    with _conn_lock:
        conn = get_conn()
        _init_schema()
        seed_if_empty()


def _init_schema() -> None:
    with _conn_lock:
        get_conn().executescript(_SCHEMA)
        get_conn().commit()


def close_db() -> None:
    global _conn
    with _conn_lock:
        if _conn is not None:
            _conn.close()
            _conn = None


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------


def query_all(sql: str, params: tuple = ()) -> list[sqlite3.Row]:
    with _conn_lock:
        return get_conn().execute(sql, params).fetchall()


def query_one(sql: str, params: tuple = ()) -> sqlite3.Row | None:
    rows = query_all(sql, params)
    return rows[0] if rows else None


def execute(sql: str, params: tuple = ()) -> int:
    """Run a write statement; returns last insert rowid (0 if none)."""
    with _conn_lock:
        cur = get_conn().execute(sql, params)
        get_conn().commit()
        return cur.lastrowid or 0


def delete_row(sql: str, params: tuple = ()) -> bool:
    """Run a DELETE/UPDATE; returns True if a row was affected."""
    with _conn_lock:
        cur = get_conn().execute(sql, params)
        get_conn().commit()
        return cur.rowcount > 0
