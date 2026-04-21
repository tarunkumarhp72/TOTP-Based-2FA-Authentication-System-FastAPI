"""
Rate limiting decorators for endpoints.
Apply directly to routes without needing .env configuration.
"""
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from functools import wraps
from typing import Any, Callable

import asyncio

from fastapi import Request

from app.core.exceptions import RateLimitException
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class RateLimitRule:
    """Configuration for rate limiting."""
    max_requests: int
    window_seconds: int


class RateLimiter:
    """In-memory sliding-window rate limiter."""
    
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._windows: dict[str, deque[float]] = defaultdict(deque)
    
    async def is_allowed(self, key: str, rule: RateLimitRule) -> bool:
        """Check if request is allowed under the rate limit rule."""
        now = time.monotonic()
        cutoff = now - rule.window_seconds
        
        async with self._lock:
            window = self._windows[key]
            # Remove old timestamps outside the window
            while window and window[0] < cutoff:
                window.popleft()
            
            if len(window) >= rule.max_requests:
                return False
            
            window.append(now)
            return True


# Global rate limiter instance
_limiter = RateLimiter()


def rate_limit(max_requests: int, window_seconds: int = 60) -> Callable:
    """
    Decorator to apply rate limiting to an endpoint.
    
    Args:
        max_requests: Maximum number of requests allowed in the window
        window_seconds: Time window in seconds (default: 60)
    
    Usage:
        @app.post("/api/v1/auth/login")
        @rate_limit(max_requests=5, window_seconds=60)
        async def login(request: Request, ...):
            ...
    
    Example:
        # 5 login attempts per minute
        @rate_limit(5, 60)
        
        # 3 registrations per hour
        @rate_limit(3, 3600)
        
        # 10 requests per 5 seconds
        @rate_limit(10, 5)
    """
    rule = RateLimitRule(max_requests=max_requests, window_seconds=window_seconds)
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Extract request from args/kwargs
            request: Request | None = None
            
            # Check positional args for Request
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            # Check kwargs for Request
            if not request:
                request = kwargs.get("request")
            
            if not request:
                raise ValueError("Request object not found in function arguments")
            
            # Build rate limit key: IP + endpoint
            client_ip = request.client.host if request.client else "unknown"
            endpoint = request.url.path
            key = f"rate:{client_ip}:{endpoint}"
            
            # Check if allowed
            allowed = await _limiter.is_allowed(key, rule)
            if not allowed:
                logger.warning(
                    "rate_limit_exceeded",
                    extra={
                        "ip": client_ip,
                        "path": endpoint,
                        "limit": max_requests,
                        "window": window_seconds,
                    },
                )
                raise RateLimitException()
            
            # Call the original function
            return await func(*args, **kwargs)
        
        return wrapper
    
    return decorator
