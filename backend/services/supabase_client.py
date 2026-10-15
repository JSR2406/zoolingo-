"""
Supabase (PostgreSQL) client for ZooLingo pet data storage.

Provides CRUD operations for pet profiles, health records, care schedules,
and conversations. Falls back to local SQLite if Supabase is not configured.

Environment variables:
    SUPABASE_URL: https://xxx.supabase.co
    SUPABASE_SERVICE_ROLE_KEY: service role key
    SUPABASE_ANON_KEY: anon public key
"""
import logging
from typing import Any, Dict, List, Optional

from config import config

logger = logging.getLogger(__name__)


class SupabaseClient:
    """Thin client for Supabase REST API (PostgreSQL backend)."""

    def __init__(self):
        self.url = config.SUPABASE_URL
        self.service_role_key = config.SUPABASE_SERVICE_ROLE_KEY
        self.anon_key = config.SUPABASE_ANON_KEY
        self.enabled = config.SUPABASE_ENABLED
        self._client = None

        if self.enabled:
            try:
                from supabase import create_client

                self._client = create_client(self.url, self.service_role_key)
                logger.info("Supabase client initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize Supabase client: {e}")
                self.enabled = False

    # -- Pet operations -------------------------------------------------

    def create_pet(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new pet profile in Supabase."""
        if not self._client:
            return None
        try:
            result = self._client.table("pets").insert(data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Supabase create_pet failed: {e}")
            return None

    def get_pets(self, user_id: str = "default") -> List[Dict[str, Any]]:
        """Get all pets for a user."""
        if not self._client:
            return []
        try:
            result = (
                self._client.table("pets").select("*").eq("user_id", user_id).execute()
            )
            return result.data
        except Exception as e:
            logger.error(f"Supabase get_pets failed: {e}")
            return []

    def get_pet(self, pet_id: int) -> Optional[Dict[str, Any]]:
        """Get a single pet by ID."""
        if not self._client:
            return None
        try:
            result = self._client.table("pets").select("*").eq("id", pet_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Supabase get_pet failed: {e}")
            return None

    def update_pet(self, pet_id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update a pet profile."""
        if not self._client:
            return None
        try:
            result = self._client.table("pets").update(data).eq("id", pet_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Supabase update_pet failed: {e}")
            return None

    def delete_pet(self, pet_id: int) -> bool:
        """Delete a pet profile."""
        if not self._client:
            return False
        try:
            self._client.table("pets").delete().eq("id", pet_id).execute()
            return True
        except Exception as e:
            logger.error(f"Supabase delete_pet failed: {e}")
            return False

    # -- Health records -------------------------------------------------

    def create_health_record(
        self, pet_id: int, record: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Create a health record for a pet."""
        if not self._client:
            return None
        try:
            record["pet_id"] = pet_id
            result = self._client.table("health_records").insert(record).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Supabase create_health_record failed: {e}")
            return None

    def get_health_records(self, pet_id: int) -> List[Dict[str, Any]]:
        """Get all health records for a pet."""
        if not self._client:
            return []
        try:
            result = (
                self._client.table("health_records")
                .select("*")
                .eq("pet_id", pet_id)
                .order("recorded_on", desc=True)
                .execute()
            )
            return result.data
        except Exception as e:
            logger.error(f"Supabase get_health_records failed: {e}")
            return []

    # -- Care schedules -------------------------------------------------

    def create_care_schedule(
        self, pet_id: int, schedule: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Create a care schedule for a pet."""
        if not self._client:
            return None
        try:
            schedule["pet_id"] = pet_id
            result = self._client.table("care_schedules").insert(schedule).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Supabase create_care_schedule failed: {e}")
            return None

    def get_care_schedules(self, pet_id: int) -> List[Dict[str, Any]]:
        """Get all care schedules for a pet."""
        if not self._client:
            return []
        try:
            result = (
                self._client.table("care_schedules")
                .select("*")
                .eq("pet_id", pet_id)
                .execute()
            )
            return result.data
        except Exception as e:
            logger.error(f"Supabase get_care_schedules failed: {e}")
            return []

    # -- Vet contacts --------------------------------------------------

    def create_vet_contact(self, contact: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a vet contact."""
        if not self._client:
            return None
        try:
            result = self._client.table("vet_contacts").insert(contact).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Supabase create_vet_contact failed: {e}")
            return None

    def get_vet_contacts(self) -> List[Dict[str, Any]]:
        """Get all vet contacts."""
        if not self._client:
            return []
        try:
            result = self._client.table("vet_contacts").select("*").execute()
            return result.data
        except Exception as e:
            logger.error(f"Supabase get_vet_contacts failed: {e}")
            return []

    # -- Expert conversations -------------------------------------------

    def create_conversation(
        self, pet_id: int, role: str, content: str
    ) -> Optional[Dict[str, Any]]:
        """Store an expert chat conversation message."""
        if not self._client:
            return None
        try:
            result = (
                self._client.table("conversations")
                .insert({"pet_id": pet_id, "role": role, "content": content})
                .execute()
            )
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Supabase create_conversation failed: {e}")
            return None

    def get_conversations(self, pet_id: int) -> List[Dict[str, Any]]:
        """Get all conversation messages for a pet."""
        if not self._client:
            return []
        try:
            result = (
                self._client.table("conversations")
                .select("*")
                .eq("pet_id", pet_id)
                .order("created_at", desc=False)
                .execute()
            )
            return result.data
        except Exception as e:
            logger.error(f"Supabase get_conversations failed: {e}")
            return []


# Global singleton
supabase_client = SupabaseClient()
