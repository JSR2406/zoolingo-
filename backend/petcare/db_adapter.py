"""
Database adapter for ZooLingo PetCare data layer.

Supports two backends:
1. SQLite (default, local development)
2. Supabase PostgreSQL (production)

The router uses the adapter interface, so it works with either backend.
"""
from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Abstract adapter interface
# ---------------------------------------------------------------------------


class DatabaseAdapter(ABC):
    """Abstract database adapter for pet data storage."""

    @abstractmethod
    def init_db(self) -> None:
        """Create tables + seed demo data (idempotent)."""

    @abstractmethod
    def query_all(self, table: str, filters: Optional[dict] = None) -> list[dict]:
        """Select all rows from a table, optionally filtered."""

    @abstractmethod
    def query_one(self, table: str, filters: dict) -> Optional[dict]:
        """Select a single row from a table."""

    @abstractmethod
    def execute(self, table: str, data: dict) -> int:
        """Insert a row, return the new row ID."""

    @abstractmethod
    def update_row(self, table: str, row_id: int, data: dict) -> bool:
        """Update a row by ID, return True if a row was affected."""

    @abstractmethod
    def delete_row(self, table: str, row_id: int) -> bool:
        """Delete a row by ID, return True if a row was affected."""

    @abstractmethod
    def close(self) -> None:
        """Close the database connection."""


# ---------------------------------------------------------------------------
# SQLite adapter (default, local development)
# ---------------------------------------------------------------------------


