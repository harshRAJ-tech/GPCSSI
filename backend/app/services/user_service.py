# File: backend/app/services/user_service.py
"""
User provisioning service.

WHY: Account creation logic lives in one place so both the admin endpoint
and the CLI seeding script share the same validation and hashing path.
Usernames are unique; we surface a clear conflict rather than a raw DB
error.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.enums import UserRole
from app.models.user import User


class UsernameTaken(Exception):
    """Raised when creating a user whose username already exists."""


def create_user(
    db: Session,
    *,
    username: str,
    full_name: str,
    password: str,
    role: UserRole,
) -> User:
    """Create and persist a user with a hashed password."""
    existing = db.scalar(select(User).where(User.username == username))
    if existing is not None:
        raise UsernameTaken(username)

    user = User(
        username=username,
        full_name=full_name,
        hashed_password=hash_password(password),
        role=role,
    )
    db.add(user)
    db.flush()
    return user
