from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.models.audit_log import AuditLog


class AuditLogger:
    @staticmethod
    async def log(
        db: AsyncSession,
        user_id: UUID,
        event_type: str,
        resource: str,
        action: str,
        actor_ip: str = "",
        actor_ua: str = "",
        session_id: UUID | None = None,
        resource_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        log_entry = AuditLog(
            user_id=user_id,
            session_id=session_id,
            event_type=event_type,
            resource=resource,
            resource_id=resource_id,
            action=action,
            actor_ip=actor_ip,
            actor_ua=actor_ua,
            metadata=metadata or {},
            created_at=datetime.now(timezone.utc),
        )
        db.add(log_entry)

    @staticmethod
    async def log_event(
        db: AsyncSession,
        user_id: UUID,
        event_type: str,
        resource: str,
        resource_id: str | None,
        action: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        await AuditLogger.log(
            db=db,
            user_id=user_id,
            event_type=event_type,
            resource=resource,
            resource_id=resource_id,
            action=action,
            metadata=details,
        )