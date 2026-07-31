"""create sessions table

Revision ID: 0003
Revises: 0001
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sessions",
        sa.Column("id", sa.UUID(), server_default=sa.text("uuid_generate_v7()"), primary_key=True),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.Text(), nullable=False),
        sa.Column("ip_address", sa.INET(), nullable=False),
        sa.Column("user_agent", sa.Text(), nullable=False),
        sa.Column("device_info", sa.JSONB(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_index("idx_sessions_token_hash", "sessions", ["token_hash"], unique=True)
    op.create_index("idx_sessions_user_id", "sessions", ["user_id"], postgresql_where=sa.text("is_active = TRUE"))
    op.create_index("idx_sessions_expires", "sessions", ["expires_at"], postgresql_where=sa.text("is_active = TRUE"))
    op.create_check_constraint(
        "ck_sessions_expires_future",
        "sessions",
        sa.text("expires_at > created_at"),
    )


def downgrade() -> None:
    op.drop_table("sessions")