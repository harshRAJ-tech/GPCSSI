# File: backend/app/models/entity_occurrence.py
"""
EntityOccurrence model.

WHY: An Entity is global (one UPI = one row), but correlation must answer
'which CASES is this entity linked to?'. This join table records the
provenance of every entity: which case (and optionally which evidence
file) it appeared in. It is the bridge that turns a global entity into
case-level intelligence.

Unique on (entity_id, case_id): an entity seen many times in one case is
ONE link, with `mention_count` tracking how often. That keeps the graph
clean while preserving signal (a UPI mentioned 30 times in a case is
stronger than one mentioned once).
"""
from datetime import datetime

from sqlalchemy import Integer, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class EntityOccurrence(Base):
    __tablename__ = "entity_occurrences"
    __table_args__ = (
        UniqueConstraint("entity_id", "case_id", name="uq_occurrence_entity_case"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    entity_id: Mapped[int] = mapped_column(
        ForeignKey("entities.id", ondelete="CASCADE"), index=True, nullable=False
    )
    case_id: Mapped[int] = mapped_column(
        ForeignKey("cases.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # Optional: the specific evidence file the entity was extracted from.
    evidence_id: Mapped[int | None] = mapped_column(
        ForeignKey("evidence.id", ondelete="SET NULL"), nullable=True
    )

    # How many times this entity was seen in this case.
    mention_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
