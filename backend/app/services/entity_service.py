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
from app.services import extraction, normalization, graph_service
from app.core.neo4j_db import _driver as neo4j_driver


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
    entities_with_mentions: list[tuple[Entity, int]] = []
    
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
            entities_with_mentions.append((entity, mentions))

    # Trigger Neo4j graph sync if we have a valid driver
    if case_id is not None and neo4j_driver is not None and entities_with_mentions:
        try:
            with neo4j_driver.session() as session:
                graph_service.sync_entities_for_case(
                    session, case_id=case_id, entities_with_mentions=entities_with_mentions, evidence_id=evidence_id
                )
        except Exception as e:
            # We log the error but don't fail the PostgreSQL transaction
            import logging
            logging.getLogger(__name__).error("Neo4j sync failed: %s", e)

    return entities


def re_extract_for_evidence(
    db: Session,
    *,
    text: str,
    case_id: int,
    evidence_id: int,
) -> list[Entity]:
    """
    Clear existing entity links for this evidence, then re-extract from text.
    
    This is used when an investigator manually corrects OCR extraction text.
    Entities that were previously linked to this evidence but no longer appear
    in the corrected text will lose their link (by design).
    """
    from sqlalchemy import delete
    
    # 1. Clear old occurrences specifically tied to this evidence file
    stmt = delete(EntityOccurrence).where(EntityOccurrence.evidence_id == evidence_id)
    db.execute(stmt)
    db.flush()
    
    # 1.5 Remove old edges from Neo4j
    if neo4j_driver is not None:
        try:
            with neo4j_driver.session() as session:
                graph_service.remove_evidence_links(session, evidence_id=evidence_id)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error("Neo4j evidence cleanup failed: %s", e)
    
    # 2. Extract and store using the corrected text
    return extract_and_store(db, text=text, case_id=case_id, evidence_id=evidence_id)
