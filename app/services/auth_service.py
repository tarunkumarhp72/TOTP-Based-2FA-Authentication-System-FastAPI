# app/services/auth_service.py
import json
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    AccountInactiveException,
    AccountLockedException,
    InvalidBackupCodeException,
    InvalidCredentialsException,
    InvalidTOTPException,
    TOTPAlreadyEnabledException,
    TOTPNotEnabledException,
    TOTPRequiredException,
    TokenInvalidException,
    UserAlreadyExistsException,
    UserNotFoundException,
)
from app.core.logging import get_logger
from app.core.security import (
    TokenType,
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_backup_codes,
    hash_backup_code,
    hash_password,
    verify_backup_code,
    verify_password,
)
from app.models.users import User
from app.repositories.user_repository import UserRepository
from app.utils.totp import (
    generate_qr_code_url,
    generate_totp_secret,
    generate_totp_uri,
    verify_totp,
)

logger = get_logger(__name__)


class AuthService:
    """
    Orchestrates all authentication flows.
    Receives a DB session, creates the repository, and delegates persistence.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._repo = UserRepository(session)

    # ── Registration ──────────────────────────────────────────────

    async def register(self, email: str, password: str) -> dict:
        """
        Create a new user account.
        Returns the user ID and email on success.
        """
        existing = await self._repo.get_by_email(email)
        if existing:
            raise UserAlreadyExistsException()

        hashed = hash_password(password)
        user = await self._repo.create(email=email, hashed_password=hashed)

        logger.info("user_registered", extra={"user_id": user.id, "email": email})
        return {"user_id": user.id, "email": user.email}

    # ── Login ─────────────────────────────────────────────────────

    async def login(
        self,
        email: str,
        password: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> dict:
        """
        Step 1 of login.

        - If TOTP is not enabled: returns full token pair immediately.
        - If TOTP is enabled: returns a short-lived partial token that must be
          exchanged via /auth/verify-totp within 5 minutes.
        """
        user = await self._repo.get_by_email(email)

        # Generic error – avoid leaking whether the email exists
        if not user or not verify_password(password, user.hashed_password):
            if user:
                await self._increment_failure(user)
            logger.warning(
                "login_failed",
                extra={"email": email, "ip": ip_address, "reason": "bad_credentials"},
            )
            raise InvalidCredentialsException()

        self._check_account_health(user)

        await self._repo.record_login_success(user.id)
        logger.info("login_success_step1", extra={"user_id": user.id, "ip": ip_address})

        if user.totp_enabled:
            # Issue a partial (pre-2FA) token so step 2 can reference this user
            partial_token = create_access_token(
                user_id=user.id,
                roles=["pre_2fa"],
                token_version=user.token_version,
            )
            return {"totp_required": True, "partial_token": partial_token}

        # No 2FA – issue full token pair
        return await self._issue_full_tokens(
            user=user,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    # ── TOTP setup ────────────────────────────────────────────────

    async def setup_totp(self, user_id: str) -> dict:
        """
        Generate a TOTP secret + QR code for the user to scan.
        The secret is stored but totp_enabled remains False until confirmed.
        """
        user = await self._get_active_user(user_id)
        if user.totp_enabled:
            raise TOTPAlreadyEnabledException()

        secret = generate_totp_secret()
        await self._repo.update_totp_secret(user_id, secret)

        uri = generate_totp_uri(secret, user.email)
        qr_url = generate_qr_code_url(uri)

        logger.info("totp_setup_initiated", extra={"user_id": user_id})
        return {"totp_uri": uri, "qr_code_url": qr_url}

    async def enable_totp(self, user_id: str, otp: str) -> dict:
        """
        Confirm TOTP setup by verifying the first code.
        Enables 2FA and returns plaintext backup codes (shown once).
        """
        user = await self._get_active_user(user_id)
        if user.totp_enabled:
            raise TOTPAlreadyEnabledException()
        if not user.totp_secret:
            raise TOTPNotEnabledException(message="Run /auth/totp/setup first")

        if not verify_totp(user.totp_secret, otp):
            raise InvalidTOTPException()

        plain_codes = generate_backup_codes()
        hashed_codes = [hash_backup_code(c) for c in plain_codes]
        await self._repo.enable_totp(user_id, hashed_codes)

        logger.info("totp_enabled", extra={"user_id": user_id})
        return {"backup_codes": plain_codes}

    # ── TOTP login verification (step 2) ──────────────────────────

    async def verify_totp_login(
        self,
        partial_token: str,
        otp: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> dict:
        """Complete the 2FA login flow by verifying the TOTP code."""
        user_id = self._extract_pre2fa_subject(partial_token)
        user = await self._get_active_user(user_id)

        if not user.totp_enabled or not user.totp_secret:
            raise TOTPNotEnabledException()

        if not verify_totp(user.totp_secret, otp):
            logger.warning("totp_verify_failed", extra={"user_id": user_id, "ip": ip_address})
            raise InvalidTOTPException()

        logger.info("totp_verify_success", extra={"user_id": user_id, "ip": ip_address})
        return await self._issue_full_tokens(
            user=user,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    # ── Backup code verification ───────────────────────────────────

    async def verify_backup_code_login(
        self,
        partial_token: str,
        backup_code: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> dict:
        """Use a backup code instead of TOTP to complete login."""
        user_id = self._extract_pre2fa_subject(partial_token)
        user = await self._get_active_user(user_id)

        if not user.totp_enabled:
            raise TOTPNotEnabledException()

        stored_hashes: list[str] = json.loads(user.backup_codes_hashed or "[]")
        matched_index: int | None = None

        for i, hashed in enumerate(stored_hashes):
            if verify_backup_code(backup_code, hashed):
                matched_index = i
                break

        if matched_index is None:
            logger.warning("backup_code_failed", extra={"user_id": user_id})
            raise InvalidBackupCodeException()

        # Remove the used code (single-use)
        remaining = stored_hashes[:matched_index] + stored_hashes[matched_index + 1:]
        await self._repo.consume_backup_code(user_id, remaining)

        logger.info(
            "backup_code_used",
            extra={"user_id": user_id, "remaining_codes": len(remaining)},
        )
        return await self._issue_full_tokens(
            user=user,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    # ── Token refresh ─────────────────────────────────────────────

    async def refresh_tokens(
        self,
        raw_refresh_token: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> dict:
        """Rotate the refresh token and issue a new access token."""
        payload = decode_token(raw_refresh_token, TokenType.REFRESH)
        user_id: str = payload["sub"]

        stored = await self._repo.get_refresh_token(raw_refresh_token)
        if not stored or stored.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            raise TokenInvalidException(message="Refresh token not found or expired")

        user = await self._get_active_user(user_id)

        # Revoke old token (rotation)
        await self._repo.revoke_refresh_token(raw_refresh_token)

        return await self._issue_full_tokens(user=user, ip_address=ip_address, user_agent=user_agent)

    # ── Logout ────────────────────────────────────────────────────

    async def logout(self, raw_refresh_token: str) -> None:
        await self._repo.revoke_refresh_token(raw_refresh_token)
        logger.info("user_logged_out")

    async def logout_all(self, user_id: str) -> None:
        await self._repo.revoke_all_user_tokens(user_id)
        await self._repo.increment_token_version(user_id)
        logger.info("user_all_tokens_revoked", extra={"user_id": user_id})

    # ── Profile ───────────────────────────────────────────────────

    async def get_profile(self, user_id: str) -> User:
        return await self._get_active_user(user_id)

    # ── Private helpers ───────────────────────────────────────────

    async def _get_active_user(self, user_id: str) -> User:
        user = await self._repo.get_by_id(user_id)
        if not user:
            raise UserNotFoundException()
        self._check_account_health(user)
        return user

    @staticmethod
    def _check_account_health(user: User) -> None:
        if not user.is_active:
            raise AccountInactiveException()
        if user.locked_until and user.locked_until > datetime.now(timezone.utc):
            raise AccountLockedException(
                message=f"Account locked until {user.locked_until.isoformat()}"
            )

    async def _increment_failure(self, user: User) -> None:
        attempts = user.failed_login_attempts + 1
        locked_until: datetime | None = None
        if attempts >= settings.MAX_LOGIN_ATTEMPTS:
            locked_until = datetime.now(timezone.utc) + timedelta(
                minutes=settings.LOCKOUT_DURATION_MINUTES
            )
            logger.warning(
                "account_locked",
                extra={"user_id": user.id, "locked_until": locked_until.isoformat()},
            )
        await self._repo.record_login_failure(user.id, attempts, locked_until)

    async def _issue_full_tokens(
        self,
        user: User,
        ip_address: str | None,
        user_agent: str | None,
    ) -> dict:
        access_token = create_access_token(user_id=user.id, token_version=user.token_version)
        raw_refresh = create_refresh_token(user_id=user.id)

        expires_at = datetime.now(timezone.utc) + timedelta(
            days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
        )
        await self._repo.store_refresh_token(
            user_id=user.id,
            raw_token=raw_refresh,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return {
            "access_token": access_token,
            "refresh_token": raw_refresh,
            "token_type": "bearer",
        }

    @staticmethod
    def _extract_pre2fa_subject(partial_token: str) -> str:
        """Decode the partial token and ensure it's a pre-2FA access token."""
        payload = decode_token(partial_token, TokenType.ACCESS)
        if "pre_2fa" not in payload.get("roles", []):
            raise TokenInvalidException(message="Not a pre-2FA token")
        return payload["sub"]