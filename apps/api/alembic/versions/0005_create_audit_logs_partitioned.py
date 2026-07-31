"""create partitioned audit_logs table

Revision ID: 0005
Revises: 0001, 0003
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = ("0001", "0003")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE audit_logs (
            id          UUID NOT NULL DEFAULT uuid_generate_v7(),
            user_id     UUID NOT NULL REFERENCES users(id) ON DELETE SET NULL,
            session_id  UUID REFERENCES sessions(id) ON DELETE SET NULL,
            event_type  VARCHAR(50) NOT NULL,
            resource    VARCHAR(255) NOT NULL,
            resource_id VARCHAR(255),
            action      VARCHAR(100) NOT NULL,
            actor_ip    INET NOT NULL,
            actor_ua    TEXT NOT NULL,
            metadata    JSONB NOT NULL DEFAULT '{}',
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (id, created_at)
        ) PARTITION BY RANGE (created_at);
        """
    )

    op.execute(
        """
        CREATE TABLE audit_logs_2026_07 PARTITION OF audit_logs
        FOR VALUES FROM ('2026-07-01') TO ('2026-08-01');
        """
    )

    op.execute(
        """
        CREATE TABLE audit_logs_default PARTITION OF audit_logs DEFAULT;
        """
    )

    op.create_index("idx_audit_created", "audit_logs", [sa.text("created_at DESC")])
    op.create_index("idx_audit_user", "audit_logs", ["user_id", sa.text("created_at DESC")])
    op.create_index("idx_audit_event", "audit_logs", ["event_type", sa.text("created_at DESC")])
    op.create_index("idx_audit_resource", "audit_logs", ["resource", "resource_id"])


def downgrade() -> None:
    op.drop_table("audit_logs")