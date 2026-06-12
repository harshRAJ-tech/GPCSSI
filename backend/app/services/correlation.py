# File: backend/app/services/correlation.py
"""
Correlation / search service.

WHY: This is the investigative core -- 'have we seen this before?'. Given
a value (a phone, UPI, account...), it finds the canonical entity and
returns:
  - every CASE the entity is linked to (with mention counts), and
  - the CO-OCCURRING entities (other artifacts that share those cases).

The co-occurrence query is what surfaces 'this UPI is connected to that
phone and that account', the relationships an investigator cares about.

The query value is normalized through the SAME pure functions used at
ingestion, so search and storage always agree. All access is via
parameterized SQLAlchemy queries (no string-built SQL -> no SQLi).
"""
from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.entity import Entity
from app.models.entity_occurrence import EntityOccurrence
from app.models.enums import EntityType
from app.services import extraction, normalization


@dataclass
class CaseLink:
    case_id: int
    mention_count: int


@dataclass
class ConnectedEntity:
    entity_id: int
    entity_type: EntityType
    normalized_value: str
    shared_case_count: int


@dataclass
class CorrelationResult:
    entity_id: int
    entity_type: EntityType
    normalized_value: str
    cases: list[CaseLink] = field(default_factory=list)
    connected_entities: list[ConnectedEntity] = field(default_factory=list)


def _infer_type(value: str) -> EntityType | None:
    """Infer the entity type by running the value through the extractor."""
    matches = extraction.extract(value)
    return matches[0].entity_type if matches else None


def find_entity(
    db: Session, *, value: str, entity_type: EntityType | None = None
) -> Entity | None:
    """Resolve a query value to its canonical Entity, if it exists."""
    etype = entity_type or _infer_type(value)
    if etype is None:
        return None
    normalized = normalization.normalize(etype, value)
    return db.scalar(
        select(Entity).where(
            Entity.entity_type == etype,
            Entity.normalized_value == normalized,
        )
    )


def correlate(
    db: Session, *, value: str, entity_type: EntityType | None = None
) -> CorrelationResult | None:
    """Return the cases and connected entities for a queried value."""
    entity = find_entity(db, value=value, entity_type=entity_type)
    if entity is None:
        return None

    # Cases this entity is linked to, with mention counts.
    case_rows = db.execute(
        select(EntityOccurrence.case_id, EntityOccurrence.mention_count)
        .where(EntityOccurrence.entity_id == entity.id)
        .order_by(EntityOccurrence.mention_count.desc())
    ).all()
    cases = [CaseLink(case_id=cid, mention_count=mc) for cid, mc in case_rows]
    case_ids = [c.case_id for c in cases]

    connected: list[ConnectedEntity] = []
    if case_ids:
        # Other entities sharing any of those cases, ranked by how many
        # cases they share with the queried entity.
        other = EntityOccurrence
        rows = db.execute(
            select(
                Entity.id,
                Entity.entity_type,
                Entity.normalized_value,
                func.count(func.distinct(other.case_id)).label("shared"),
            )
            .join(other, other.entity_id == Entity.id)
            .where(other.case_id.in_(case_ids), Entity.id != entity.id)
            .group_by(Entity.id, Entity.entity_type, Entity.normalized_value)
            .order_by(func.count(func.distinct(other.case_id)).desc())
        ).all()
        connected = [
            ConnectedEntity(
                entity_id=eid,
                entity_type=etype,
                normalized_value=nval,
                shared_case_count=shared,
            )
            for eid, etype, nval, shared in rows
        ]

    return CorrelationResult(
        entity_id=entity.id,
        entity_type=entity.entity_type,
        normalized_value=entity.normalized_value,
        cases=cases,
        connected_entities=connected,
    )


@dataclass
class ExpansionResult:
    entity_id: int
    entity_type: EntityType
    normalized_value: str
    connected_entities: list[ConnectedEntity] = field(default_factory=list)


def _connected_entities(db: Session, entity: Entity) -> list[ConnectedEntity]:
    """Return entities co-occurring with `entity` across its cases.

    WHY extracted: this is the exact co-occurrence logic used by
    `correlate()`. Sharing it keeps a single source of truth, so search
    and graph-expansion can never drift apart. All access is via
    parameterized SQLAlchemy queries (no string-built SQL -> no SQLi).
    """
    case_ids = [
        cid
        for (cid,) in db.execute(
            select(EntityOccurrence.case_id).where(
                EntityOccurrence.entity_id == entity.id
            )
        ).all()
    ]
    if not case_ids:
        return []

    other = EntityOccurrence
    rows = db.execute(
        select(
            Entity.id,
            Entity.entity_type,
            Entity.normalized_value,
            func.count(func.distinct(other.case_id)).label("shared"),
        )
        .join(other, other.entity_id == Entity.id)
        .where(other.case_id.in_(case_ids), Entity.id != entity.id)
        .group_by(Entity.id, Entity.entity_type, Entity.normalized_value)
        .order_by(func.count(func.distinct(other.case_id)).desc())
    ).all()
    return [
        ConnectedEntity(
            entity_id=eid,
            entity_type=etype,
            normalized_value=nval,
            shared_case_count=shared,
        )
        for eid, etype, nval, shared in rows
    ]


def expand_entity(db: Session, *, entity_id: int) -> ExpansionResult | None:
    """Expand a single known entity into its connected entities.

    WHY: the Graph Explorer needs lazy, node-by-node expansion -- click a
    connected entity and load *its* neighbours. This resolves an entity
    by its primary key (not a free-text value) and returns the same
    co-occurring entities `correlate()` does, so the frontend can reuse
    one rendering path. Returns None if the id does not exist.
    """
    entity = db.get(Entity, entity_id)
    if entity is None:
        return None
    return ExpansionResult(
        entity_id=entity.id,
        entity_type=entity.entity_type,
        normalized_value=entity.normalized_value,
        connected_entities=_connected_entities(db, entity),
    )
