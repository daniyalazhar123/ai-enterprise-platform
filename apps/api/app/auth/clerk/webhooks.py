from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.config import settings
from apps.api.app.models.user import User


class ClerkWebhookHandler:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def verify_signature(self, payload: bytes, headers: dict[str, str]) -> bool:
        svix_id = headers.get("svix-id", "")
        svix_timestamp = headers.get("svix-timestamp", "")
        svix_signature = headers.get("svix-signature", "")

        if not all([svix_id, svix_timestamp, svix_signature]):
            return False

        try:
            import svix
            wh = svix.Webhook(settings.CLERK_WEBHOOK_SECRET or "")
            wh.verify(payload, {"svix-id": svix_id, "svix-timestamp": svix_timestamp, "svix-signature": svix_signature})
            return True
        except Exception:
            return False

    async def handle_event(self, event_type: str, data: dict[str, Any]) -> None:
        handler_map = {
            "user.created": self._handle_user_created,
            "user.updated": self._handle_user_updated,
            "user.deleted": self._handle_user_deleted,
            "session.created": self._handle_session_created,
            "session.revoked": self._handle_session_revoked,
            "email.verified": self._handle_email_verified,
        }
        handler = handler_map.get(event_type)
        if handler:
            await handler(data)

    async def _handle_user_created(self, data: dict[str, Any]) -> None:
        clerk_id = data.get("id", "")
        email = data.get("email_addresses", [{}])[0].get("email_address", "") if data.get("email_addresses") else ""
        name = f"{data.get('first_name', '')} {data.get('last_name', '')}".strip() or email.split("@")[0]

        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if user:
            user.clerk_id = clerk_id
        else:
            user = User(
                email=email,
                password_hash=None,
                display_name=name,
                clerk_id=clerk_id,
                is_verified=True,
                is_active=True,
            )
            self.db.add(user)
        await self.db.flush()

    async def _handle_user_updated(self, data: dict[str, Any]) -> None:
        clerk_id = data.get("id", "")
        result = await self.db.execute(select(User).where(User.clerk_id == clerk_id))
        user = result.scalar_one_or_none()
        if user:
            name = f"{data.get('first_name', '')} {data.get('last_name', '')}".strip()
            if name:
                user.display_name = name
            await self.db.flush()

    async def _handle_user_deleted(self, data: dict[str, Any]) -> None:
        clerk_id = data.get("id", "")
        result = await self.db.execute(select(User).where(User.clerk_id == clerk_id))
        user = result.scalar_one_or_none()
        if user:
            user.deleted_at = datetime.now(timezone.utc)
            user.is_active = False
            user.clerk_id = f"deleted-{clerk_id}"
            await self.db.flush()

    async def _handle_session_created(self, data: dict[str, Any]) -> None:
        pass

    async def _handle_session_revoked(self, data: dict[str, Any]) -> None:
        pass

    async def _handle_email_verified(self, data: dict[str, Any]) -> None:
        clerk_id = data.get("user_id", "")
        result = await self.db.execute(select(User).where(User.clerk_id == clerk_id))
        user = result.scalar_one_or_none()
        if user:
            user.is_verified = True
            await self.db.flush()