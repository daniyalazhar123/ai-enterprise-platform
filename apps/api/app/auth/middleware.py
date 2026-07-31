from __future__ import annotations

from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from apps.api.app.models.session import Session
from apps.api.app.models.user import User


class AuthContext:
    def __init__(
        self,
        user: User | None = None,
        session: Session | None = None,
        token_payload: dict[str, Any] | None = None,
    ) -> None:
        self.user = user
        self.session = session
        self.token_payload = token_payload


class AuthContextMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        request.state.auth_context = AuthContext()
        response = await call_next(request)
        return response