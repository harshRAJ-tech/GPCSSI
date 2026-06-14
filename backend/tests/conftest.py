# File: backend/tests/conftest.py
"""
Test bootstrap.

WHY: The application config is fail-closed -- it raises at import time if
DATABASE_URL / SECRET_KEY are absent. The pure unit tests
(extraction/normalization) never open a database connection, but they DO
import modules that transitively construct the Settings object. Setting
harmless placeholder env vars BEFORE any app import lets these tests run
with no .env file and no database, while leaving the fail-closed
behaviour intact for real runtime.

This must run at collection time, so it lives in conftest.py (imported by
pytest before test modules) and sets the variables at module top level.
"""
import os

# setdefault: never override a real value if one is already provided.
os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://test:test@localhost:5432/test"
)
os.environ.setdefault("SECRET_KEY", "test-secret-not-used-for-real-auth")

# Disable rate limiting during tests so we don't hit the 5/minute login cap
from main import app
app.state.limiter.enabled = False
