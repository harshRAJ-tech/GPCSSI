# File: backend/app/core/security.py
"""
Password hashing and JWT token utilities.

WHY: Authentication primitives live in one audited place. We use bcrypt
(via passlib) for password hashing -- it is deliberately slow, which
resists brute-force attacks -- and short-lived signed JWTs for stateless
session tokens. The signing key comes from settings (env), never source.
"""
from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext

from app.core.config import settings

# bcrypt with passlib. 'deprecated=auto' lets us migrate schemes later.
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """Return a bcrypt hash. The plaintext is never stored anywhere."""
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Constant-time verification of a password against its stored hash."""
    return _pwd_context.verify(plain_password, hashed_password)


def create_access_token(subject: str) -> str:
    """Issue a signed JWT whose 'sub' claim is the user id (as a string)."""
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> str:
    """
    Validate a JWT and return its 'sub' claim.

    Raises jwt.PyJWTError on any problem (expired, bad signature, malformed).
    Callers translate that into an HTTP 401.
    """
    payload = jwt.decode(
        token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
    )
    subject = payload.get("sub")
    if subject is None:
        raise jwt.InvalidTokenError("Token missing 'sub' claim")
    return subject
