# File: backend/app/api/rbac.py
"""
Role-based access control (RBAC).

WHY: Authentication answers 'who are you'; authorization answers 'are you
allowed to do this'. `require_role` is a dependency factory: it returns a
dependency that first resolves the authenticated user, then checks their
role against an allowlist, raising 403 if not permitted. This keeps the
check declarative at each endpoint and impossible to forget silently.
"""
from collections.abc import Callable

from fastapi import Depends, HTTPException, status

from app.api.deps import get_current_user
from app.models.enums import UserRole
from app.models.user import User


def require_role(*allowed: UserRole) -> Callable[..., User]:
    """Return a dependency that allows only the given roles."""
    allowed_set = set(allowed)

    def _checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_set:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient role for this action",
            )
        return current_user

    return _checker
