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

    def update_health_record(
        self, record_id: int, data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update a health record."""
        if not self._client:
            return None
        try:
            result = (
                self._client.table("health_records")
                .update(data)
                .eq("id", record_id)
                .execute()
            )
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Supabase update_health_record failed: {e}")
            return None

    def delete_health_record(self, record_id: int) -> bool:
        """Delete a health record."""
        if not self._client:
            return False
        try:
            self._client.table("health_records").delete().eq("id", record_id).execute()
            return True
        except Exception as e:
            logger.error(f"Supabase delete_health_record failed: {e}")
            return False

    # -- Vaccinations -----------------------------------------------------

    def create_vaccination(
        self, pet_id: int, record: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Create a vaccination record."""
        if not self._client:
            return None
        try:
            record["pet_id"] = pet_id
            result = self._client.table("vaccination_records").insert(record).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Supabase create_vaccination failed: {e}")
            return None

    def get_vaccinations(self, pet_id: int) -> List[Dict[str, Any]]:
        """Get all vaccinations for a pet."""
        if not self._client:
            return []
        try:
            result = (
                self._client.table("vaccination_records")
                .select("*")
                .eq("pet_id", pet_id)
                .execute()
            )
            return result.data
        except Exception as e:
            logger.error(f"Supabase get_vaccinations failed: {e}")
            return []

    def delete_vaccination(self, vacc_id: int) -> bool:
        """Delete a vaccination record."""
        if not self._client:
            return False
        try:
            self._client.table("vaccination_records").delete().eq("id", vacc_id).execute()
            return True
        except Exception as e:
            logger.error(f"Supabase delete_vaccination failed: {e}")
            return False

    # -- Weight logs ------------------------------------------------------

    def create_weight_log(
        self, pet_id: int, record: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Create a weight log entry."""
        if not self._client:
            return None
        try:
            record["pet_id"] = pet_id
            result = self._client.table("weight_log").insert(record).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Supabase create_weight_log failed: {e}")
            return None

    def get_weight_logs(self, pet_id: int) -> List[Dict[str, Any]]:
        """Get all weight logs for a pet."""
        if not self._client:
            return []
        try:
            result = (
                self._client.table("weight_log")
                .select("*")
                .eq("pet_id", pet_id)
                .execute()
            )
            return result.data
        except Exception as e:
            logger.error(f"Supabase get_weight_logs failed: {e}")
            return []

    def delete_weight_log(self, log_id: int) -> bool:
        """Delete a weight log entry."""
        if not self._client:
            return False
        try:
            self._client.table("weight_log").delete().eq("id", log_id).execute()
            return True
        except Exception as e:
            logger.error(f"Supabase delete_weight_log failed: {e}")
            return False

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

    def update_care_schedule(
        self, schedule_id: int, data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update a care schedule."""
        if not self._client:
            return None
        try:
            result = (
                self._client.table("care_schedules")
                .update(data)
                .eq("id", schedule_id)
                .execute()
            )
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Supabase update_care_schedule failed: {e}")
            return None

    def delete_care_schedule(self, schedule_id: int) -> bool:
        """Delete a care schedule."""
        if not self._client:
            return False
        try:
            self._client.table("care_schedules").delete().eq("id", schedule_id).execute()
            return True
        except Exception as e:
            logger.error(f"Supabase delete_care_schedule failed: {e}")
            return False

    def complete_care_schedule(self, schedule_id: int) -> Optional[Dict[str, Any]]:
        """Mark a care schedule as complete."""
        if not self._client:
            return None
        try:
            result = (
                self._client.table("care_schedules")
                .update({"active": False})
                .eq("id", schedule_id)
                .execute()
            )
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Supabase complete_care_schedule failed: {e}")
            return None

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

    def update_vet_contact(
        self, vet_id: int, data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update a vet contact."""
        if not self._client:
            return None
        try:
            result = (
                self._client.table("vet_contacts")
                .update(data)
                .eq("id", vet_id)
                .execute()
            )
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Supabase update_vet_contact failed: {e}")
            return None

    def delete_vet_contact(self, vet_id: int) -> bool:
        """Delete a vet contact."""
        if not self._client:
            return False
        try:
            self._client.table("vet_contacts").delete().eq("id", vet_id).execute()
            return True
        except Exception as e:
            logger.error(f"Supabase delete_vet_contact failed: {e}")
            return False

    # -- Medication schedules -------------------------------------------

    def create_medication_schedule(
        self, pet_id: int, schedule: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Create a medication schedule."""
        if not self._client:
            return None
        try:
            schedule["pet_id"] = pet_id
            result = (
                self._client.table("medication_schedules")
                .insert(schedule)
                .execute()
            )
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Supabase create_medication_schedule failed: {e}")
            return None

    def get_medication_schedules(self, pet_id: int) -> List[Dict[str, Any]]:
        """Get all medication schedules for a pet."""
        if not self._client:
            return []
        try:
            result = (
                self._client.table("medication_schedules")
                .select("*")
                .eq("pet_id", pet_id)
                .execute()
            )
            return result.data
        except Exception as e:
            logger.error(f"Supabase get_medication_schedules failed: {e}")
            return []

    def update_medication_schedule(
        self, schedule_id: int, data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update a medication schedule."""
        if not self._client:
            return None
        try:
            result = (
                self._client.table("medication_schedules")
                .update(data)
                .eq("id", schedule_id)
                .execute()
            )
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Supabase update_medication_schedule failed: {e}")
            return None

    def delete_medication_schedule(self, schedule_id: int) -> bool:
        """Delete a medication schedule."""
        if not self._client:
            return False
        try:
            self._client.table("medication_schedules").delete().eq("id", schedule_id).execute()
            return True
        except Exception as e:
            logger.error(f"Supabase delete_medication_schedule failed: {e}")
            return False

    # -- Reminders ------------------------------------------------------

    def create_reminder(
        self, user_id: str, reminder: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Create a reminder."""
        if not self._client:
            return None
        try:
            reminder["user_id"] = user_id
            result = self._client.table("reminders").insert(reminder).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Supabase create_reminder failed: {e}")
            return None

    def get_reminders(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all reminders for a user."""
        if not self._client:
            return []
        try:
            result = (
                self._client.table("reminders")
                .select("*")
                .eq("user_id", user_id)
                .execute()
            )
            return result.data
        except Exception as e:
            logger.error(f"Supabase get_reminders failed: {e}")
            return []

    def update_reminder(
        self, reminder_id: int, data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update a reminder."""
        if not self._client:
            return None
        try:
            result = (
                self._client.table("reminders")
                .update(data)
                .eq("id", reminder_id)
                .execute()
            )
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Supabase update_reminder failed: {e}")
            return None

    def delete_reminder(self, reminder_id: int) -> bool:
        """Delete a reminder."""
        if not self._client:
            return False
        try:
            self._client.table("reminders").delete().eq("id", reminder_id).execute()
            return True
        except Exception as e:
            logger.error(f"Supabase delete_reminder failed: {e}")
            return False

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
