"""
Utility helper functions.
"""
import re
from typing import Any, Dict


def sanitize_email(email: str) -> str:
    """Sanitize email address."""
    return email.lower().strip()


def is_valid_email(email: str) -> bool:
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def mask_sensitive_data(data: str, mask_char: str = "*", visible_chars: int = 4) -> str:
    """Mask sensitive data for logging."""
    if len(data) <= visible_chars:
        return mask_char * len(data)
    return data[:visible_chars] + mask_char * (len(data) - visible_chars)


def extract_client_info(request) -> Dict[str, Any]:
    """Extract client information from request."""
    return {
        "ip": request.headers.get("X-Forwarded-For", "").split(",")[0].strip() or request.client.host,
        "user_agent": request.headers.get("User-Agent", ""),
        "accept": request.headers.get("Accept", ""),
    }