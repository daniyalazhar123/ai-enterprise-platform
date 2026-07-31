"""
AI-specific error handling middleware.

Converts AI exceptions into structured JSON error responses
with proper HTTP status codes and logging.
"""

from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse
from structlog import get_logger

from apps.api.app.core.exceptions import (
    AiProviderError,
    ContextLengthExceededError,
    DocumentProcessingError,
    EmbeddingError,
    VectorStoreError,
)

logger = get_logger()


ERROR_STATUS_MAP: dict[type[Exception], int] = {
    AiProviderError: 502,
    EmbeddingError: 502,
    VectorStoreError: 503,
    DocumentProcessingError: 400,
    ContextLengthExceededError: 413,
}


async def ai_error_handler(request: Request, exc: Exception) -> JSONResponse:
    status_code = ERROR_STATUS_MAP.get(type(exc), 500)
    detail = str(exc)

    await logger.aerror(
        "ai_error",
        error=detail,
        error_type=type(exc).__name__,
        path=str(request.url.path),
        status_code=status_code,
    )

    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "type": type(exc).__name__,
                "message": detail,
                "status_code": status_code,
            }
        },
    )


AI_ERROR_HANDLERS: list[tuple[type[Exception], Any]] = [
    (AiProviderError, ai_error_handler),
    (EmbeddingError, ai_error_handler),
    (VectorStoreError, ai_error_handler),
    (DocumentProcessingError, ai_error_handler),
    (ContextLengthExceededError, ai_error_handler),
]