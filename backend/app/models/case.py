# File: backend/app/models/case.py
"""
Case model.

WHY: A case is the top-level investigation container. Every piece of
evidence and every audit entry traces back to a case, which is the
foundation of traceability in an investigation tool.
"""
from datetime import datetime

from sqlalchemy import String, Text, Enum as SAEnum, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import RiskLevel


class Case(Base):
    __tablename__ = "cases"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Risk level is nullable until the scoring engine evaluates the case.
    risk_level: Mapped[RiskLevel | None] = mapped_column(
        SAEnum(RiskLevel, name="risk_level"), nullable=True
    )

    # Who opened the case. Restrict deletion of users that own cases.
    created_by: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Convenience relationship to access a case's evidence.
    evidence: Mapped[list["Evidence"]] = relationship(  # noqa: F821
        back_populates="case", cascade="all, delete-orphan"
    )
