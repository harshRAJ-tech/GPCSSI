# File: backend/app/api/routes/entities.py
"""
Entity extraction routes.

WHY: Exposes the core capability -- turn raw text into de-duplicated
investigative entities. Authenticated and audited. The input length is
bounded by the schema to keep extraction cheap and bounded.
"""
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.enums import AuditAction
from app.models.user import User
from app.schemas.entity import EntityResponse, ExtractRequest
from app.services import audit, entity_service

router = APIRouter(prefix="/entities", tags=["entities"])


@router.post(
    "/extract",
    response_model=list[EntityResponse],
    status_code=status.HTTP_201_CREATED,
)
def extract_entities(
    payload: ExtractRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list:
    """Extract and persist entities from supplied text."""
    entities = entity_service.extract_and_store(db, text=payload.text)

    audit.record(
        db,
        action=AuditAction.EXTRACT_ENTITIES,
        user_id=current_user.id,
        target_ref=f"entities:{len(entities)}",
        source_ip=request.client.host if request.client else None,
    )
    db.commit()
    return entities
