from __future__ import annotations

from typing import Any


class AppException(Exception):
    def __init__(
        self,
        message: str,
        status_code: int = 400,
        error_code: str = "UNKNOWN_ERROR",
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class AuthenticationError(AppException):
    def __init__(self, message: str = "Authentication failed", details: dict[str, Any] | None = None) -> None:
        super().__init__(
            message=message,
            status_code=401,
            error_code="AUTHENTICATION_ERROR",
            details=details,
        )


class AuthorizationError(AppException):
    def __init__(self, message: str = "Insufficient permissions", details: dict[str, Any] | None = None) -> None:
        super().__init__(
            message=message,
            status_code=403,
            error_code="AUTHORIZATION_ERROR",
            details=details,
        )


class NotFoundError(AppException):
    def __init__(self, message: str = "Resource not found", details: dict[str, Any] | None = None) -> None:
        super().__init__(
            message=message,
            status_code=404,
            error_code="NOT_FOUND",
            details=details,
        )


class ConflictError(AppException):
    def __init__(self, message: str = "Resource already exists", details: dict[str, Any] | None = None) -> None:
        super().__init__(
            message=message,
            status_code=409,
            error_code="CONFLICT",
            details=details,
        )


class ValidationError(AppException):
    def __init__(self, message: str = "Validation failed", details: dict[str, Any] | None = None) -> None:
        super().__init__(
            message=message,
            status_code=422,
            error_code="VALIDATION_ERROR",
            details=details,
        )


class RateLimitError(AppException):
    def __init__(self, message: str = "Rate limit exceeded", details: dict[str, Any] | None = None) -> None:
        super().__init__(
            message=message,
            status_code=429,
            error_code="RATE_LIMIT_EXCEEDED",
            details=details,
        )


class TokenExpiredError(AuthenticationError):
    def __init__(self, message: str = "Token has expired", details: dict[str, Any] | None = None) -> None:
        super().__init__(message=message, details=details)
        self.error_code = "TOKEN_EXPIRED"


class TokenRevokedError(AuthenticationError):
    def __init__(self, message: str = "Token has been revoked", details: dict[str, Any] | None = None) -> None:
        super().__init__(message=message, details=details)
        self.error_code = "TOKEN_REVOKED"


class AccountLockedError(AuthenticationError):
    def __init__(self, message: str = "Account is temporarily locked", details: dict[str, Any] | None = None) -> None:
        super().__init__(message=message, details=details)
        self.error_code = "ACCOUNT_LOCKED"


class AccountDeactivatedError(AuthenticationError):
    def __init__(self, message: str = "Account is deactivated", details: dict[str, Any] | None = None) -> None:
        super().__init__(message=message, details=details)
        self.error_code = "ACCOUNT_DEACTIVATED"


class SessionLimitError(AppException):
    def __init__(self, message: str = "Maximum active sessions reached", details: dict[str, Any] | None = None) -> None:
        super().__init__(
            message=message,
            status_code=429,
            error_code="SESSION_LIMIT_REACHED",
            details=details,
        )


class TheftDetectedError(AuthenticationError):
    def __init__(self, message: str = "Refresh token theft detected", details: dict[str, Any] | None = None) -> None:
        super().__init__(message=message, details=details)
        self.error_code = "THEFT_DETECTED"


class AiProviderError(AppException):
    def __init__(self, message: str = "AI provider error", details: dict[str, Any] | None = None) -> None:
        super().__init__(message=message, status_code=502, error_code="AI_PROVIDER_ERROR", details=details)


class AiRateLimitError(AppException):
    def __init__(self, message: str = "AI rate limit exceeded", details: dict[str, Any] | None = None) -> None:
        super().__init__(message=message, status_code=429, error_code="AI_RATE_LIMIT", details=details)


class EmbeddingError(AppException):
    def __init__(self, message: str = "Embedding generation failed", details: dict[str, Any] | None = None) -> None:
        super().__init__(message=message, status_code=502, error_code="EMBEDDING_ERROR", details=details)


class VectorStoreError(AppException):
    def __init__(self, message: str = "Vector store error", details: dict[str, Any] | None = None) -> None:
        super().__init__(message=message, status_code=502, error_code="VECTOR_STORE_ERROR", details=details)


class DocumentProcessingError(AppException):
    def __init__(self, message: str = "Document processing failed", details: dict[str, Any] | None = None) -> None:
        super().__init__(message=message, status_code=422, error_code="DOCUMENT_PROCESSING_ERROR", details=details)


class ContextLengthExceededError(AppException):
    def __init__(self, message: str = "Context length exceeded", details: dict[str, Any] | None = None) -> None:
        super().__init__(message=message, status_code=413, error_code="CONTEXT_LENGTH_EXCEEDED", details=details)