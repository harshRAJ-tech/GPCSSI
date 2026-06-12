# File: backend/app/api/routes/search.py
"""
Search / correlation routes.

WHY: The most-used investigator action: paste a phone/UPI/account and
immediately see linked cases and connected entities. Type is inferred
from the value by default (best demo UX), with an optional explicit
override. Authenticated and audited as a SEARCH action; the audited
target_ref deliberately records only the entity type, never the searched
value itself, so the audit log does not accumulate sensitive query data.
"""
from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.enums import AuditAction, EntityType
from app.models.user import User
from app.schemas.search import CorrelationOut, EntityExpansionOut
from app.services import audit, correlation

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=CorrelationOut)
def search(
    request: Request,
    value: str = Query(min_length=1, max_length=512),
    entity_type: EntityType | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CorrelationOut:
    """Correlate a value: return linked cases and connected entities."""
    result = correlation.correlate(db, value=value, entity_type=entity_type)

    # Audit the search by type only -- never log the raw query value.
    audit.record(
        db,
        action=AuditAction.SEARCH,
        user_id=current_user.id,
        target_ref=f"type:{result.entity_type.value if result else 'unknown'}",
        source_ip=request.client.host if request.client else None,
    )
    db.commit()

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No entity found for the supplied value",
        )
    return CorrelationOut(
        entity_id=result.entity_id,
        entity_type=result.entity_type,
        normalized_value=result.normalized_value,
        cases=[c.__dict__ for c in result.cases],
        connected_entities=[c.__dict__ for c in result.connected_entities],
    )


@router.get("/expand/{entity_id}", response_model=EntityExpansionOut)
def expand(
    request: Request,
    entity_id: int = Path(ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EntityExpansionOut:
    """Expand a known entity into its connected entities (graph drill-down).

    WHY: powers lazy, node-by-node expansion in the Graph Explorer. Like
    /search, it is authenticated and audited as a SEARCH action; the
    audited target_ref records only the entity type, never any value.
    """
    result = correlation.expand_entity(db, entity_id=entity_id)

    audit.record(
        db,
        action=AuditAction.SEARCH,
        user_id=current_user.id,
        target_ref=f"expand:{result.entity_type.value if result else 'unknown'}",
        source_ip=request.client.host if request.client else None,
    )
    db.commit()

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No entity found for the supplied id",
        )
    return EntityExpansionOut(
        entity_id=result.entity_id,
        entity_type=result.entity_type,
        normalized_value=result.normalized_value,
        connected_entities=[c.__dict__ for c in result.connected_entities],
    )
