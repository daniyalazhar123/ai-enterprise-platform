from __future__ import annotations

from apps.api.app.core.config import settings


class ClerkClient:
    def __init__(self) -> None:
        self.enabled = settings.CLERK_ENABLED
        self.api_key = settings.CLERK_API_KEY
        self.frontend_api = settings.CLERK_FRONTEND_API
        self.jwt_issuer = settings.CLERK_JWT_ISSUER
        self._initialized = False

    async def initialize(self) -> None:
        if self.enabled and not self._initialized:
            self._initialized = True

    async def verify_session(self, session_token: str) -> dict | None:
        if not self.enabled:
            return None
        try:
            from clerk_backend import Client as ClerkSDK
            from clerk_backend.sdk import ClerkSDKError

            sdk = ClerkSDK(secret_key=self.api_key)
            user = await sdk.users.get_user(session_token=session_token)
            return user.to_dict() if user else None
        except Exception:
            return None


clerk_client = ClerkClient()