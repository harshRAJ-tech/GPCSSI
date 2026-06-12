# File: backend/app/api/routes/auth.py
"""
Authentication routes.

WHY: A single login endpoint issues a short-lived JWT. We return the same
generic error for 'unknown user' and 'wrong password' so an attacker
cannot enumerate valid usernames. Every login attempt is audited.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import create_access_token, verify_password
from app.models.enums import AuditAction
from app.models.user import User
from app.schemas.auth import TokenResponse
from app.services import audit

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(
    request: Request,
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Authenticate a user and return a bearer token."""
    user = db.scalar(select(User).where(User.username == form.username))

    # Generic failure for both unknown user and bad password (no enumeration).
    if user is None or not verify_password(form.password, user.hashed_password):
        audit.record(
            db,
            action=AuditAction.LOGIN,
            user_id=user.id if user else None,
            target_ref="login:failure",
            source_ip=request.client.host if request.client else None,
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled"
        )

    audit.record(
        db,
        action=AuditAction.LOGIN,
        user_id=user.id,
        target_ref="login:success",
        source_ip=request.client.host if request.client else None,
    )
    db.commit()

    return TokenResponse(access_token=create_access_token(str(user.id)))
