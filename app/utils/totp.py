# app/utils/totp.py
import urllib.parse

import pyotp

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def generate_totp_secret() -> str:
    """Generate a cryptographically secure base32 TOTP secret."""
    return pyotp.random_base32()


def get_totp(secret: str) -> pyotp.TOTP:
    return pyotp.TOTP(secret)


def generate_totp_uri(secret: str, email: str) -> str:
    """Build an otpauth:// URI for authenticator app import."""
    totp = get_totp(secret)
    return totp.provisioning_uri(name=email, issuer_name=settings.TOTP_ISSUER)


def generate_qr_code_url(uri: str) -> str:
    """
    Generate a QR code URL from the TOTP URI using QR Server API.
    Returns a direct URL to the QR code image.
    """
    encoded_uri = urllib.parse.quote(uri)
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={encoded_uri}"
    return qr_url


def verify_totp(secret: str, code: str) -> bool:
    """
    Verify a 6-digit TOTP code.
    valid_window=1 allows ±30s clock skew (one step before/after).
    """
    try:
        totp = get_totp(secret)
        return totp.verify(code.strip(), valid_window=1)
    except Exception:
        logger.warning("TOTP verification raised an unexpected exception")
        return False