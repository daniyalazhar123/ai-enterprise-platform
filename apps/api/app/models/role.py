from __future__ import annotations

from typing import TYPE_CHECKING, List
from uuid import UUID

from sqlmodel import Field, Relationship, SQLModel

from apps.api.app.db.base import TimestampMixin, UUIDPrimaryKeyMixin
from apps.api.app.models.permission import Permission, RolePermissionLink

if TYPE_CHECKING:
    from apps.api.app.models.user import User


class UserRoleLink(SQLModel, table=True):
    __tablename__ = "user_roles"

    user_id: UUID = Field(foreign_key="users.id", primary_key=True)
    role_id: UUID = Field(foreign_key="roles.id", primary_key=True)


class Role(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    __tablename__ = "roles"

    name: str = Field(max_length=100, nullable=False)
    description: str | None = Field(default=None, nullable=True)
    is_system: bool = Field(default=False, nullable=False)

    users: List["User"] = Relationship(back_populates="roles", link_model=UserRoleLink)
    permissions: List["Permission"] = Relationship(back_populates="roles", link_model=RolePermissionLink)