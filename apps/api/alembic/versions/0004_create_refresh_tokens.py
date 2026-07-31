"""create refresh_tokens table

Revision ID: 0004
Revises: 0001, 0003
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = ("0001", "0003")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.UUID(), server_default=sa.text("uuid_generate_v7()"), primary_key=True),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("session_id", sa.UUID(), sa.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.Text(), nullable=False),
        sa.Column("family", sa.String(64), nullable=False),
        sa.Column("metadata", sa.JSONB(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_index("idx_rt_token_hash", "refresh_tokens", ["token_hash"], unique=True)
    op.create_index("idx_rt_user_id", "refresh_tokens", ["user_id"], postgresql_where=sa.text("revoked_at IS NULL"))
    op.create_index(
        "idx_rt_session_id",
        "refresh_tokens",
        ["session_id"],
        postgresql_where=sa.text("revoked_at IS NULL"),
    )
    op.create_index("idx_rt_family", "refresh_tokens", ["family"])
    op.create_check_constraint("ck_rt_expires_future", "refresh_tokens", sa.text("expires_at > created_at"))


def downgrade() -> None:
    op.drop_table("refresh_tokens")