"""
Authentication routes for ZooLingo using Supabase Auth.

Endpoints:
- GET /auth/me - Get the current user's profile (requires valid Supabase JWT)
- POST /auth/profile - Create or update the user's profile in the profiles table

Note: User signup/login happens client-side via supabase-js (Supabase Auth).
The backend only verifies the JWT and manages the profiles table.
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, EmailStr

from auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_user_profile,
    get_current_user,
    get_user_profile,
)

router = APIRouter(prefix="/auth", tags=["auth"])


# ---------------------------------------------------------------------------
# Request/Response schemas
# ---------------------------------------------------------------------------


class ProfileUpdate(BaseModel):
    email: Optional[str] = None
    plan: Optional[str] = None


class UserOut(BaseModel):
    id: str
    email: str
    plan: str
    conversions_used: int
    created_at: str

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/me", response_model=UserOut)
async def me(current_user: dict = Depends(get_current_user)):
    """Return the currently authenticated user's profile."""
    return UserOut(
        id=str(current_user["id"]),
        email=str(current_user.get("email", "")),
        plan=str(current_user.get("plan", "free")),
        conversions_used=int(current_user.get("conversions_used", 0)),
        created_at=str(current_user["created_at"]),
    )


@router.post("/profile", response_model=UserOut)
async def upsert_profile(
    payload: ProfileUpdate,
    current_user: dict = Depends(get_current_user),
):
    """Create or update the current user's profile in the profiles table."""
    user_id = str(current_user["id"])

    # Build update payload
    update_data = {}
    if payload.email is not None:
        update_data["email"] = payload.email
    if payload.plan is not None:
        update_data["plan"] = payload.plan

    # Try to persist to Supabase profiles table
    from supabase_client import supabase_client

    if supabase_client.enabled:
        try:
            supabase_client._client.table("profiles").upsert(
                {"id": user_id, **update_data}
            ).execute()
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to upsert profile to Supabase: {e}")

    # Update in-memory cache
    profile = create_user_profile(
        user_id,
        email=update_data.get("email", str(current_user.get("email", ""))),
        plan=update_data.get("plan", str(current_user.get("plan", "free"))),
    )

    return UserOut(
        id=str(profile["id"]),
        email=str(profile.get("email", "")),
        plan=str(profile.get("plan", "free")),
        conversions_used=int(profile.get("conversions_used", 0)),
        created_at=str(profile["created_at"]),
    )
