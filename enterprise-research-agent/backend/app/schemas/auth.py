from __future__ import annotations

import uuid

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"  # noqa: S105 - OAuth2 token type, not a secret
    expires_in: int = Field(description="Seconds until the token expires")


class UserOut(BaseModel):
    id: uuid.UUID
    email: EmailStr
