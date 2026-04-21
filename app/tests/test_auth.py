# app/tests/test_auth.py
"""
Integration tests for the authentication API.
Run with: pytest app/tests/ -v
"""
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base, get_db
from app.main import app
from app.middleware.rate_limit import _backend

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestSession = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Reset rate limiter state between tests
    _backend._windows.clear()
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    async def override_get_db():
        async with TestSession() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db

    # Use localhost so TrustedHostMiddleware passes
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://localhost",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


VALID_USER = {"email": "test@example.com", "password": "SecureP@ss1"}


class TestRegistration:
    async def test_register_success(self, client):
        resp = await client.post("/api/v1/auth/register", json=VALID_USER)
        assert resp.status_code == 201
        assert resp.json()["success"] is True

    async def test_register_duplicate_email(self, client):
        await client.post("/api/v1/auth/register", json=VALID_USER)
        resp = await client.post("/api/v1/auth/register", json=VALID_USER)
        assert resp.status_code == 409

    async def test_register_weak_password(self, client):
        resp = await client.post(
            "/api/v1/auth/register",
            json={"email": "a@b.com", "password": "weak"},
        )
        assert resp.status_code == 422

    async def test_register_invalid_email(self, client):
        resp = await client.post(
            "/api/v1/auth/register",
            json={"email": "not-an-email", "password": "SecureP@ss1"},
        )
        assert resp.status_code == 422


class TestLogin:
    async def test_login_success_no_totp(self, client):
        await client.post("/api/v1/auth/register", json=VALID_USER)
        resp = await client.post("/api/v1/auth/login", json=VALID_USER)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "access_token" in data
        assert "refresh_token" in data

    async def test_login_wrong_password(self, client):
        await client.post("/api/v1/auth/register", json=VALID_USER)
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": VALID_USER["email"], "password": "WrongP@ss1"},
        )
        assert resp.status_code == 400

    async def test_login_unknown_email(self, client):
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@example.com", "password": "SecureP@ss1"},
        )
        assert resp.status_code == 400


class TestProfile:
    async def test_get_profile_authenticated(self, client):
        await client.post("/api/v1/auth/register", json=VALID_USER)
        login_resp = await client.post("/api/v1/auth/login", json=VALID_USER)
        token = login_resp.json()["data"]["access_token"]

        resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["email"] == VALID_USER["email"]

    async def test_get_profile_unauthenticated(self, client):
        resp = await client.get("/api/v1/auth/me")
        assert resp.status_code == 401


class TestTokenRefresh:
    async def test_refresh_success(self, client):
        await client.post("/api/v1/auth/register", json=VALID_USER)
        login_resp = await client.post("/api/v1/auth/login", json=VALID_USER)
        refresh_token = login_resp.json()["data"]["refresh_token"]

        resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert resp.status_code == 200
        assert "access_token" in resp.json()["data"]

    async def test_refresh_invalid_token(self, client):
        resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid.token.here"},
        )
        assert resp.status_code == 401


class TestHealthChecks:
    async def test_liveness(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200

    async def test_readiness(self, client):
        resp = await client.get("/health/ready")
        assert resp.status_code == 200