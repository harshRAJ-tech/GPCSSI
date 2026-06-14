# File: backend/app/schemas/auth.py
"""
Auth response schema.

WHY: The login request itself uses FastAPI's OAuth2PasswordRequestForm
(form fields username/password), so we only need to define the token
response shape here.
"""
from pydantic import BaseModel


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class RegisterRequest(BaseModel):
    username: str
    full_name: str
    password: str

