# File: backend/app/schemas/case.py
"""Case request/response schemas."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import RiskLevel


class CaseCreate(BaseModel):
    # Trim + length-bound the title to avoid empty or oversized values.
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=10_000)


class CaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    risk_level: RiskLevel | None
    created_by: int
    created_at: datetime
