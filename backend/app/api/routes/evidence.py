# File: backend/app/api/routes/evidence.py
"""
Evidence upload routes.

WHY: This endpoint ties together authentication, secure storage, the
database record, and the audit trail. The flow is:

  authenticated user -> case must exist -> store file securely ->
  persist Evidence row (with sha256) -> write audit entry -> respond.

All DB work shares one transaction so a failure leaves no partial state.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.case import Case
from app.models.enums import AuditAction
from app.models.evidence import Evidence
from app.models.user import User
from app.schemas.evidence import (
    EvidenceResponse,
    EvidenceDetailResponse,
    ExtractedTextUpdate,
)
from app.services import audit
from app.services.evidence_storage import (
    FileTooLarge,
    UnsupportedFileType,
    store_upload,
)

logger = logging.getLogger(__name__)

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

    # Trigger OCR and text extraction, then extract and link entities
    try:
        from app.services import ocr as ocr_service
        from app.services import entity_service

        logger.info(
            "Extracting text from evidence %d (type: %s, path: %s)",
            evidence.id,
            evidence.content_type,
            evidence.stored_path,
        )
        extracted_text = ocr_service.extract_text_from_evidence(
            evidence.content_type, evidence.stored_path
        )
        evidence.extracted_text = extracted_text

        if extracted_text.strip():
            logger.info("Extracting and storing entities from evidence %d...", evidence.id)
            entity_service.extract_and_store(
                db, text=extracted_text, case_id=case_id, evidence_id=evidence.id
            )
        else:
            logger.info("No text extracted from evidence %d.", evidence.id)
    except Exception as e:
        # Robust handling: log OCR/extraction failure but DO NOT fail the file upload.
        # This keeps the upload itself fully working if external deep-learning libs crash.
        logger.exception("Text/OCR extraction failed for evidence %d: %s", evidence.id, e)

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


@router.get(
    "/{case_id}/evidence",
    response_model=list[EvidenceDetailResponse],
    status_code=status.HTTP_200_OK,
)
def list_case_evidence(
    case_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all evidence attached to a case, including extracted text and linked entities."""
    from sqlalchemy import select
    from app.models.entity_occurrence import EntityOccurrence
    from app.models.entity import Entity

    case = db.get(Case, case_id)
    if case is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Case not found"
        )

    # Note: RBAC/authorization for viewing cases should apply here in a full implementation.
    
    evidence_list = db.scalars(
        select(Evidence).where(Evidence.case_id == case_id).order_by(Evidence.uploaded_at.desc())
    ).all()

    results = []
    for ev in evidence_list:
        # Fetch entities linked specifically to this evidence file
        linked_entities = []
        stmt = (
            select(Entity, EntityOccurrence.mention_count)
            .join(EntityOccurrence, Entity.id == EntityOccurrence.entity_id)
            .where(EntityOccurrence.evidence_id == ev.id)
        )
        for entity, mention_count in db.execute(stmt):
            linked_entities.append(
                {
                    "entity_id": entity.id,
                    "entity_type": entity.entity_type,
                    "normalized_value": entity.normalized_value,
                    "raw_value": entity.raw_value,
                    "mention_count": mention_count,
                }
            )
            
        ev_dict = ev.__dict__.copy()
        ev_dict["linked_entities"] = linked_entities
        results.append(ev_dict)

    audit.record(
        db,
        action=AuditAction.VIEW_CASE,
        user_id=current_user.id,
        target_ref=f"case:{case_id}",
        source_ip=request.client.host if request.client else None,
    )
    # Don't need to commit since it's just a flush for audit log, but safe to do
    db.commit()

    return results


@router.put(
    "/{case_id}/evidence/{evidence_id}/extracted-text",
    response_model=EvidenceDetailResponse,
    status_code=status.HTTP_200_OK,
)
def update_evidence_extracted_text(
    case_id: int,
    evidence_id: int,
    payload: ExtractedTextUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update the extracted text for an evidence file (e.g., manual OCR correction).
    This will clear previous entity links for this file and re-extract them.
    """
    from sqlalchemy import select
    from app.models.entity_occurrence import EntityOccurrence
    from app.models.entity import Entity
    from app.services import entity_service

    evidence = db.get(Evidence, evidence_id)
    if evidence is None or evidence.case_id != case_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found"
        )

    # Update text
    evidence.extracted_text = payload.extracted_text

    # Re-extract entities
    logger.info("Re-extracting entities for evidence %d after manual text edit", evidence.id)
    entity_service.re_extract_for_evidence(
        db, text=payload.extracted_text, case_id=case_id, evidence_id=evidence_id
    )

    # Log action
    audit.record(
        db,
        action=AuditAction.EDIT_EVIDENCE_TEXT,
        user_id=current_user.id,
        target_ref=f"evidence:{evidence.id}",
        source_ip=request.client.host if request.client else None,
    )

    db.commit()
    db.refresh(evidence)

    # Build response with new entities
    linked_entities = []
    stmt = (
        select(Entity, EntityOccurrence.mention_count)
        .join(EntityOccurrence, Entity.id == EntityOccurrence.entity_id)
        .where(EntityOccurrence.evidence_id == evidence.id)
    )
    for entity, mention_count in db.execute(stmt):
        linked_entities.append(
            {
                "entity_id": entity.id,
                "entity_type": entity.entity_type,
                "normalized_value": entity.normalized_value,
                "raw_value": entity.raw_value,
                "mention_count": mention_count,
            }
        )

    ev_dict = evidence.__dict__.copy()
    ev_dict["linked_entities"] = linked_entities
    return ev_dict
