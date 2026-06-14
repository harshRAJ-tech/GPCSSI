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
from app.models.enums import AuditAction, UserRole
from app.models.user import User
from app.schemas.auth import TokenResponse, RegisterRequest
from app.services import audit
from app.services.user_service import create_user, UsernameTaken

# Import the global limiter
from app.core.rate_limit import limiter

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
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


@router.post("/register", response_model=TokenResponse)
@limiter.limit("5/minute")
def register(
    request: Request,
    payload: RegisterRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """[DEV ONLY] Register a new user and return a bearer token."""
    try:
        # Defaulting to INVESTIGATION_OFFICER for self-registered users
        user = create_user(
            db,
            username=payload.username,
            full_name=payload.full_name,
            password=payload.password,
            role=UserRole.INVESTIGATION_OFFICER
        )
        db.commit()
    except UsernameTaken:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists"
        )
        
    audit.record(
        db,
        action=AuditAction.LOGIN,
        user_id=user.id,
        target_ref="register:success",
        source_ip=request.client.host if request.client else None,
    )
    db.commit()

    return TokenResponse(access_token=create_access_token(str(user.id)))
