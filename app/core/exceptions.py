# app/core/exceptions.py
from fastapi import HTTPException, status


class BaseAPIException(HTTPException):
    """Base exception for all API errors."""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code: str = "INTERNAL_ERROR"
    message: str = "An unexpected error occurred"

    def __init__(self, message: str | None = None, details: dict | None = None) -> None:
        self.detail = {
            "code": self.error_code,
            "message": message or self.message,
            "details": details or {},
        }
        super().__init__(status_code=self.status_code, detail=self.detail)


# ── 400 Bad Request ───────────────────────────────────────────────────────────

class ValidationException(BaseAPIException):
    status_code = status.HTTP_400_BAD_REQUEST
    error_code = "VALIDATION_ERROR"
    message = "Request validation failed"


class InvalidCredentialsException(BaseAPIException):
    status_code = status.HTTP_400_BAD_REQUEST
    error_code = "INVALID_CREDENTIALS"
    message = "Invalid email or password"


class InvalidTOTPException(BaseAPIException):
    status_code = status.HTTP_400_BAD_REQUEST
    error_code = "INVALID_TOTP"
    message = "Invalid or expired TOTP code"


class InvalidBackupCodeException(BaseAPIException):
    status_code = status.HTTP_400_BAD_REQUEST
    error_code = "INVALID_BACKUP_CODE"
    message = "Invalid or already used backup code"


class TOTPAlreadyEnabledException(BaseAPIException):
    status_code = status.HTTP_400_BAD_REQUEST
    error_code = "TOTP_ALREADY_ENABLED"
    message = "TOTP 2FA is already enabled for this account"


class TOTPNotEnabledException(BaseAPIException):
    status_code = status.HTTP_400_BAD_REQUEST
    error_code = "TOTP_NOT_ENABLED"
    message = "TOTP 2FA is not enabled for this account"


# ── 401 Unauthorized ─────────────────────────────────────────────────────────

class AuthenticationException(BaseAPIException):
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "AUTHENTICATION_REQUIRED"
    message = "Authentication credentials are missing or invalid"


class TokenExpiredException(BaseAPIException):
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "TOKEN_EXPIRED"
    message = "Access token has expired"


class TokenInvalidException(BaseAPIException):
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "TOKEN_INVALID"
    message = "Access token is invalid or has been revoked"


class TOTPRequiredException(BaseAPIException):
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "TOTP_REQUIRED"
    message = "TOTP verification is required to complete login"


# ── 403 Forbidden ─────────────────────────────────────────────────────────────

class AuthorizationException(BaseAPIException):
    status_code = status.HTTP_403_FORBIDDEN
    error_code = "FORBIDDEN"
    message = "You do not have permission to perform this action"


class AccountLockedException(BaseAPIException):
    status_code = status.HTTP_403_FORBIDDEN
    error_code = "ACCOUNT_LOCKED"
    message = "Account temporarily locked due to too many failed attempts"


class AccountInactiveException(BaseAPIException):
    status_code = status.HTTP_403_FORBIDDEN
    error_code = "ACCOUNT_INACTIVE"
    message = "Account is inactive or has been suspended"


# ── 404 Not Found ─────────────────────────────────────────────────────────────

class NotFoundException(BaseAPIException):
    status_code = status.HTTP_404_NOT_FOUND
    error_code = "NOT_FOUND"
    message = "Requested resource not found"


class UserNotFoundException(NotFoundException):
    error_code = "USER_NOT_FOUND"
    message = "User not found"


# ── 409 Conflict ──────────────────────────────────────────────────────────────

class ConflictException(BaseAPIException):
    status_code = status.HTTP_409_CONFLICT
    error_code = "CONFLICT"
    message = "Resource already exists"


class UserAlreadyExistsException(ConflictException):
    error_code = "USER_ALREADY_EXISTS"
    message = "A user with this email already exists"


# ── 429 Too Many Requests ─────────────────────────────────────────────────────

class RateLimitException(BaseAPIException):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    error_code = "RATE_LIMIT_EXCEEDED"
    message = "Too many requests. Please try again later"