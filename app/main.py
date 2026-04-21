# app/main.py
from typing import Any

from fastapi import FastAPI

from app.core.config import settings
from app.core.exception_handlers import register_exception_handlers
from app.core.logging import setup_logging
from app.middleware import setup_middleware
from app.routes.auth import router as auth_router

# ── Setup Logging ─────────────────────────────────────────────────────────────
setup_logging()


# ── Application Factory ───────────────────────────────────────────────────────
def create_application() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
    )

    # ── Setup Middleware ──────────────────────────────────────────────
    setup_middleware(app)

    # ── Setup Exception Handlers ──────────────────────────────────────
    register_exception_handlers(app)

    # ── Include Routers ───────────────────────────────────────────────
    app.include_router(auth_router)

    # ── Health Check Endpoints ────────────────────────────────────────
    @app.get("/health", tags=["Ops"])
    async def health_check() -> dict[str, Any]:
        return {"status": "ok", "version": settings.APP_VERSION}

    @app.get("/health/ready", tags=["Ops"])
    async def readiness_check() -> dict[str, Any]:
        """Check if the application is ready (database connectivity)."""
        from sqlalchemy import text

        from app.db.base import AsyncSessionLocal

        try:
            async with AsyncSessionLocal() as session:
                await session.execute(text("SELECT 1"))
            return {"status": "ready", "database": "ok"}
        except Exception as exc:
            return {"status": "not_ready", "database": str(exc)}

    return app


# ── Instantiate App ───────────────────────────────────────────────────────────
app = create_application()
