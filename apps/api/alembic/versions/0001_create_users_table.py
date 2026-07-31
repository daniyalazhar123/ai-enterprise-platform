"""create users table

Revision ID: 0001
Revises:
Create Date: 2026-07-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_uuidv7;")

    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), server_default=sa.text("uuid_generate_v7()"), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=True),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("avatar_url", sa.Text(), nullable=True),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
        sa.Column("is_superuser", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
        sa.Column("locale", sa.String(10), nullable=False, server_default=sa.text("'en'")),
        sa.Column("clerk_id", sa.String(255), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_login_attempts", sa.SmallInteger(), nullable=False, server_default=sa.text("0")),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_index("idx_users_email", "users", ["email"], unique=True, postgresql_where=sa.text("deleted_at IS NULL"))
    op.create_index(
        "idx_users_clerk_id",
        "users",
        ["clerk_id"],
        unique=True,
        postgresql_where=sa.text("clerk_id IS NOT NULL AND deleted_at IS NULL"),
    )
    op.create_index("idx_users_active", "users", ["is_active", "deleted_at"])
    op.create_index(
        "idx_users_locked",
        "users",
        ["locked_until"],
        postgresql_where=sa.text("locked_until IS NOT NULL"),
    )

    op.create_check_constraint(
        "ck_users_display_name_length",
        "users",
        sa.text("length(display_name) >= 2"),
    )


def downgrade() -> None:
    op.drop_table("users")