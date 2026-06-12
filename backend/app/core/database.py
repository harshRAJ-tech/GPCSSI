# File: backend/app/core/database.py
"""
Database engine and session management.

WHY: Centralizing session creation ensures every DB session is properly
closed after each request, preventing connection-pool exhaustion. The
`get_db` generator is used as a FastAPI dependency.
"""
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session

from app.core.config import settings

# pool_pre_ping verifies a connection is alive before using it,
# avoiding errors from stale connections.
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """Base class all ORM models inherit from."""
    pass


def get_db() -> Generator[Session, None, None]:
    """Yield a DB session and guarantee it is closed afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
