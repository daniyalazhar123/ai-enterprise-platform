from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, List
from uuid import UUID

from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship

from apps.api.app.db.base import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from apps.api.app.models.refresh_token import RefreshToken
    from apps.api.app.models.user import User


class Session(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    __tablename__ = "sessions"

    user_id: UUID = Field(foreign_key="users.id", nullable=False)
    token_hash: str = Field(nullable=False)
    ip_address: str = Field(nullable=False)
    user_agent: str = Field(nullable=False)
    device_info: dict[str, Any] = Field(default={}, nullable=False, sa_type=JSONB)
    is_active: bool = Field(default=True, nullable=False)
    expires_at: datetime = Field(nullable=False)
    last_used_at: datetime = Field(nullable=False)

    user: "User" = Relationship(back_populates="sessions")
    refresh_tokens: List[RefreshToken] = Relationship(back_populates="session")