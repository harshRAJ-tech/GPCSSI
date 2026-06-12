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
from app.models.entity_occurrence import EntityOccurrence
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


def _record_occurrence(
    db: Session,
    *,
    entity_id: int,
    case_id: int,
    evidence_id: int | None,
    mentions: int,
) -> None:
    """
    Link an entity to a case, or bump its mention_count if already linked.

    Honors the (entity_id, case_id) unique constraint: one link per
    entity per case, with a running count of how often it was seen.
    """
    occurrence = db.scalar(
        select(EntityOccurrence).where(
            EntityOccurrence.entity_id == entity_id,
            EntityOccurrence.case_id == case_id,
        )
    )
    if occurrence is None:
        db.add(
            EntityOccurrence(
                entity_id=entity_id,
                case_id=case_id,
                evidence_id=evidence_id,
                mention_count=mentions,
            )
        )
    else:
        occurrence.mention_count += mentions
    db.flush()


def extract_and_store(
    db: Session,
    *,
    text: str,
    case_id: int | None = None,
    evidence_id: int | None = None,
) -> list[Entity]:
    """
    Extract entities from text and upsert them. Returns unique entities.

    When `case_id` is given, each distinct entity is also linked to that
    case via an EntityOccurrence, with mention_count reflecting how many
    times it appeared in this text. That provenance is what powers
    correlation/search later.
    """
    # Count mentions per (type, normalized) so mention_count is accurate.
    counts: dict[tuple[EntityType, str], int] = {}
    raw_for_key: dict[tuple[EntityType, str], str] = {}

    for extracted in extraction.extract(text):
        normalized = normalization.normalize(extracted.entity_type, extracted.raw_value)
        key = (extracted.entity_type, normalized)
        counts[key] = counts.get(key, 0) + 1
        raw_for_key.setdefault(key, extracted.raw_value)

    entities: list[Entity] = []
    for (entity_type, _normalized), mentions in counts.items():
        entity, _created = get_or_create(
            db, entity_type=entity_type, raw_value=raw_for_key[(entity_type, _normalized)]
        )
        entities.append(entity)

        if case_id is not None:
            _record_occurrence(
                db,
                entity_id=entity.id,
                case_id=case_id,
                evidence_id=evidence_id,
                mentions=mentions,
            )

    return entities
