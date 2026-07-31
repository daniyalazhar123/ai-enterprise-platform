"""create verification_tokens table

Revision ID: 0006
Revises: 0001
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "verification_tokens",
        sa.Column("id", sa.UUID(), server_default=sa.text("uuid_generate_v7()"), primary_key=True),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.Text(), nullable=False),
        sa.Column("purpose", sa.String(50), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_index("idx_vt_token_hash", "verification_tokens", ["token_hash"], unique=True)
    op.create_index("idx_vt_user_purpose", "verification_tokens", ["user_id", "purpose"])
    op.create_check_constraint(
        "ck_vt_purpose",
        "verification_tokens",
        sa.text("purpose IN ('email_verification', 'password_reset')"),
    )


def downgrade() -> None:
    op.drop_table("verification_tokens")