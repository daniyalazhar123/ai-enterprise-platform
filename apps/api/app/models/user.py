from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from sqlmodel import Field, Relationship

from apps.api.app.db.base import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin
from apps.api.app.models.role import UserRoleLink

if TYPE_CHECKING:
    from apps.api.app.models.audit_log import AuditLog
    from apps.api.app.models.password_history import PasswordHistory
    from apps.api.app.models.refresh_token import RefreshToken
    from apps.api.app.models.role import Role
    from apps.api.app.models.session import Session
    from apps.api.app.models.verification_token import VerificationToken


class User(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, table=True):
    __tablename__ = "users"

    email: str = Field(max_length=320, nullable=False)
    password_hash: str | None = Field(default=None, nullable=True)
    display_name: str = Field(max_length=255, nullable=False)
    avatar_url: str | None = Field(default=None, nullable=True)
    is_verified: bool = Field(default=False, nullable=False)
    is_active: bool = Field(default=True, nullable=False)
    is_superuser: bool = Field(default=False, nullable=False)
    locale: str = Field(default="en", max_length=10, nullable=False)
    clerk_id: str | None = Field(default=None, max_length=255, nullable=True)
    last_login_at: datetime | None = Field(default=None, nullable=True)
    failed_login_attempts: int = Field(default=0, nullable=False)
    locked_until: datetime | None = Field(default=None, nullable=True)

    sessions: List[Session] = Relationship(back_populates="user")
    refresh_tokens: List[RefreshToken] = Relationship(back_populates="user")
    roles: List[Role] = Relationship(back_populates="users", link_model=UserRoleLink)
    audit_logs: List[AuditLog] = Relationship(back_populates="user")
    password_history: List[PasswordHistory] = Relationship(back_populates="user")
    verification_tokens: List[VerificationToken] = Relationship(back_populates="user")