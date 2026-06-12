# File: backend/app/schemas/entity.py
"""Entity request/response schemas."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import EntityType


class ExtractRequest(BaseModel):
    # Bound the input size to prevent unbounded regex work on huge payloads.
    text: str = Field(min_length=1, max_length=200_000)


class EntityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    entity_type: EntityType
    raw_value: str
    normalized_value: str
    first_seen_at: datetime
