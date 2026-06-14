# File: backend/app/core/config.py
"""
Central configuration.

WHY: A law-enforcement tool must never embed secrets in source code.
All sensitive values load from environment variables. If a required
secret is absent, the app refuses to start (fail-closed), which is
safer than booting with insecure defaults.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Loaded from a .env file locally; from the environment in deployment.
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="forbid"
    )

    # Database connection (no default -> must be supplied)
    DATABASE_URL: str

    # Secret used to sign auth tokens. No default on purpose.
    SECRET_KEY: str

    # Neo4j connection
    NEO4J_URI: str
    NEO4J_USER: str
    NEO4J_PASSWORD: str

    # JWT settings.
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Where uploaded evidence is stored on disk.
    UPLOAD_DIR: str = "uploads"

    # Max upload size in bytes (default 25 MB) to prevent DoS via huge files.
    MAX_UPLOAD_BYTES: int = 25 * 1024 * 1024


# Single shared instance. Importing this will raise immediately
# if DATABASE_URL or SECRET_KEY are missing -> fail-closed.
settings = Settings()  # type: ignore[call-arg]
