"""
Simple and optimized rate limiting decorators.
Apply directly to routes without .env configuration.
"""
import time
import asyncio
from collections import defaultdict, deque
from functools import wraps
from typing import Callable, Any

from fastapi import Request, HTTPException, status

from app.core.logging import get_logger

logger = get_logger(__name__)


class RateLimiter:
    """In-memory sliding window rate limiter."""
    
    def __init__(self):
        self._lock = asyncio.Lock()
        self._windows = defaultdict(deque)
    
    async def is_allowed(self, key: str, limit: int, window: int) -> bool:
        """Check if request is allowed."""
        now = time.monotonic()
        cutoff = now - window
        
        async with self._lock:
            timestamps = self._windows[key]
            
            # Remove old timestamps
            while timestamps and timestamps[0] < cutoff:
                timestamps.popleft()
            
            # Check limit
            if len(timestamps) >= limit:
                return False
            
            # Add current request
            timestamps.append(now)
            return True


# Global instance
_limiter = RateLimiter()


def _get_key(request: Request) -> str:
    """Get rate limit key from request."""
    # Try to get user ID if authenticated
    user = getattr(request.state, "user", None)
    if user and hasattr(user, "id"):
        return f"user:{user.id}"
    
    # Fallback to IP
    ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
    if not ip:
        ip = request.client.host if request.client else "unknown"
    
    return f"ip:{ip}"


def rate_limit(limit: int, window: int = 60) -> Callable:
    """
    Rate limiting decorator.
    
    Args:
        limit: Max requests allowed
        window: Time window in seconds (default: 60)
    
    Usage:
        @rate_limit(5, 60)  # 5 requests per minute
        @rate_limit(10, 300)  # 10 requests per 5 minutes
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Find request object
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            if not request:
                request = kwargs.get("request")
            if not request:
                return await func(*args, **kwargs)
            
            # Check rate limit
            key = f"{_get_key(request)}:{request.url.path}"
            allowed = await _limiter.is_allowed(key, limit, window)
            
            if not allowed:
                logger.warning(
                    "Rate limit exceeded",
                    extra={
                        "key": key,
                        "limit": limit,
                        "window": window,
                        "path": request.url.path
                    }
                )
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many requests"
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


# ── Convenience decorators ──────────────────────────────────────────────

def rate_limit_auth(limit: int = 5, window: int = 60) -> Callable:
    """Auth endpoints rate limit (default: 5/minute)."""
    return rate_limit(limit, window)


def rate_limit_api(limit: int = 60, window: int = 60) -> Callable:
    """General API rate limit (default: 60/minute)."""
    return rate_limit(limit, window)


def rate_limit_heavy(limit: int = 10, window: int = 60) -> Callable:
    """Heavy operations rate limit (default: 10/minute)."""
    return rate_limit(limit, window)


# ── Time-based helpers ─────────────────────────────────────────────────

def per_minute(limit: int) -> Callable:
    """Rate limit per minute."""
    return rate_limit(limit, 60)


def per_hour(limit: int) -> Callable:
    """Rate limit per hour."""
    return rate_limit(limit, 3600)


def per_day(limit: int) -> Callable:
    """Rate limit per day."""
    return rate_limit(limit, 86400)
