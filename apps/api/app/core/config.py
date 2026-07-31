from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from typing import Literal

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── General ──────────────────────────────────────────────────────────
    APP_NAME: str = "AI Enterprises"
    DEBUG: bool = False
    ENVIRONMENT: Literal["local", "review", "staging", "production"] = "local"
    API_PREFIX: str = "/api/v1"
    ROOT_DIR: Path = Path(__file__).resolve().parent.parent.parent

    # ── PostgreSQL (Neon) ────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/ai_enterprises"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10
    DATABASE_POOL_RECYCLE: int = 1800
    DATABASE_ECHO: bool = False

    @computed_field
    @property
    def database_url_sync(self) -> str:
        return self.DATABASE_URL.replace("+asyncpg", "")

    # ── Redis ────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_CACHE_TTL: int = 300

    # ── JWT ──────────────────────────────────────────────────────────────
    JWT_ALGORITHM: str = "RS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    JWT_ISSUER: str = "https://auth.ai-enterprises.com"
    JWT_AUDIENCE: str = "ai-enterprises-api"
    JWT_PRIVATE_KEY_PATH: str = ".secrets/jwt_private.pem"
    JWT_PUBLIC_KEY_PATH: str = ".secrets/jwt_public.pem"
    JWT_PRIVATE_KEY_ENCRYPTION_KEY: str | None = None
    JWT_KID: str = ""

    # ── Refresh Token ────────────────────────────────────────────────────
    REFRESH_TOKEN_BYTES: int = 32
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    MAX_ACTIVE_SESSIONS: int = 10
    SESSION_SLIDING_WINDOW_HOURS: int = 24
    SESSION_MAX_EXTENDED_DAYS: int = 7

    # ── Argon2 ──────────────────────────────────────────────────────────
    ARGON2_TIME_COST: int = 3
    ARGON2_MEMORY_COST: int = 65536  # 64 MB
    ARGON2_PARALLELISM: int = 4
    ARGON2_HASH_LENGTH: int = 32
    ARGON2_SALT_LENGTH: int = 16

    # ── Password Policy ──────────────────────────────────────────────────
    PASSWORD_MIN_LENGTH: int = 12
    PASSWORD_MAX_LENGTH: int = 128
    PASSWORD_REQUIRE_UPPER: bool = True
    PASSWORD_REQUIRE_LOWER: bool = True
    PASSWORD_REQUIRE_DIGIT: bool = True
    PASSWORD_REQUIRE_SPECIAL: bool = True
    PASSWORD_HISTORY_CHECK: int = 5
    PASSWORD_HIBP_API: str = "https://api.pwnedpasswords.com/range/"

    # ── HIBP ────────────────────────────────────────────────────────────
    HIBP_ENABLED: bool = True
    HIBP_API_KEY: str | None = None

    # ── Clerk ────────────────────────────────────────────────────────────
    CLERK_ENABLED: bool = False
    CLERK_API_KEY: str | None = None
    CLERK_FRONTEND_API: str | None = None
    CLERK_JWT_ISSUER: str | None = None
    CLERK_WEBHOOK_SECRET: str | None = None

    # ── OAuth ────────────────────────────────────────────────────────────
    GOOGLE_CLIENT_ID: str | None = None
    GOOGLE_CLIENT_SECRET: str | None = None
    GITHUB_CLIENT_ID: str | None = None
    GITHUB_CLIENT_SECRET: str | None = None

    # ── Rate Limiting ───────────────────────────────────────────────────
    RATE_LIMIT_DEFAULT: int = 100
    RATE_LIMIT_AUTH_LOGIN: int = 10
    RATE_LIMIT_AUTH_REGISTER: int = 5
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    # ── Email ────────────────────────────────────────────────────────────
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 587
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_FROM: str = "noreply@ai-enterprises.com"
    EMAIL_VERIFICATION_REQUIRED: bool = True
    EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS: int = 24
    PASSWORD_RESET_TOKEN_EXPIRE_HOURS: int = 1

    # ── Logging ──────────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: Literal["json", "console"] = "json"
    SENTRY_DSN: str | None = None

    # ── CORS ─────────────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list[str] = ["*"]
    CORS_ALLOW_HEADERS: list[str] = ["*"]

    # ── Task scheduling ─────────────────────────────────────────────────
    SESSION_CLEANUP_INTERVAL_MINUTES: int = 60
    AUDIT_ARCHIVE_INTERVAL_HOURS: int = 24

    # ── AI / LLM ────────────────────────────────────────────────────────
    OPENAI_API_KEY: str | None = None
    GEMINI_API_KEY: str | None = None
    GROK_API_KEY: str | None = None
    OPENROUTER_API_KEY: str | None = None
    COHERE_API_KEY: str | None = None

    LLM_DEFAULT_MODEL: str = "gpt-4o"
    LLM_FALLBACK_MODEL: str = "gemini-2.5-pro"
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 4096
    LLM_REQUEST_TIMEOUT: int = 60

    # ── Qdrant ───────────────────────────────────────────────────────────
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: str | None = None
    QDRANT_COLLECTION: str = "ai_enterprises_embeddings_v1"
    QDRANT_VECTOR_SIZE: int = 1024

    # ── Embeddings ──────────────────────────────────────────────────────
    EMBEDDING_MODEL: str = "embed-english-v3.0"
    EMBEDDING_BATCH_SIZE: int = 32
    EMBEDDING_MAX_INPUT_LENGTH: int = 512

    # ── Chunking ─────────────────────────────────────────────────────────
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 64
    CHUNK_MIN_SIZE: int = 50

    # ── RAG ──────────────────────────────────────────────────────────────
    RAG_TOP_K: int = 5
    RAG_SCORE_THRESHOLD: float = 0.65
    RAG_RRF_K: int = 60
    RAG_HYBRID_ALPHA: float = 0.5

    # ── Conversation ────────────────────────────────────────────────────
    CONVERSATION_TTL_HOURS: int = 24
    MAX_CONVERSATION_HISTORY: int = 50
    MEMORY_REDIS_TTL: int = 86400

    # ── Document Upload ──────────────────────────────────────────────────
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE_MB: int = 50
    ALLOWED_EXTENSIONS: list[str] = [".pdf", ".md", ".txt", ".docx"]


settings = Settings()