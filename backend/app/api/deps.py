# File: backend/app/api/deps.py
"""
Shared API dependencies (authentication, current user).

WHY: Centralizing 'who is the caller' means every protected endpoint
resolves the user the same way. Endpoints depend on `get_current_user`;
if the token is missing/invalid/expired, or the user is inactive, the
request is rejected with 401 before any business logic runs.
"""
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User

# tokenUrl points clients at the login endpoint for the OpenAPI docs.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

_CREDENTIALS_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Resolve and validate the authenticated user from the bearer token."""
    try:
        subject = decode_access_token(token)
        user_id = int(subject)
    except (jwt.PyJWTError, ValueError):
        # Do not leak which part failed; a generic 401 is safer.
        raise _CREDENTIALS_ERROR

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise _CREDENTIALS_ERROR
    return user
