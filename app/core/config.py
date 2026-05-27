from functools import lru_cache
from pydantic import field_validator  # यह add करो
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    # ── Application ──────────────────────────────────────────────
    APP_NAME: str
    APP_VERSION: str
    ENVIRONMENT: str
    DEBUG: bool
    SECRET_KEY: str
 
    # ── Database ─────────────────────────────────────────────────
    DATABASE_URL: str
    DB_POOL_SIZE: int
    DB_MAX_OVERFLOW: int
    DB_POOL_TIMEOUT: int
    DB_ECHO: bool
 
    # ── Redis ────────────────────────────────────────────────────
    REDIS_URL: str
    REDIS_POOL_SIZE: int
 
    # ── JWT ──────────────────────────────────────────────────────
    JWT_ALGORITHM: str
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int
    JWT_SECRET_KEY: str
 
    # ── Security ─────────────────────────────────────────────────
    BCRYPT_ROUNDS: int
    MAX_LOGIN_ATTEMPTS: int
    LOCKOUT_DURATION_MINUTES: int
    TOTP_ISSUER: str
    TOTP_BACKUP_CODE_COUNT: int
 
    # ── CORS ─────────────────────────────────────────────────────
    ALLOWED_ORIGINS: list[str]
    ALLOWED_HOSTS: list[str]
 
    # ── Request ──────────────────────────────────────────────────
    MAX_REQUEST_SIZE_BYTES: int
    REQUEST_TIMEOUT_SECONDS: int

    # ── यह validator add करो ─────────────────────────────────────
    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def fix_database_url(cls, v: str) -> str:
        """Ensure async driver is used."""
        if v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        if v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql+asyncpg://", 1)
        return v
    
    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"
    

@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()