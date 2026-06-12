# File: backend/app/services/entity_service.py
"""
Entity persistence + correlation primitive.

WHY: This service turns extracted text into persisted, de-duplicated
entities. `get_or_create` honors the (entity_type, normalized_value)
unique constraint, so the same UPI seen across many cases becomes ONE
row. That collapse is exactly what makes correlation possible.

`extract_and_store` is the orchestration used by the API: extract ->
normalize -> upsert, returning the resulting Entity rows.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entity import Entity
from app.models.enums import EntityType
from app.services import extraction, normalization


def get_or_create(
    db: Session, *, entity_type: EntityType, raw_value: str
) -> tuple[Entity, bool]:
    """
    Return (entity, created). Looks up by normalized value; inserts if new.

    The unique constraint is the source of truth; this lookup-then-insert
    is the common path. A concurrent insert would raise IntegrityError,
    which the caller's transaction handling surfaces -- acceptable for the
    prototype's single-writer ingestion.
    """
    normalized = normalization.normalize(entity_type, raw_value)

    existing = db.scalar(
        select(Entity).where(
            Entity.entity_type == entity_type,
            Entity.normalized_value == normalized,
        )
    )
    if existing is not None:
        return existing, False

    entity = Entity(
        entity_type=entity_type,
        raw_value=raw_value,
        normalized_value=normalized,
    )
    db.add(entity)
    db.flush()
    return entity, True


def extract_and_store(db: Session, *, text: str) -> list[Entity]:
    """Extract entities from text and upsert them. Returns unique entities."""
    seen: set[tuple[EntityType, str]] = set()
    entities: list[Entity] = []

    for extracted in extraction.extract(text):
        normalized = normalization.normalize(extracted.entity_type, extracted.raw_value)
        key = (extracted.entity_type, normalized)
        if key in seen:
            continue
        seen.add(key)

        entity, _created = get_or_create(
            db, entity_type=extracted.entity_type, raw_value=extracted.raw_value
        )
        entities.append(entity)

    return entities
