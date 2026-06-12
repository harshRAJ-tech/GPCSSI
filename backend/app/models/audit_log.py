# File: backend/app/models/audit_log.py
"""
Audit log model.

WHY: For a law-enforcement tool, 'who looked at what, and when' is a core
feature, not an add-on. This table is APPEND-ONLY at the application
layer: the service code only ever inserts rows, never updates or deletes
them.

LIMITATION (flagged honestly): true immutability must be enforced at the
database level (a restricted role with INSERT-only privileges, plus a
trigger blocking UPDATE/DELETE). That is a hardening follow-up tracked
separately; app-level append-only is the starting point, not the end
state.

We deliberately do NOT store sensitive payloads here -- only the action,
the acting user, the target reference, and minimal metadata -- so the
audit log itself never becomes a place that leaks PII.
"""
from datetime import datetime

from sqlalchemy import String, Enum as SAEnum, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.enums import AuditAction


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Nullable so a failed-login attempt (unknown user) can still be logged.
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True, nullable=True
    )

    action: Mapped[AuditAction] = mapped_column(
        SAEnum(AuditAction, name="audit_action"), nullable=False
    )

    # Free-form reference to the target, e.g. 'case:42' or 'entity:1337'.
    target_ref: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # Source IP, for traceability. Never store request bodies / PII here.
    source_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True, nullable=False
    )
