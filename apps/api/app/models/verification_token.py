from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlmodel import Field, Relationship

from apps.api.app.db.base import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from apps.api.app.models.user import User


class VerificationToken(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    __tablename__ = "verification_tokens"

    user_id: UUID = Field(foreign_key="users.id", nullable=False)
    token_hash: str = Field(nullable=False)
    purpose: str = Field(max_length=50, nullable=False)
    expires_at: datetime = Field(nullable=False)
    used_at: datetime | None = Field(default=None, nullable=True)

    user: "User" = Relationship(back_populates="verification_tokens")