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

# Supabase client for persistent storage (falls back to SQLite if not configured)
try:
    from backend.services.supabase_client import supabase_client as _supabase
except Exception:
    _supabase = None

_DEFAULT_PATH = Path(__file__).resolve().parent / "petcare.db"


def _use_supabase() -> bool:
    """Return True if Supabase is configured and available."""
    return _supabase is not None and _supabase.enabled


def _normalize_rows(rows) -> list:
    """Normalize Supabase response or sqlite rows to list of dicts."""
    if rows is None:
        return []
    if isinstance(rows, list):
        return [dict(r) if hasattr(r, "items") else dict(r) for r in rows]
    return [dict(rows)] if hasattr(rows, "items") else []


def _normalize_row(row):
    """Normalize a single row to a dict or None."""
    if row is None:
        return None
    return dict(row) if hasattr(row, "items") else dict(row)

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

-- GPS location logs (provider-aggregated, production-safe)
CREATE TABLE IF NOT EXISTS locations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    pet_id INTEGER NOT NULL,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    accuracy REAL,
    altitude REAL,
    speed REAL,
    heading REAL,
    provider TEXT NOT NULL DEFAULT 'unknown',
    timestamp TEXT NOT NULL DEFAULT (datetime('now')),
    is_simulator INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (pet_id) REFERENCES pets (id)
);

CREATE INDEX IF NOT EXISTS idx_locations_user_id ON locations(user_id);
CREATE INDEX IF NOT EXISTS idx_locations_pet_id ON locations(pet_id);
CREATE INDEX IF NOT EXISTS idx_locations_timestamp ON locations(timestamp DESC);

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
    FOREIGN KEY (pet_id) REFERENCES pets (id)
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
    FOREIGN KEY (pet_id) REFERENCES pets (id)
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
    FOREIGN KEY (pet_id) REFERENCES pets (id)
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
    FOREIGN KEY (pet_id) REFERENCES pets (id)
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

-- Conversations (chat sessions per pet)
CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    pet_id INTEGER NOT NULL,
    title TEXT NOT NULL DEFAULT 'New Conversation',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (pet_id) REFERENCES pets (id)
);

CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_pet_id ON conversations(pet_id);

-- Messages (chat messages within conversations)
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL,
    user_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (conversation_id) REFERENCES conversations (id)
);

CREATE INDEX IF NOT EXISTS idx_messages_user_id ON messages(user_id);
CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id);

-- Voice conversions (audio translation events)
CREATE TABLE IF NOT EXISTS voice_conversions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    pet_id INTEGER,
    conversation_id INTEGER,
    animal TEXT NOT NULL,
    emotion TEXT NOT NULL,
    interpretation TEXT NOT NULL,
    interpretation_score REAL,
    language TEXT NOT NULL DEFAULT 'en-IN',
    audio_file_id INTEGER,
    model_version TEXT,
    status TEXT NOT NULL DEFAULT 'success',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (pet_id) REFERENCES pets (id),
    FOREIGN KEY (conversation_id) REFERENCES conversations (id),
    FOREIGN KEY (audio_file_id) REFERENCES audio_assets (id)
);

CREATE INDEX IF NOT EXISTS idx_voice_conversions_user_id ON voice_conversions(user_id);
CREATE INDEX IF NOT EXISTS idx_voice_conversions_pet_id ON voice_conversions(pet_id);
CREATE INDEX IF NOT EXISTS idx_voice_conversions_conversation_id ON voice_conversions(conversation_id);

-- Audio assets (stored audio files)
CREATE TABLE IF NOT EXISTS audio_assets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    filename TEXT NOT NULL,
    storage_path TEXT NOT NULL,
    file_size INTEGER,
    mime_type TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_audio_assets_user_id ON audio_assets(user_id);

-- Medication schedules
CREATE TABLE IF NOT EXISTS medication_schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    pet_id INTEGER NOT NULL,
    medication_name TEXT NOT NULL,
    dosage TEXT NOT NULL DEFAULT '',
    frequency TEXT NOT NULL DEFAULT 'daily',
    time_of_day TEXT NOT NULL DEFAULT '',
    next_due_on TEXT,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (pet_id) REFERENCES pets (id)
);

CREATE INDEX IF NOT EXISTS idx_medication_schedules_user_id ON medication_schedules(user_id);
CREATE INDEX IF NOT EXISTS idx_medication_schedules_pet_id ON medication_schedules(pet_id);

