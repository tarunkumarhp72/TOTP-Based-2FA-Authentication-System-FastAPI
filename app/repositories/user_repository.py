# app/repositories/user_repository.py
import hashlib
import json
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.users import RefreshToken, User


class UserRepository:
    """
    Database access layer for User and RefreshToken.
    No business logic lives here — only CRUD operations.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ── User CRUD ─────────────────────────────────────────────────

    async def create(
        self,
        *,
        email: str,
        hashed_password: str,
    ) -> User:
        user = User(email=email.lower().strip(), hashed_password=hashed_password)
        self._session.add(user)
        await self._session.flush()  # populate ID without committing
        return user

    async def get_by_id(self, user_id: str) -> User | None:
        result = await self._session.execute(
            select(User).where(User.id == user_id, User.is_deleted.is_(False))
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(
            select(User).where(
                User.email == email.lower().strip(),
                User.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def update_totp_secret(self, user_id: str, secret: str | None) -> None:
        await self._session.execute(
            update(User)
            .where(User.id == user_id)
            .values(totp_secret=secret, updated_at=datetime.now(timezone.utc))
        )

    async def enable_totp(
        self, user_id: str, backup_code_hashes: list[str]
    ) -> None:
        await self._session.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                totp_enabled=True,
                backup_codes_hashed=json.dumps(backup_code_hashes),
                updated_at=datetime.now(timezone.utc),
            )
        )

    async def disable_totp(self, user_id: str) -> None:
        await self._session.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                totp_enabled=False,
                totp_secret=None,
                backup_codes_hashed=None,
                updated_at=datetime.now(timezone.utc),
            )
        )

    async def record_login_success(self, user_id: str) -> None:
        await self._session.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                failed_login_attempts=0,
                locked_until=None,
                last_login_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
        )

    async def record_login_failure(
        self, user_id: str, attempts: int, locked_until: datetime | None
    ) -> None:
        await self._session.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                failed_login_attempts=attempts,
                locked_until=locked_until,
                updated_at=datetime.now(timezone.utc),
            )
        )

    async def consume_backup_code(
        self, user_id: str, remaining_hashes: list[str]
    ) -> None:
        """Persist the backup code list after one code has been consumed."""
        await self._session.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                backup_codes_hashed=json.dumps(remaining_hashes),
                updated_at=datetime.now(timezone.utc),
            )
        )

    # ── Refresh tokens ────────────────────────────────────────────

    @staticmethod
    def _hash_token(raw_token: str) -> str:
        return hashlib.sha256(raw_token.encode()).hexdigest()

    async def store_refresh_token(
        self,
        *,
        user_id: str,
        raw_token: str,
        expires_at: datetime,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> RefreshToken:
        rt = RefreshToken(
            user_id=user_id,
            token_hash=self._hash_token(raw_token),
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        self._session.add(rt)
        await self._session.flush()
        return rt

    async def get_refresh_token(self, raw_token: str) -> RefreshToken | None:
        result = await self._session.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == self._hash_token(raw_token),
                RefreshToken.is_revoked.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def revoke_refresh_token(self, raw_token: str) -> None:
        await self._session.execute(
            update(RefreshToken)
            .where(RefreshToken.token_hash == self._hash_token(raw_token))
            .values(is_revoked=True)
        )

    async def revoke_all_user_tokens(self, user_id: str) -> None:
        await self._session.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id)
            .values(is_revoked=True)
        )

    async def increment_token_version(self, user_id: str) -> None:
        """Increment token version to invalidate all existing access tokens."""
        await self._session.execute(
            update(User)
            .where(User.id == user_id)
            .values(token_version=User.token_version + 1)
        )