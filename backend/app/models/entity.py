# File: backend/app/models/entity.py
"""
Entity model.

WHY: An entity is an investigative artifact (a UPI ID, phone number,
account, wallet, etc.). The KEY design decision: an entity is unique on
(entity_type, normalized_value). So the same UPI seen in 10 complaints is
ONE row that many cases point to. That single fact is what makes
correlation possible -- 'have we seen this before' becomes a lookup on a
unique, normalized value rather than a fuzzy text search.

We keep BOTH the raw value (as first seen) and the normalized value (used
for matching), so the investigator can still see the original form.
"""
from datetime import datetime

from sqlalchemy import String, Enum as SAEnum, DateTime, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.enums import EntityType


class Entity(Base):
    __tablename__ = "entities"
    __table_args__ = (
        # Enforces the 'one entity per normalized value' rule at the DB level.
        UniqueConstraint(
            "entity_type", "normalized_value", name="uq_entity_type_value"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    entity_type: Mapped[EntityType] = mapped_column(
        SAEnum(EntityType, name="entity_type"), nullable=False
    )

    # The value as originally extracted (e.g. '+91-9876543210').
    raw_value: Mapped[str] = mapped_column(String(512), nullable=False)

    # The canonical form used for matching (e.g. '9876543210').
    normalized_value: Mapped[str] = mapped_column(
        String(512), index=True, nullable=False
    )

    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
