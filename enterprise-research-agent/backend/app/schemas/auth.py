from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"email": "an.nguyen@example.com", "password": "S3cure-pass"}]
        }
    )


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"email": "an.nguyen@example.com", "password": "S3cure-pass"}]
        }
    )


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"  # noqa: S105 - OAuth2 token type, not a secret
    expires_in: int = Field(description="Seconds until the token expires")

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "access_token": "eyJhbGciOiJIUzI1NiJ9...",
                    "token_type": "bearer",
                    "expires_in": 3600,
                }
            ]
        }
    )


class UserOut(BaseModel):
    id: uuid.UUID
    email: EmailStr

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"id": "0b6c2a52-8f3e-4c1d-9a7b-2e5f6d8c9a10", "email": "an.nguyen@example.com"}
            ]
        }
    )
