"""Shared API schemas: unified error format and pagination (Requirement 9.5)."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ErrorBody(BaseModel):
    code: str = Field(description="Stable machine-readable code, e.g. `not_found`")
    message: str = Field(description="Human-readable message")
    request_id: str = Field(description="Same value as the `X-Request-ID` response header")
    details: list[dict[str, Any]] | None = Field(
        default=None, description="Field errors, only present for `validation_error`"
    )


class ErrorResponse(BaseModel):
    """Every non-2xx response has this shape."""

    error: ErrorBody


class Page(BaseModel, Generic[T]):
    """Envelope for every list endpoint (offset pagination)."""

    items: list[T]
    total: int = Field(description="Number of items matching the query, ignoring limit/offset")
    limit: int
    offset: int

    model_config = ConfigDict(
        json_schema_extra={"examples": [{"items": [], "total": 0, "limit": 20, "offset": 0}]}
    )
