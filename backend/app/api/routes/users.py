# File: backend/app/api/routes/users.py
"""
User administration routes.

WHY: This is an investigation tool, so there is NO open self-registration.
Only a SYSTEM_ADMIN may provision accounts. The endpoint is guarded by
RBAC, and every creation is audited. The response never includes the
password or its hash.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.rbac import require_role
from app.core.database import get_db
from app.models.enums import AuditAction, UserRole
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse
from app.services import audit
from app.services.user_service import UsernameTaken, create_user

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user_endpoint(
    payload: UserCreate,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.SYSTEM_ADMIN)),
) -> User:
    """Provision a new user account. SYSTEM_ADMIN only."""
    try:
        user = create_user(
            db,
            username=payload.username,
            full_name=payload.full_name,
            password=payload.password,
            role=payload.role,
        )
    except UsernameTaken:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Username already exists"
        )

    audit.record(
        db,
        action=AuditAction.CREATE_CASE,  # placeholder until a CREATE_USER action exists
        user_id=admin.id,
        target_ref=f"user:{user.id}",
        source_ip=request.client.host if request.client else None,
    )
    db.commit()
    db.refresh(user)
    return user
