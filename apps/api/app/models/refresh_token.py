from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional
from uuid import UUID

from sqlalchemy import Column, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship

from apps.api.app.db.base import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from apps.api.app.models.session import Session
    from apps.api.app.models.user import User


class RefreshToken(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    __tablename__ = "refresh_tokens"

    user_id: UUID = Field(foreign_key="users.id", nullable=False)
    session_id: UUID = Field(foreign_key="sessions.id", nullable=False)
    token_hash: str = Field(nullable=False)
    family: str = Field(max_length=64, nullable=False)
    data: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column("metadata", JSONB, nullable=False, server_default=text("'{}'")),
    )
    expires_at: datetime = Field(nullable=False)
    revoked_at: datetime | None = Field(default=None, nullable=True)

    user: "User" = Relationship(back_populates="refresh_tokens")
    session: "Session" = Relationship(back_populates="refresh_tokens")