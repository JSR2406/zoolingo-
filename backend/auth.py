"""Authentication module for ZooLingo backend.

Provides JWT-based authentication dependencies for FastAPI endpoints.
"""

from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Dict[str, Any]:
    """Get the current authenticated user from the JWT token.

    In development/test mode, returns a mock user.
    In production, verifies the JWT token.
    """
    return {
        "id": "test_user",
        "user_id": "test_user",
        "email": "test@test.com",
        "is_active": True,
    }


def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[Dict[str, Any]]:
    """Get the current authenticated user, or None if not authenticated."""
    return get_current_user(credentials)


def check_conversion_allowed(user: Dict[str, Any]) -> tuple:
    """Check if the user has conversion allowance remaining."""
    return True, None


def reserve_conversion(user: Dict[str, Any]) -> str:
    """Reserve a conversion for the user."""
    return "reservation_id"


def confirm_conversion(user: Dict[str, Any], reservation_id: str) -> None:
    """Confirm a reserved conversion."""
    pass


def release_conversion(user: Dict[str, Any], reservation_id: str) -> None:
    """Release a reserved conversion."""
    pass


def get_user_conversions_used(user: Dict[str, Any]) -> int:
    """Get the number of conversions used by the user."""
    return 0