# app/schemas/auth.py
import re
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

# ── Shared response envelope ──────────────────────────────────────────────────

class APIResponse(BaseModel):
    success: bool = True
    message: str = "Operation successful"
    request_id: str = ""


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict = {}


class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail
    request_id: str = ""


# ── Registration ──────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        errors: list[str] = []
        if not re.search(r"[A-Z]", v):
            errors.append("at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            errors.append("at least one lowercase letter")
        if not re.search(r"\d", v):
            errors.append("at least one digit")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            errors.append("at least one special character")
        if errors:
            raise ValueError(f"Password must contain: {', '.join(errors)}")
        return v


class RegisterResponse(APIResponse):
    data: dict = Field(
        default_factory=dict,
        description="Contains user_id and email",
    )


# ── Login (step 1) ────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class LoginResponse(APIResponse):
    """
    On success without TOTP: returns full token pair.
    When TOTP is required: returns totp_required=True and a partial token.
    """
    data: dict = {}


# ── TOTP setup ────────────────────────────────────────────────────────────────

class TOTPSetupResponse(APIResponse):
    data: dict = Field(
        description="Contains totp_uri and qr_code_url (direct URL to QR code image)"
    )


class TOTPEnableRequest(BaseModel):
    """Confirm TOTP setup by submitting first valid code."""
    otp: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class TOTPEnableResponse(APIResponse):
    data: dict = Field(description="Contains backup_codes list")


# ── Login TOTP verification (step 2) ─────────────────────────────────────────

class TOTPVerifyRequest(BaseModel):
    otp: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")
    partial_token: str


class TOTPVerifyResponse(APIResponse):
    data: dict = Field(description="Contains access_token and refresh_token")


# ── Backup code verification ──────────────────────────────────────────────────

class BackupCodeVerifyRequest(BaseModel):
    backup_code: str = Field(min_length=11, max_length=11, pattern=r"^[A-Z0-9]{5}-[A-Z0-9]{5}$")
    partial_token: str


# ── Token refresh ─────────────────────────────────────────────────────────────

class RefreshTokenRequest(BaseModel):
    refresh_token: str


class TokenResponse(APIResponse):
    data: dict = Field(description="Contains access_token and refresh_token")


# ── Token revoke ──────────────────────────────────────────────────────────────

class RevokeTokenRequest(BaseModel):
    refresh_token: str


# ── User info ─────────────────────────────────────────────────────────────────

class UserProfile(BaseModel):
    id: str
    email: str
    is_active: bool
    is_verified: bool
    totp_enabled: bool
    created_at: datetime
    last_login_at: datetime | None = None

    model_config = {"from_attributes": True}


class UserProfileResponse(APIResponse):
    data: UserProfile