# File: backend/app/schemas/search.py
"""Search / correlation response schemas."""
from pydantic import BaseModel

from app.models.enums import EntityType


class CaseLinkOut(BaseModel):
    case_id: int
    mention_count: int


class ConnectedEntityOut(BaseModel):
    entity_id: int
    entity_type: EntityType
    normalized_value: str
    shared_case_count: int


class CorrelationOut(BaseModel):
    entity_id: int
    entity_type: EntityType
    normalized_value: str
    cases: list[CaseLinkOut]
    connected_entities: list[ConnectedEntityOut]
