# app/routes/auth.py
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.base import get_db
from app.dependencies.auth import get_current_user
from app.utils.ratelimiter import rate_limit_auth, per_hour, per_minute
from app.models.users import User
from app.schemas.users import (
    BackupCodeVerifyRequest,
    LoginRequest,
    LoginResponse,
    RefreshTokenRequest,
    RegisterRequest,
    RegisterResponse,
    RevokeTokenRequest,
    TOTPEnableRequest,
    TOTPEnableResponse,
    TOTPSetupResponse,
    TOTPVerifyRequest,
    TOTPVerifyResponse,
    TokenResponse,
    UserProfileResponse,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])
logger = get_logger(__name__)


def _ip(request: Request) -> str | None:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


def _ua(request: Request) -> str | None:
    return request.headers.get("User-Agent")


# ── Registration ──────────────────────────────────────────────────────────────

@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
@per_hour(3)
async def register(
    payload: RegisterRequest,
    session: AsyncSession = Depends(get_db),
) -> RegisterResponse:
    svc = AuthService(session)
    data = await svc.register(email=payload.email, password=payload.password)
    return RegisterResponse(message="Account created successfully", data=data)


# ── Login (step 1) ────────────────────────────────────────────────────────────

@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Login with email and password",
)
@rate_limit_auth(5, 60)
async def login(
    payload: LoginRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> LoginResponse:
    svc = AuthService(session)
    data = await svc.login(
        email=payload.email,
        password=payload.password,
        ip_address=_ip(request),
        user_agent=_ua(request),
    )
    msg = "TOTP verification required" if data.get("totp_required") else "Login successful"
    return LoginResponse(message=msg, data=data)


# ── TOTP setup ────────────────────────────────────────────────────────────────

@router.post(
    "/totp/setup",
    response_model=TOTPSetupResponse,
    summary="Initiate TOTP 2FA setup – returns QR code",
)
async def totp_setup(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> TOTPSetupResponse:
    svc = AuthService(session)
    data = await svc.setup_totp(current_user.id)
    return TOTPSetupResponse(message="Scan the QR code with your authenticator app", data=data)


@router.post(
    "/totp/enable",
    response_model=TOTPEnableResponse,
    summary="Confirm TOTP setup with first OTP code",
)
async def totp_enable(
    payload: TOTPEnableRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> TOTPEnableResponse:
    svc = AuthService(session)
    data = await svc.enable_totp(current_user.id, payload.otp)
    return TOTPEnableResponse(
        message="2FA enabled. Store your backup codes securely – they will not be shown again.",
        data=data,
    )


# ── TOTP login verification (step 2) ─────────────────────────────────────────

@router.post(
    "/verify-totp",
    response_model=TOTPVerifyResponse,
    summary="Complete login by verifying TOTP code",
)
@rate_limit_auth(3, 60)
async def verify_totp(
    payload: TOTPVerifyRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> TOTPVerifyResponse:
    svc = AuthService(session)
    data = await svc.verify_totp_login(
        partial_token=payload.partial_token,
        otp=payload.otp,
        ip_address=_ip(request),
        user_agent=_ua(request),
    )
    return TOTPVerifyResponse(message="Login successful", data=data)


# ── Backup code verification ──────────────────────────────────────────────────

@router.post(
    "/verify-backup-code",
    response_model=TOTPVerifyResponse,
    summary="Complete login using a backup recovery code",
)
@rate_limit_auth(3, 60)
async def verify_backup_code(
    payload: BackupCodeVerifyRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> TOTPVerifyResponse:
    svc = AuthService(session)
    data = await svc.verify_backup_code_login(
        partial_token=payload.partial_token,
        backup_code=payload.backup_code,
        ip_address=_ip(request),
        user_agent=_ua(request),
    )
    return TOTPVerifyResponse(message="Login successful via backup code", data=data)


# ── Token management ──────────────────────────────────────────────────────────

@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Rotate refresh token and issue new access token",
)
async def refresh_token(
    payload: RefreshTokenRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> TokenResponse:
    svc = AuthService(session)
    data = await svc.refresh_tokens(
        raw_refresh_token=payload.refresh_token,
        ip_address=_ip(request),
        user_agent=_ua(request),
    )
    return TokenResponse(message="Tokens refreshed", data=data)


@router.post(
    "/logout",
    response_model=dict,
    summary="Revoke the current refresh token",
)
async def logout(
    payload: RevokeTokenRequest,
    session: AsyncSession = Depends(get_db),
) -> dict:
    svc = AuthService(session)
    await svc.logout(payload.refresh_token)
    return {"success": True, "message": "Logged out successfully"}


@router.post(
    "/logout-all",
    response_model=dict,
    summary="Revoke all refresh tokens for the current user",
)
async def logout_all(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    svc = AuthService(session)
    await svc.logout_all(current_user.id)
    return {"success": True, "message": "All sessions terminated"}


# ── Profile ───────────────────────────────────────────────────────────────────

@router.get(
    "/me",
    response_model=UserProfileResponse,
    summary="Get current user profile",
)
async def get_profile(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> UserProfileResponse:
    from app.schemas.users import UserProfile
    return UserProfileResponse(
        data=UserProfile.model_validate(current_user),
    )