class SQLiteAdapter(DatabaseAdapter):
    """SQLite implementation using the existing petcare.database module."""

    def __init__(self):
        from petcare.database import (
            _SEED,
            _SCHEMA,
            _conn,
            _conn_lock,
            _init_schema,
            _pet_id_for,
            get_conn,
        )

        self._SEED = _SEED
        self._SCHEMA = _SCHEMA
        self._conn = _conn
        self._conn_lock = _conn_lock
        self._init_schema = _init_schema
        self._pet_id_for = _pet_id_for
        self.get_conn = get_conn

    def init_db(self) -> None:
        with self._conn_lock:
            conn = self.get_conn()
            self._init_schema()
            self._seed_if_empty()

    def _seed_if_empty(self) -> None:
        count = self.query_one("pets", {})
        if count is not None and count.get("n", 0) > 0:
            return
        conn = self.get_conn()
        try:
            for p in self._SEED["pets"]:
                conn.execute(
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
            for v in self._SEED["vaccination_records"]:
                conn.execute(
                    "INSERT INTO vaccination_records (pet_id, name, administered_on, next_due_on) "
                    "VALUES (?,?,?,?)",
                    (
                        self._pet_id_for(v["pet_name"]),
                        v["name"],
                        v["administered_on"],
                        v["next_due_on"],
                    ),
                )
            for w in self._SEED["weight_log"]:
                conn.execute(
                    "INSERT INTO weight_log (pet_id, weight_kg, logged_on) VALUES (?,?,?)",
                    (
                        self._pet_id_for(w["pet_name"]),
                        w["weight_kg"],
                        w["logged_on"],
                    ),
                )
            for h in self._SEED["health_records"]:
                conn.execute(
                    "INSERT INTO health_records (pet_id, record_type, title, description, recorded_on) "
                    "VALUES (?,?,?,?,?)",
                    (
                        self._pet_id_for(h["pet_name"]),
                        h["record_type"],
                        h["title"],
                        h["description"],
                        h["recorded_on"],
                    ),
                )
            for c in self._SEED["care_schedules"]:
                conn.execute(
                    "INSERT INTO care_schedules (pet_id, task, category, frequency, time_of_day) "
                    "VALUES (?,?,?,?,?)",
                    (
                        self._pet_id_for(c["pet_name"]),
                        c["task"],
                        c["category"],
                        c["frequency"],
                        c["time_of_day"],
                    ),
                )
            for vc in self._SEED["vet_contacts"]:
                conn.execute(
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
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    def query_all(self, table: str, filters: Optional[dict] = None) -> list[dict]:
        from petcare.database import query_all as _qa

        if filters:
            where = " AND ".join(f"{k} = ?" for k in filters)
            sql = f"SELECT * FROM {table} WHERE {where}"
            return [dict(r) for r in _qa(sql, tuple(filters.values()))]
        return [dict(r) for r in _qa(f"SELECT * FROM {table}")]

    def query_one(self, table: str, filters: dict) -> Optional[dict]:
        from petcare.database import query_one as _qo

        where = " AND ".join(f"{k} = ?" for k in filters)
        sql = f"SELECT * FROM {table} WHERE {where}"
        row = _qo(sql, tuple(filters.values()))
        return dict(row) if row else None

    def execute(self, table: str, data: dict) -> int:
        from petcare.database import execute as _exec

        cols = ", ".join(data.keys())
        placeholders = ", ".join("?" for _ in data)
        sql = f"INSERT INTO {table} ({cols}) VALUES ({placeholders})"
        return _exec(sql, tuple(data.values()))

    def update_row(self, table: str, row_id: int, data: dict) -> bool:
        from petcare.database import execute as _exec

        sets = ", ".join(f"{k} = ?" for k in data)
        sql = f"UPDATE {table} SET {sets} WHERE id = ?"
        cur = _exec(sql, tuple(data.values()) + (row_id,))
        return cur > 0

    def delete_row(self, table: str, row_id: int) -> bool:
        from petcare.database import delete_row as _dr

        return _dr(f"DELETE FROM {table} WHERE id = ?", (row_id,))

    def close(self) -> None:
        from petcare.database import close_db

        close_db()


# ---------------------------------------------------------------------------
# Supabase adapter (production)
# ---------------------------------------------------------------------------


class SupabaseAdapter(DatabaseAdapter):
    """Supabase REST API implementation using the supabase-py client."""

    def __init__(self):
        from supabase import create_client

        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
        if not url or not key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY/ANON_KEY required")

        self._client = create_client(url, key)
        self._tables = {
            "pets": "pets",
            "vaccination_records": "vaccination_records",
            "weight_log": "weight_log",
            "health_records": "health_records",
            "care_schedules": "care_schedules",
            "vet_contacts": "vet_contacts",
        }

    def init_db(self) -> None:
        """Supabase tables are created via migrations; seed data is optional."""
        logger.info("Supabase adapter: tables expected to exist via migrations")

    def query_all(self, table: str, filters: Optional[dict] = None) -> list[dict]:
        query = self._client.table(self._tables[table]).select("*")
        if filters:
            for k, v in filters.items():
                query = query.eq(k, v)
        result = query.execute()
        return result.data or []

    def query_one(self, table: str, filters: dict) -> Optional[dict]:
        query = self._client.table(self._tables[table]).select("*")
        for k, v in filters.items():
            query = query.eq(k, v)
        result = query.limit(1).execute()
        return result.data[0] if result.data else None

    def execute(self, table: str, data: dict) -> int:
        data["created_at"] = datetime.now(timezone.utc).isoformat()
        result = self._client.table(self._tables[table]).insert(data).execute()
        return result.data[0]["id"] if result.data else 0

    def update_row(self, table: str, row_id: int, data: dict) -> bool:
        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        result = (
            self._client.table(self._tables[table])
            .update(data)
            .eq("id", row_id)
            .execute()
        )
        return bool(result.data)

    def delete_row(self, table: str, row_id: int) -> bool:
        result = (
            self._client.table(self._tables[table]).delete().eq("id", row_id).execute()
        )
        return bool(result.data)

    def close(self) -> None:
        pass


# ---------------------------------------------------------------------------
# Adapter factory
# ---------------------------------------------------------------------------


def get_adapter() -> DatabaseAdapter:
    """Return the appropriate database adapter based on environment config."""
    if os.getenv("SUPABASE_URL") and (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
    ):
        logger.info("Using Supabase adapter for pet data storage")
        return SupabaseAdapter()
    logger.info("Using SQLite adapter for pet data storage")
    return SQLiteAdapter()


# Global adapter instance
db = get_adapter()
