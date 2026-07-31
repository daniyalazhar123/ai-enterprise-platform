from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlmodel import Field, Relationship

from apps.api.app.db.base import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from apps.api.app.models.user import User


class PasswordHistory(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    __tablename__ = "password_history"

    user_id: UUID = Field(foreign_key="users.id", nullable=False)
    password_hash: str = Field(nullable=False)

    user: "User" = Relationship(back_populates="password_history")