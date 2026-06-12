# File: backend/app/models/__init__.py
"""
ORM models package.

WHY: Importing every model here ensures they are all registered on
`Base.metadata` before `create_all()` runs, so no table is silently
skipped at startup.
"""
from app.models.user import User
from app.models.case import Case
from app.models.evidence import Evidence
from app.models.entity import Entity
from app.models.entity_occurrence import EntityOccurrence
from app.models.relationship import Relationship
from app.models.audit_log import AuditLog

__all__ = [
    "User",
    "Case",
    "Evidence",
    "Entity",
    "EntityOccurrence",
    "Relationship",
    "AuditLog",
]