-- Reminders (delivery attempts)
CREATE TABLE IF NOT EXISTS reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    pet_id INTEGER,
    medication_schedule_id INTEGER,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    kind TEXT NOT NULL DEFAULT 'medication',  -- 'medication' | 'vaccination' | 'care' | 'custom'
    target_date TEXT NOT NULL DEFAULT (datetime('now')),
    delivered_at TEXT NOT NULL DEFAULT '',
    delivery_method TEXT NOT NULL DEFAULT 'app',  -- 'app' | 'sms' | 'email' | 'push'
    status TEXT NOT NULL DEFAULT 'pending',  -- 'pending' | 'sent' | 'delivered' | 'failed'
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (pet_id) REFERENCES pets (id),
    FOREIGN KEY (medication_schedule_id) REFERENCES medication_schedules (id)
);

CREATE INDEX IF NOT EXISTS idx_reminders_user_id ON reminders(user_id);
CREATE INDEX IF NOT EXISTS idx_reminders_pet_id ON reminders(pet_id);
CREATE INDEX IF NOT EXISTS idx_reminders_target_date ON reminders(target_date);
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
    "medication_schedules": [
        {
            "pet_name": "Buddy",
            "medication_name": "Heartworm prevention",
            "dosage": " monthly",
            "frequency": "monthly",
            "time_of_day": "08:00",
        },
        {
            "pet_name": "Mia",
            "medication_name": "Flea treatment",
            "dosage": " weekly",
            "frequency": "weekly",
            "time_of_day": "07:30",
        },
    ],
    "reminders": [
        {
            "pet_name": "Buddy",
            "title": "Heartworm pill",
            "description": "Give monthly heartworm prevention",
            "kind": "medication",
        },
        {
            "pet_name": "Mia",
            "title": "Flea treatment",
            "description": "Apply weekly flea treatment",
            "kind": "medication",
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
                    "microchip_id, avatar_emoji, notes) VALUES (?,?,?,?,?,?,?,?,?,?)",
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


# ---------------------------------------------------------------------------
# Connection management
# ---------------------------------------------------------------------------


def _resolve_db_target() -> str:
    """Pick the sqlite target for this runtime."""
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
                _migrate_schema()
                seed_if_empty()
    return _conn


def init_db() -> None:
    """Create tables + seed (call once at app startup).
    Skips SQLite schema if Supabase is configured (user runs SQL manually in Supabase)."""
    if _use_supabase():
        logger.info("Supabase configured — skipping SQLite schema creation")
        return
    with _conn_lock:
        conn = get_conn()
        _init_schema()
        seed_if_empty()


def _init_schema() -> None:
    with _conn_lock:
        get_conn().executescript(_SCHEMA)
        get_conn().commit()
    _migrate_schema()


def _migrate_schema() -> None:
    """Add missing columns to existing tables (for databases created before
    user_id was added). This is idempotent."""
    with _conn_lock:
        conn = get_conn()

        # Columns to add: (table, column_name, column_definition)
        migrations = [
            ("pets", "user_id", "TEXT NOT NULL DEFAULT 'legacy_user'"),
            (
                "vaccination_records",
                "user_id",
                "TEXT NOT NULL DEFAULT 'legacy_user'",
            ),
            ("weight_log", "user_id", "TEXT NOT NULL DEFAULT 'legacy_user'"),
            (
                "health_records",
                "user_id",
                "TEXT NOT NULL DEFAULT 'legacy_user'",
            ),
            (
                "care_schedules",
                "user_id",
                "TEXT NOT NULL DEFAULT 'legacy_user'",
            ),
            ("vet_contacts", "user_id", "TEXT NOT NULL DEFAULT 'legacy_user'"),
        ]

        for table, column, coldef in migrations:
            try:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {coldef}")
            except sqlite3.OperationalError:
                # Column already exists - skip
                pass

        conn.commit()


def close_db() -> None:
    global _conn
    with _conn_lock:
        if _conn is not None:
            _conn.close()
            _conn = None


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------


def _extract_table(sql: str) -> str | None:
    """Extract table name from simple SQL (SELECT/INSERT/UPDATE/DELETE)."""
    import re
    m = re.search(r'(?:FROM|INTO|UPDATE|INTO|DELETE FROM)\s+(\w+)', sql, re.IGNORECASE)
    return m.group(1) if m else None


def _supabase_select(table: str, params: tuple) -> list | None:
    """Route simple SELECT queries to Supabase client. Returns None if not handled."""
    if not _use_supabase():
        return None
    client = _supabase
    user_id = params[0] if params else None

    try:
        if table == "pets":
            return client.get_pets(user_id or "default")
        elif table == "vaccination_records":
            # Get vaccinations for all pets of user — need pet IDs first
            pets = client.get_pets(user_id or "default")
            if not pets:
                return []
            all_vax = []
            for p in pets:
                all_vax.extend(client.get_vaccinations(p["id"]))
            return all_vax
        elif table == "weight_log":
            pets = client.get_pets(user_id or "default")
            if not pets:
                return []
            all_weights = []
            for p in pets:
                all_weights.extend(client.get_weight_logs(p["id"]))
            return all_weights
        elif table == "health_records":
            pets = client.get_pets(user_id or "default")
            if not pets:
                return []
            all_health = []
            for p in pets:
                all_health.extend(client.get_health_records(p["id"]))
            return all_health
        elif table == "care_schedules":
            pets = client.get_pets(user_id or "default")
            if not pets:
                return []
            all_care = []
            for p in pets:
                all_care.extend(client.get_care_schedules(p["id"]))
            return all_care
        elif table == "vet_contacts":
            return client.get_vet_contacts()
        elif table == "medication_schedules":
            pets = client.get_pets(user_id or "default")
            if not pets:
                return []
            all_meds = []
            for p in pets:
                all_meds.extend(client.get_medication_schedules(p["id"]))
            return all_meds
        elif table == "reminders":
            return client.get_reminders(user_id or "default")
    except Exception as e:
        logger.warning(f"Supabase select failed for {table}: {e}")
    return None


def _supabase_execute(table: str, data: dict) -> int | None:
    """Route INSERT queries to Supabase client. Returns new row id or None."""
    if not _use_supabase():
        return None
    client = _supabase
    try:
        if table == "pets":
            result = client.create_pet(data)
            return result.get("id") if result else None
        elif table == "vaccination_records":
            result = client.create_vaccination(data.get("pet_id"), data)
            return result.get("id") if result else None
        elif table == "weight_log":
            result = client.create_weight_log(data.get("pet_id"), data)
            return result.get("id") if result else None
        elif table == "health_records":
            result = client.create_health_record(data.get("pet_id"), data)
            return result.get("id") if result else None
        elif table == "care_schedules":
            result = client.create_care_schedule(data.get("pet_id"), data)
            return result.get("id") if result else None
        elif table == "vet_contacts":
            result = client.create_vet_contact(data)
            return result.get("id") if result else None
        elif table == "medication_schedules":
            result = client.create_medication_schedule(data.get("pet_id"), data)
            return result.get("id") if result else None
        elif table == "reminders":
            result = client.create_reminder(data.get("user_id", "default"), data)
            return result.get("id") if result else None
    except Exception as e:
        logger.warning(f"Supabase insert failed for {table}: {e}")
    return None


def query_all(sql: str, params: tuple = ()) -> list:
    if _use_supabase():
        table = _extract_table(sql)
        if table and sql.strip().upper().startswith("SELECT"):
            result = _supabase_select(table, params)
            if result is not None:
                return result
    with _conn_lock:
        return get_conn().execute(sql, params).fetchall()


def query_one(sql: str, params: tuple = ()):
    rows = query_all(sql, params)
    return rows[0] if rows else None


def execute(sql: str, params: tuple = ()) -> int:
    """Run a write statement; returns last insert rowid (0 if none)."""
    if _use_supabase():
        table = _extract_table(sql)
        if table and sql.strip().upper().startswith("INSERT"):
            # Build data dict from params — params order matches column order in SQL
            result = _supabase_execute(table, {"params": list(params)})
            if result is not None:
                return result
    with _conn_lock:
        cur = get_conn().execute(sql, params)
        get_conn().commit()
        return cur.lastrowid or 0


def delete_row(sql: str, params: tuple = ()) -> bool:
    """Run a DELETE/UPDATE; returns True if a row was affected."""
    if _use_supabase():
        table = _extract_table(sql)
        if table:
            client = _supabase
            try:
                if table == "care_schedules" and params:
                    client.complete_care_schedule(params[0])
                    return True
                elif table == "medication_schedules" and params:
                    client.delete_medication_schedule(params[0])
                    return True
                elif table == "reminders" and params:
                    client.delete_reminder(params[0])
                    return True
                elif table == "vet_contacts" and params:
                    client.delete_vet_contact(params[0])
                    return True
                elif table == "health_records" and params:
                    client.delete_health_record(params[0])
                    return True
                elif table == "vaccination_records" and params:
                    client.delete_vaccination(params[0])
                    return True
                elif table == "weight_log" and params:
                    client.delete_weight_log(params[0])
                    return True
            except Exception as e:
                logger.warning(f"Supabase delete failed for {table}: {e}")
    with _conn_lock:
        cur = get_conn().execute(sql, params)
        get_conn().commit()
        return cur.rowcount > 0
