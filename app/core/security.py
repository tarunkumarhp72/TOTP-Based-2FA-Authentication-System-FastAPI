# app/core/security.py
import secrets
import string
from datetime import datetime, timedelta, timezone
from enum import StrEnum

import bcrypt
import jwt

from app.core.config import settings
from app.core.exceptions import TokenExpiredException, TokenInvalidException
from app.core.logging import get_logger

logger = get_logger(__name__)

# ── Token types ───────────────────────────────────────────────────────────────

class TokenType(StrEnum):
    ACCESS = "access"
    REFRESH = "refresh"


# ── Password hashing ─────────────────────────────────────────────────────────

def hash_password(plain_password: str) -> str:
    """Hash a password using bcrypt with configured work factor."""
    salt = bcrypt.gensalt(rounds=settings.BCRYPT_ROUNDS)
    return bcrypt.hashpw(plain_password.encode(), salt).decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Constant-time password comparison to prevent timing attacks."""
    try:
        return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())
    except Exception:
        return False


# ── JWT tokens ────────────────────────────────────────────────────────────────

def _build_payload(
    subject: str,
    token_type: TokenType,
    extra: dict | None = None,
) -> dict:
    now = datetime.now(timezone.utc)
    if token_type == TokenType.ACCESS:
        expire = now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    else:
        expire = now + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)

    payload = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": expire,
        "jti": secrets.token_hex(16),
    }
    if extra:
        payload.update(extra)
    return payload


def create_access_token(user_id: str, roles: list[str] | None = None, token_version: int = 0) -> str:
    """Issue a short-lived access token."""
    payload = _build_payload(
        subject=user_id,
        token_type=TokenType.ACCESS,
        extra={"roles": roles or [], "token_version": token_version},
    )
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    """Issue a long-lived refresh token."""
    payload = _build_payload(subject=user_id, token_type=TokenType.REFRESH)
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str, expected_type: TokenType) -> dict:
    """
    Decode and validate a JWT.

    Raises TokenExpiredException or TokenInvalidException on failure.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except jwt.ExpiredSignatureError:
        raise TokenExpiredException()
    except jwt.InvalidTokenError:
        raise TokenInvalidException()

    if payload.get("type") != expected_type:
        raise TokenInvalidException(message="Unexpected token type")

    if expected_type == TokenType.ACCESS and "token_version" not in payload:
        raise TokenInvalidException(message="Missing token version")

    return payload


# ── Backup codes ──────────────────────────────────────────────────────────────

_BACKUP_ALPHABET = string.ascii_uppercase + string.digits


def generate_backup_codes(count: int | None = None) -> list[str]:
    """
    Generate one-time backup codes in the format XXXXX-XXXXX.
    Returns plaintext codes; the caller is responsible for hashing before storage.
    """
    n = count or settings.TOTP_BACKUP_CODE_COUNT
    return [
        f"{''.join(secrets.choice(_BACKUP_ALPHABET) for _ in range(5))}"
        f"-"
        f"{''.join(secrets.choice(_BACKUP_ALPHABET) for _ in range(5))}"
        for _ in range(n)
    ]


def hash_backup_code(code: str) -> str:
    """Hash a single backup code for storage."""
    return hash_password(code.upper().strip())


def verify_backup_code(plain_code: str, hashed_code: str) -> bool:
    """Verify a backup code in constant time."""
    return verify_password(plain_code.upper().strip(), hashed_code)