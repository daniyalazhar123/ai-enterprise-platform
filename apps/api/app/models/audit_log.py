from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional
from uuid import UUID

from sqlmodel import Field, Relationship

from apps.api.app.db.base import UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from apps.api.app.models.user import User


class AuditLog(UUIDPrimaryKeyMixin, table=True):
    __tablename__ = "audit_logs"

    user_id: UUID = Field(foreign_key="users.id", nullable=False)
    session_id: UUID | None = Field(foreign_key="sessions.id", default=None, nullable=True)
    event_type: str = Field(max_length=50, nullable=False)
    resource: str = Field(max_length=255, nullable=False)
    resource_id: str | None = Field(default=None, max_length=255, nullable=True)
    action: str = Field(max_length=100, nullable=False)
    actor_ip: str = Field(nullable=False)
    actor_ua: str = Field(nullable=False)
    metadata: dict[str, Any] = Field(default={}, nullable=False)
    created_at: datetime = Field(nullable=False)

    user: "User" = Relationship(back_populates="audit_logs")