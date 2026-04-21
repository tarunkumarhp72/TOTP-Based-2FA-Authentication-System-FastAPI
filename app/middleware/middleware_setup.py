"""
Middleware setup for the FastAPI application.
"""
import uuid
from typing import Any

from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.core.config import settings
from app.core.logging import request_id_ctx
from app.middleware.rate_limit import RateLimitMiddleware


def setup_middleware(app: Any) -> None:
    """Setup all middleware for the FastAPI app."""
    # CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    )

    # Trusted Host Middleware
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_HOSTS,
    )

    # Rate Limit Middleware
    app.add_middleware(RateLimitMiddleware)

    # Request ID & Security Headers Middleware
    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        """Add request ID and security headers to all responses."""
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        token = request_id_ctx.set(request_id)
        response = await call_next(request)
        request_id_ctx.reset(token)

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        return response
