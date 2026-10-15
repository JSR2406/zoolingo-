"""
Authentication and authorization module for ZooLingo.

Provides:
- Password hashing with argon2-cffi
- JWT access token creation and verification
- FastAPI dependency to extract the current authenticated user
- In-memory user store (placeholder; replace with Supabase/PostgreSQL in production)

SECURITY NOTES:
- Secret keys must never be committed to version control. Use environment variables.
- JWT tokens are short-lived (15 minutes by default).
- Refresh tokens are NOT implemented in this stage; use access token only.
- All stateful endpoints must use get_current_user dependency.
"""
from __future__ import annotations

import hashlib
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SECRET_KEY = os.getenv("AUTH_SECRET_KEY")
if not SECRET_KEY:
    # In production this MUST be set via environment variable.
    # A fallback is provided only for local development.
    SECRET_KEY = "dev-secret-key-change-in-production"
    logger.warning(
        "AUTH_SECRET_KEY not set. Using insecure development default. "
        "Set AUTH_SECRET_KEY in production."
    )

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))

ph = PasswordHasher()
security = HTTPBearer(auto_error=False)


# ---------------------------------------------------------------------------
# Password hashing (argon2)
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    """Return an argon2 hash of the given plaintext password."""
    return ph.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against an argon2 hash."""
    try:
        ph.verify(hashed_password, plain_password)
        return True
    except VerificationError:
        return False


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------

def create_access_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
    """Create a signed JWT access token."""
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode: Dict[str, object] = {
        "sub": subject,
        "iat": now,
        "exp": expire,
    }
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[str]:
    """Decode a JWT and return the subject (user_id), or None if invalid."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        subject: Optional[str] = payload.get("sub")
        return subject
    except JWTError:
        return None


# ---------------------------------------------------------------------------
# In-memory user store (placeholder for production DB)
# ---------------------------------------------------------------------------

# In production, replace this with Supabase/PostgreSQL queries.
# Each user: { user_id: { "id": str, "email": str, "password_hash": str,
# "created_at": str, "plan": str, "conversions_used": int,
# "reservations": dict } }
_USERS: Dict[str, Dict[str, object]] = {}
_EMAIL_TO_ID: Dict[str, str] = {}


def _create_user_id(email: str) -> str:
    return "user_" + hashlib.sha256(email.encode("utf-8")).hexdigest()[:16]


def create_user(email: str, password: str) -> Dict[str, object]:
    """Create a new user. Raises ValueError if email already exists."""
    if email in _EMAIL_TO_ID:
        raise ValueError("Email already registered")

    user_id = _create_user_id(email)
    _USERS[user_id] = {
        "id": user_id,
        "email": email,
        "password_hash": hash_password(password),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "plan": "free",
        "conversions_used": 0,
        "reservations": {},
    }
    _EMAIL_TO_ID[email] = user_id
    return _USERS[user_id]


def get_user_by_email(email: str) -> Optional[Dict[str, object]]:
    """Look up a user by email."""
    user_id = _EMAIL_TO_ID.get(email)
    if user_id is None:
        return None
    return _USERS.get(user_id)


def get_user_by_id(user_id: str) -> Optional[Dict[str, object]]:
    """Look up a user by ID."""
    return _USERS.get(user_id)


def authenticate_user(email: str, password: str) -> Optional[Dict[str, object]]:
    """Verify email+password and return the user dict, or None."""
    user = get_user_by_email(email)
    if user is None:
        return None
    if not verify_password(password, str(user["password_hash"])):
        return None
    return user


# ---------------------------------------------------------------------------
# Usage enforcement (subscription plans)
# ---------------------------------------------------------------------------

# Plan configuration. In production this should come from a database table
# so it can be updated without redeploying code.
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
        "conversion_quota": None,  # Unlimited (to be configured)
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

    # None quota means unlimited (paid tiers)
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
    allowed, reason = check_conversion_allowed(user)
    if not allowed:
        raise ValueError(reason)

    reservation_id = "res_" + uuid.uuid4().hex[:16]
    # Store reservation in the user dict (in production, use a DB table)
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
        return  # Already processed or never existed

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


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Dict[str, object]:
    """
    Dependency that extracts and validates the current user from a Bearer JWT.

    Raises HTTPException(401) if no valid token is provided.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    user_id = decode_access_token(token)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = get_user_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

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
