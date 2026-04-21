# app/dependencies/auth.py
from fastapi import Depends, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.exceptions import AuthenticationException, AuthorizationException
from app.core.security import TokenType, decode_token
from app.db.base import get_db
from app.models.users import User
from app.repositories.user_repository import UserRepository
from sqlalchemy.ext.asyncio import AsyncSession

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
    session: AsyncSession = Depends(get_db),
) -> User:
    """
    Dependency that validates the Bearer token and returns the active user.
    Raises 401 if the token is missing, expired, or invalid.
    """
    if not credentials:
        raise AuthenticationException()

    payload = decode_token(credentials.credentials, TokenType.ACCESS)

    # Reject pre-2FA tokens from reaching protected routes
    if "pre_2fa" in payload.get("roles", []):
        raise AuthenticationException(message="2FA verification not completed")

    repo = UserRepository(session)
    user = await repo.get_by_id(payload["sub"])
    if not user or not user.is_active or user.is_deleted:
        raise AuthenticationException()

    # Validate token version (invalidated by logout-all)
    if payload.get("token_version") != user.token_version:
        raise AuthenticationException(message="Token has been revoked")

    return user


async def get_current_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_superuser:
        raise AuthorizationException()
    return current_user