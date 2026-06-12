# File: backend/app/services/audit.py
"""
Audit logging service.

WHY: A single, append-only entry point for audit records. Service code
calls `record()` only; it never updates or deletes audit rows. We store
the minimum needed for traceability and deliberately keep PII / payloads
out of the log.
"""
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.enums import AuditAction


def record(
    db: Session,
    *,
    action: AuditAction,
    user_id: int | None = None,
    target_ref: str | None = None,
    source_ip: str | None = None,
) -> None:
    """Append a single audit entry. Insert-only by design."""
    entry = AuditLog(
        action=action,
        user_id=user_id,
        target_ref=target_ref,
        source_ip=source_ip,
    )
    db.add(entry)
    # Flush (not commit) so the caller controls the surrounding transaction.
    db.flush()
