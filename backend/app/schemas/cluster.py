# File: backend/app/schemas/cluster.py
"""Cluster response schemas."""
from pydantic import BaseModel

from app.models.enums import RiskLevel


class RiskOut(BaseModel):
    score: float
    level: RiskLevel
    factors: dict[str, float]


class ClusterOut(BaseModel):
    cluster_id: int
    case_ids: list[int]
    case_count: int
    linking_entity_ids: list[int]
    risk: RiskOut
