# File: backend/app/api/routes/case_extract.py
"""
Case-scoped extraction route.

WHY: Extracting text in the context of a case records EntityOccurrence
links, which is what makes the entities searchable/correlatable later.
This is distinct from the ad-hoc /entities/extract endpoint, which does
not attach provenance.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.case import Case
from app.models.enums import AuditAction
from app.models.user import User
from app.schemas.entity import EntityResponse, ExtractRequest
from app.services import audit, entity_service

router = APIRouter(prefix="/cases", tags=["entities"])


@router.post(
    "/{case_id}/extract",
    response_model=list[EntityResponse],
    status_code=status.HTTP_201_CREATED,
)
def extract_for_case(
    case_id: int,
    payload: ExtractRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list:
    """Extract entities from text and link them to a case (provenance)."""
    case = db.get(Case, case_id)
    if case is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Case not found"
        )

    entities = entity_service.extract_and_store(
        db, text=payload.text, case_id=case_id
    )

    audit.record(
        db,
        action=AuditAction.EXTRACT_ENTITIES,
        user_id=current_user.id,
        target_ref=f"case:{case_id}",
        source_ip=request.client.host if request.client else None,
    )
    db.commit()
    return entities
