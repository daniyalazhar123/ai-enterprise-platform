from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from apps.api.app.core.config import settings
from apps.api.app.core.exceptions import AppException
from apps.api.app.core.logging_ import setup_logging
from apps.api.app.core.security import crypto
from apps.api.app.db.session import close_db, init_db
from apps.api.app.ai.router import ai_router
from apps.api.app.ai.error_handler import AI_ERROR_HANDLERS
from apps.api.app.api.v1.router import router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    setup_logging()
    crypto.initialize()
    await init_db()

    from apps.api.app.ai.vectorstore.qdrant_service import qdrant_service
    try:
        await qdrant_service.ensure_collection()
    except Exception:
        pass

    yield
    await close_db()


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)

from apps.api.app.auth.middleware import AuthContextMiddleware
from apps.api.app.auth.rate_limit import RateLimitMiddleware

app.add_middleware(AuthContextMiddleware)
app.add_middleware(RateLimitMiddleware)

app.include_router(router)
app.include_router(ai_router)


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.message,
            "error_code": exc.error_code,
            "details": exc.details,
        },
    )


for exc_type, handler in AI_ERROR_HANDLERS:
    app.exception_handler(exc_type)(handler)


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "error_code": "INTERNAL_ERROR",
        },
    )


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": settings.APP_NAME}


@app.get("/.well-known/jwks.json")
async def jwks_endpoint() -> dict:
    return crypto.get_jwks().model_dump()