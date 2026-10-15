"""
Authentication routes for ZooLingo.

Endpoints:
- POST /auth/register - Create a new account
- POST /auth/login - Obtain a JWT access token
- GET /auth/me - Get the current user's profile
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    authenticate_user,
    create_access_token,
    create_user,
    get_current_user,
    get_user_by_id,
)

router = APIRouter(prefix="/auth", tags=["auth"])


# ---------------------------------------------------------------------------
# Request/Response schemas
# ---------------------------------------------------------------------------


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


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


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(payload: UserRegister):
    """Create a new user account."""
    try:
        user = create_user(payload.email, payload.password)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    return UserOut(
        id=str(user["id"]),
        email=str(user["email"]),
        plan=str(user.get("plan", "free")),
        conversions_used=int(user.get("conversions_used", 0)),
        created_at=str(user["created_at"]),
    )


@router.post("/login", response_model=TokenResponse)
async def login(payload: UserLogin):
    """Authenticate and return a JWT access token."""
    user = authenticate_user(payload.email, payload.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(subject=str(user["id"]))
    return TokenResponse(
        access_token=access_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/me", response_model=UserOut)
async def me(current_user: dict = Depends(get_current_user)):
    """Return the currently authenticated user's profile."""
    return UserOut(
        id=str(current_user["id"]),
        email=str(current_user["email"]),
        plan=str(current_user.get("plan", "free")),
        conversions_used=int(current_user.get("conversions_used", 0)),
        created_at=str(current_user["created_at"]),
    )
