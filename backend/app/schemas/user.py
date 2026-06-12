# File: backend/app/schemas/user.py
"""
User schemas.

WHY: A password-strength floor is enforced at the schema boundary so a
weak credential can never reach the hashing layer. We never expose the
hashed password in any response model.
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import UserRole


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    full_name: str = Field(min_length=1, max_length=128)
    # Minimum length is a basic floor; production would add complexity rules.
    password: str = Field(min_length=12, max_length=256)
    role: UserRole


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime
