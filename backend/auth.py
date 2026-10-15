"""
Authentication and authorization module for ZooLingo using Supabase Auth.

Provides:
- JWT verification of Supabase Auth access tokens
- FastAPI dependency to extract the current authenticated user
- In-memory user profile cache (placeholder; replace with Supabase table queries)

SECURITY NOTES:
- Supabase JWTs are signed with the project's JWT secret. Verify using
  SUPABASE_JWT_SECRET from environment.
- All stateful endpoints must use get_current_user dependency.
- Never trust user_id from request parameters — always derive from the JWT.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Optional, Dict

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

if not SUPABASE_JWT_SECRET:
    logger.warning(
        "SUPABASE_JWT_SECRET not set. Auth will reject all tokens. "
        "Set it from Supabase Dashboard -> Project Settings -> API -> JWT Secret."
    )

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
security = HTTPBearer(auto_error=False)


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------

def decode_supabase_token(token: str) -> Optional[Dict[str, object]]:
    """Decode and verify a Supabase Auth JWT.

    Returns the token payload (dict) or None if invalid.
    """
    if not SUPABASE_JWT_SECRET:
        return None

    try:
        payload = jwt.decode(
            token,
            SUPABASE_JWT_SECRET,
            algorithms=[ALGORITHM],
            options={"verify_aud": False},  # Supabase doesn't always include aud
        )
        return payload
    except JWTError:
        return None


def get_user_id_from_token(token: str) -> Optional[str]:
    """Extract the authenticated user's UUID from a Supabase JWT."""
    payload = decode_supabase_token(token)
    if payload is None:
        return None
    # Supabase stores the user UUID in the "sub" claim
    sub = payload.get("sub")
    return str(sub) if sub else None


# ---------------------------------------------------------------------------
# In-memory user profile cache (placeholder for Supabase profiles table)
# ---------------------------------------------------------------------------

# In production, replace this with Supabase table queries via the
# supabase_client. Each profile: { user_id: { "id": str, "email": str,
# "plan": str, "conversions_used": int, "created_at": str } }
_USER_PROFILES: Dict[str, Dict[str, object]] = {}


def get_user_profile(user_id: str) -> Optional[Dict[str, object]]:
    """Look up a user profile by Supabase Auth user ID."""
    return _USER_PROFILES.get(user_id)


def create_user_profile(
    user_id: str, email: str, plan: str = "free"
) -> Dict[str, object]:
    """Create or update a user profile."""
    profile = {
        "id": user_id,
        "email": email,
        "plan": plan,
        "conversions_used": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "reservations": {},
    }
    _USER_PROFILES[user_id] = profile
    return profile


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Dict[str, object]:
    """
    Dependency that extracts and validates the current user from a Supabase
    Bearer JWT.

    Raises HTTPException(401) if no valid token is provided.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    user_id = get_user_id_from_token(token)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Try to load profile from Supabase profiles table; fall back to cache
    user = get_user_profile(user_id)
    if user is None:
        # Create a minimal profile on first authenticated request
        user = create_user_profile(user_id, email="", plan="free")

    return user


# Optional dependency: returns None if not authenticated (for public endpoints)
async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[Dict[str, object]]:
    """Return the current user if authenticated, otherwise None."""
    if credentials is None:
        return None
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None


# ---------------------------------------------------------------------------
# Usage enforcement (subscription plans)
# ---------------------------------------------------------------------------

PLAN_CONFIG: Dict[str, Dict[str, object]] = {
    "free": {
        "name": "Free",
        "price_monthly_inr": 0,
        "conversion_quota": 2,  # One-time allowance, not monthly reset
        "features": ["basic_translation", "hindi_english_tts"],
    },
    "pro": {
        "name": "Pro",
        "price_monthly_inr": 599,
        "conversion_quota": None,  # Unlimited (to be configured)
        "features": ["basic_translation", "hindi_english_tts", "priority_support"],
    },
    "premium": {
        "name": "Premium",
        "price_monthly_inr": 1599,
        "conversion_quota": None,
        "features": [
            "basic_translation",
            "hindi_english_tts",
            "priority_support",
            "advanced_analytics",
        ],
    },
}

# NOTE: Paid conversion quotas and the precise Pro/Premium feature split
# have NOT been specified. This configuration is a placeholder and must be
# finalized before production deployment. The free tier quota (2 conversions,
# one-time) is the only confirmed value.


def get_user_plan(user: dict) -> str:
    """Return the user's plan name."""
    return str(user.get("plan", "free"))


def get_user_conversions_used(user: dict) -> int:
    """Return the number of conversions the user has used."""
    return int(user.get("conversions_used", 0))


def check_conversion_allowed(user: dict) -> tuple[bool, str]:
    """
    Check if the user is allowed to perform another conversion.

    Returns (allowed, reason_message).
    """
    plan = get_user_plan(user)
    plan_config = PLAN_CONFIG.get(plan, PLAN_CONFIG["free"])
    quota = plan_config.get("conversion_quota")

    if quota is None:
        return True, ""

    used = get_user_conversions_used(user)
    if used >= quota:
        return False, (
            f"Free allowance of {quota} conversions exhausted. "
            "Upgrade to Pro or Premium for more conversions."
        )

    return True, ""


def reserve_conversion(user: dict) -> str:
    """
    Atomically reserve a conversion for the user.

    Returns a reservation_id that must be finalised (confirm_conversion)
    or released (release_conversion) after the operation completes.

    Raises ValueError if the user has no remaining conversions.
    """
    import uuid

    allowed, reason = check_conversion_allowed(user)
    if not allowed:
        raise ValueError(reason)

    reservation_id = "res_" + uuid.uuid4().hex[:16]
    if "reservations" not in user:
        user["reservations"] = {}
    user["reservations"][reservation_id] = {
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    return reservation_id


def confirm_conversion(user: dict, reservation_id: str) -> None:
    """
    Finalise a reserved conversion: increment the usage counter.

    Should be called only after a usable interpretation and playable speech
    output have been successfully produced.
    """
    reservations = user.get("reservations", {})
    if reservation_id not in reservations:
        return

    reservations[reservation_id]["status"] = "confirmed"
    reservations[reservation_id]["confirmed_at"] = datetime.now(timezone.utc).isoformat()

    user["conversions_used"] = get_user_conversions_used(user) + 1


def release_conversion(user: dict, reservation_id: str) -> None:
    """
    Release a reserved conversion without incrementing the counter.

    Called on failure or timeout so the user doesn't lose their allowance.
    """
    reservations = user.get("reservations", {})
    if reservation_id in reservations:
        reservations[reservation_id]["status"] = "released"
        reservations[reservation_id]["released_at"] = datetime.now(timezone.utc).isoformat()
