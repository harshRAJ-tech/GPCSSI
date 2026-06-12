# File: backend/app/models/user.py
"""
User model.

WHY: We store only a bcrypt password *hash*, never the plaintext. The
`role` column drives RBAC. `is_active` lets an admin disable an account
without deleting its audit history (you must never lose the trail of who
did what, even after they leave).
"""
from datetime import datetime

from sqlalchemy import String, Boolean, Enum as SAEnum, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.enums import UserRole


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(128), nullable=False)

    # Stores ONLY the bcrypt hash. Never the password itself.
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, name="user_role"), nullable=False
    )

    # Disable instead of delete, to preserve audit history integrity.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
