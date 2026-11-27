"""Unified error format (Requirement 9.5): ``{"error": {"code", "message", "request_id"}}``.

Routers keep raising ``HTTPException`` (or ``ApiError`` for a specific code); the handlers below
turn every error, including FastAPI validation errors and unknown routes, into this shape.
"""

from __future__ import annotations

import http
import logging
import uuid
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import request_id_var
from app.schemas.common import ErrorResponse

logger = logging.getLogger("app.errors")

ERROR_CODES: dict[int, str] = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    413: "payload_too_large",
    415: "unsupported_media_type",
    422: "validation_error",
    429: "rate_limited",
    500: "internal_error",
    501: "not_implemented",
    503: "service_unavailable",
}

# Example message per status, used for the OpenAPI examples only.
_EXAMPLES: dict[int, tuple[str, str]] = {
    401: ("Missing, invalid or expired token", "Not authenticated"),
    404: ("Resource does not exist or belongs to another user", "Not found"),
    409: ("Conflicts with the current state of the resource", "Conflict"),
    413: ("File larger than MAX_UPLOAD_MB (20 MB)", "File exceeds 20 MB"),
    415: ("File type is not .pdf, .docx or .md", "Unsupported file type: .xlsx"),
    422: ("Request validation failed", "Request validation failed"),
}


class ApiError(HTTPException):
    """HTTPException with an explicit error code, e.g. ``ApiError(409, "Job already finished")``."""

    def __init__(
        self,
        status_code: int,
        message: str,
        code: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(status_code=status_code, detail=message, headers=headers)
        self.code = code or ERROR_CODES.get(status_code, "error")


def error_responses(
    *statuses: int, messages: dict[int, str] | None = None
) -> dict[int | str, dict[str, Any]]:
    """OpenAPI ``responses=`` entries using ErrorResponse, with one example each.

    ``messages`` overrides the example message, e.g. ``{409: "Email already registered"}``.
    """
    out: dict[int | str, dict[str, Any]] = {}
    for status in statuses:
        description, message = _EXAMPLES[status]
        message = (messages or {}).get(status, message)
        example: dict[str, Any] = {
            "code": ERROR_CODES[status],
            "message": message,
            "request_id": "3f2b9c1e8a7d4b0c9e1f2a3b4c5d6e7f",
        }
        if status == 422:
            example["details"] = [
                {
                    "loc": ["body", "email"],
                    "msg": "value is not a valid email address",
                    "type": "value_error",
                }
            ]
        out[status] = {
            "model": ErrorResponse,
            "description": description,
            "content": {"application/json": {"example": {"error": example}}},
        }
    return out


def _error(
    request: Request,
    status: int,
    code: str,
    message: str,
    details: list[dict[str, Any]] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    request_id = request_id_var.get() or request.headers.get("X-Request-ID") or uuid.uuid4().hex
    error: dict[str, Any] = {"code": code, "message": message, "request_id": request_id}
    if details is not None:
        error["details"] = details
    response = JSONResponse({"error": error}, status_code=status, headers=headers)
    response.headers["X-Request-ID"] = request_id
    return response


async def _http_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)
    code = getattr(exc, "code", None) or ERROR_CODES.get(exc.status_code, "error")
    message = exc.detail if isinstance(exc.detail, str) else http.HTTPStatus(exc.status_code).phrase
    return _error(request, exc.status_code, code, message, headers=getattr(exc, "headers", None))


async def _validation_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    # Never echo the rejected input back: it can contain passwords.
    details = [{"loc": list(e["loc"]), "msg": e["msg"], "type": e["type"]} for e in exc.errors()]
    return _error(request, 422, "validation_error", "Request validation failed", details)


async def _unhandled_error(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled error", exc_info=exc)
    return _error(request, 500, "internal_error", "Internal server error")


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(StarletteHTTPException, _http_error)
    app.add_exception_handler(RequestValidationError, _validation_error)
    app.add_exception_handler(Exception, _unhandled_error)
