# File: backend/app/api/routes/evidence.py
"""
Evidence upload routes.

WHY: This endpoint ties together authentication, secure storage, the
database record, and the audit trail. The flow is:

  authenticated user -> case must exist -> store file securely ->
  persist Evidence row (with sha256) -> write audit entry -> respond.

All DB work shares one transaction so a failure leaves no partial state.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.case import Case
from app.models.enums import AuditAction
from app.models.evidence import Evidence
from app.models.user import User
from app.schemas.evidence import EvidenceResponse
from app.services import audit
from app.services.evidence_storage import (
    FileTooLarge,
    UnsupportedFileType,
    store_upload,
)

router = APIRouter(prefix="/cases", tags=["evidence"])


@router.post(
    "/{case_id}/evidence",
    response_model=EvidenceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_evidence(
    case_id: int,
    request: Request,
    file: UploadFile,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Evidence:
    """Upload a file as evidence attached to an existing case."""
    case = db.get(Case, case_id)
    if case is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Case not found"
        )

    try:
        stored = await store_upload(file)
    except UnsupportedFileType:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported file type",
        )
    except FileTooLarge:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File exceeds maximum allowed size",
        )

    evidence = Evidence(
        case_id=case_id,
        original_filename=file.filename or "unnamed",
        stored_path=stored.stored_path,
        content_type=file.content_type or "application/octet-stream",
        size_bytes=stored.size_bytes,
        sha256=stored.sha256,
        uploaded_by=current_user.id,
    )
    db.add(evidence)
    db.flush()  # assigns evidence.id within the same transaction

    audit.record(
        db,
        action=AuditAction.UPLOAD_EVIDENCE,
        user_id=current_user.id,
        target_ref=f"evidence:{evidence.id}",
        source_ip=request.client.host if request.client else None,
    )

    db.commit()
    db.refresh(evidence)
    return evidence
