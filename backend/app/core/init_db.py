# File: backend/app/core/init_db.py
"""
Schema bootstrap.

WHY: For the prototype we use SQLAlchemy's `create_all` to build the
schema directly from the ORM models (Alembic migrations will be added
once the schema stabilizes). Importing `app.models` first guarantees
every model is registered on `Base.metadata`, so no table is skipped.

`create_all` is idempotent: it only creates tables that do not yet
exist, so it is safe to call on every startup.
"""
from app.core.database import Base, engine

# Importing the models package registers all tables on Base.metadata.
import app.models  # noqa: F401


def init_db() -> None:
    """Create all tables that do not already exist."""
    Base.metadata.create_all(bind=engine)
