# File: backend/app/models/relationship.py
"""
Relationship model.

WHY: Correlation is relationship-driven. This table links two entities
(e.g. a UPI USED_BY a phone) or an entity to the case/evidence it came
from. In the prototype this mirrors what we will also store in Neo4j; in
PostgreSQL it gives us a reliable, queryable source of truth.

`confidence` (0.0 - 1.0) lets us distinguish a directly-observed link
from an inferred one, which matters: an investigator must know whether a
connection is fact or a hint.
"""
from datetime import datetime

from sqlalchemy import String, Float, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Relationship(Base):
    __tablename__ = "relationships"
    __table_args__ = (
        UniqueConstraint(
            "source_entity_id",
            "target_entity_id",
            "rel_type",
            name="uq_relationship_edge",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    source_entity_id: Mapped[int] = mapped_column(
        ForeignKey("entities.id", ondelete="CASCADE"), index=True, nullable=False
    )
    target_entity_id: Mapped[int] = mapped_column(
        ForeignKey("entities.id", ondelete="CASCADE"), index=True, nullable=False
    )

    # e.g. 'USES', 'OWNS', 'TRANSFERRED_TO', 'CONNECTED_TO'.
    rel_type: Mapped[str] = mapped_column(String(64), nullable=False)

    # 1.0 = directly observed; lower = inferred.
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
