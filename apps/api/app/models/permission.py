from __future__ import annotations

from typing import TYPE_CHECKING, List
from uuid import UUID

from sqlmodel import Field, Relationship, SQLModel

from apps.api.app.db.base import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from apps.api.app.models.role import Role


class RolePermissionLink(SQLModel, table=True):
    __tablename__ = "role_permissions"

    role_id: UUID = Field(foreign_key="roles.id", primary_key=True)
    permission_id: UUID = Field(foreign_key="permissions.id", primary_key=True)


class Permission(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    __tablename__ = "permissions"

    resource: str = Field(max_length=255, nullable=False)
    action: str = Field(max_length=100, nullable=False)
    description: str | None = Field(default=None, nullable=True)
    is_system: bool = Field(default=False, nullable=False)

    roles: List[Role] = Relationship(back_populates="permissions", link_model=RolePermissionLink)