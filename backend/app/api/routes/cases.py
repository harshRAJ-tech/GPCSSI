# File: backend/app/api/routes/cases.py
"""
Case routes.

WHY: A case is created by an authenticated user (any role may open one in
the prototype). Creation and viewing are both audited, because in an
investigation tool 'who viewed this case' is itself evidence of activity.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.case import Case
from app.models.enums import AuditAction
from app.models.user import User
from app.schemas.case import CaseCreate, CaseResponse
from app.services import audit

router = APIRouter(prefix="/cases", tags=["cases"])


@router.get("", response_model=list[CaseResponse], status_code=status.HTTP_200_OK)
def list_cases(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Case]:
    """List all cases."""
    from sqlalchemy import select
    cases = db.scalars(select(Case).order_by(Case.created_at.desc())).all()
    return cases

@router.post("", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
def create_case(
    payload: CaseCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Case:
    """Open a new investigation case."""
    case = Case(
        title=payload.title,
        description=payload.description,
        created_by=current_user.id,
    )
    db.add(case)
    db.flush()

    audit.record(
        db,
        action=AuditAction.CREATE_CASE,
        user_id=current_user.id,
        target_ref=f"case:{case.id}",
        source_ip=request.client.host if request.client else None,
    )
    db.commit()
    db.refresh(case)
    return case


@router.get("/{case_id}", response_model=CaseResponse)
def get_case(
    case_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Case:
    """Fetch a single case by id."""
    case = db.get(Case, case_id)
    if case is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Case not found"
        )

    audit.record(
        db,
        action=AuditAction.VIEW_CASE,
        user_id=current_user.id,
        target_ref=f"case:{case.id}",
        source_ip=request.client.host if request.client else None,
    )
    db.commit()
    return case
