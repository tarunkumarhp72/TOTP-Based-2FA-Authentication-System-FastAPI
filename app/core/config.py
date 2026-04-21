from functools import lru_cache
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
    ENVIRONMENT: str  # development | staging | production
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
 
    # ── Rate Limiting ────────────────────────────────────────────
    # Note: Rate limiting is configured via decorators, not .env
    # These are kept for reference but not actively used
 
    # ── CORS ─────────────────────────────────────────────────────
    ALLOWED_ORIGINS: list[str]
    ALLOWED_HOSTS: list[str]
 
    # ── Request ──────────────────────────────────────────────────
    MAX_REQUEST_SIZE_BYTES: int
    REQUEST_TIMEOUT_SECONDS: int
    
    @property
    def is_production(self) ->bool:
        return self.ENVIRONMENT == "production"
    
@lru_cache

def get_settings() -> Settings:
    return Settings()

settings = get_settings()