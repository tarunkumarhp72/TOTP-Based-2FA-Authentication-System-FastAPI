# app/middleware/rate_limit.py
"""
Sliding-window rate limiter.

In production, replace the InMemoryBackend with RedisBackend for
consistency across multiple application instances.
"""
import asyncio
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.core.exceptions import RateLimitException
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class RuleConfig:
    """
    max_requests: maximum allowed calls in the window.
    window_seconds: sliding window duration.
    """
    max_requests: int
    window_seconds: int


# ── Route-specific limits ─────────────────────────────────────────────────────
ROUTE_RULES: dict[str, RuleConfig] = {
    "/api/v1/auth/login": RuleConfig(max_requests=5, window_seconds=60),
    "/api/v1/auth/register": RuleConfig(max_requests=3, window_seconds=3600),
    "/api/v1/auth/verify-totp": RuleConfig(max_requests=3, window_seconds=60),
    "/api/v1/auth/refresh": RuleConfig(max_requests=10, window_seconds=60),
}

DEFAULT_RULE = RuleConfig(max_requests=60, window_seconds=60)


# ── In-memory backend (single-process only) ───────────────────────────────────

class InMemoryBackend:
    """
    Thread-safe sliding-window counter backed by an in-process deque.
    ⚠️  Not suitable for multi-process deployments – use RedisBackend instead.
    """

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        # key → deque of request timestamps
        self._windows: dict[str, deque[float]] = defaultdict(deque)

    async def is_allowed(self, key: str, rule: RuleConfig) -> bool:
        now = time.monotonic()
        cutoff = now - rule.window_seconds

        async with self._lock:
            window = self._windows[key]
            # Evict timestamps outside the current window
            while window and window[0] < cutoff:
                window.popleft()

            if len(window) >= rule.max_requests:
                return False

            window.append(now)
            return True


_backend = InMemoryBackend()


def _client_key(request: Request, path: str) -> str:
    """Build a per-client, per-route key from the request's IP address."""
    client_ip = request.client.host if request.client else "unknown"
    return f"rate:{client_ip}:{path}"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Applies sliding-window rate limits based on ROUTE_RULES."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        path = request.url.path
        rule = ROUTE_RULES.get(path, DEFAULT_RULE)
        key = _client_key(request, path)

        allowed = await _backend.is_allowed(key, rule)
        if not allowed:
            client_ip = request.client.host if request.client else "unknown"
            logger.warning(
                "rate_limit_exceeded",
                extra={"ip": client_ip, "path": path},
            )
            raise RateLimitException()

        return await call_next(request)