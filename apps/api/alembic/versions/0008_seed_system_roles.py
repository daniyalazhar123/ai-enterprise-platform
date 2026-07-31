"""seed system roles

Revision ID: 0008
Revises: 0002
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0008"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO roles (name, description, is_system) VALUES
            ('superadmin', 'Full system access', TRUE),
            ('admin', 'Administrative operations', TRUE),
            ('editor', 'Content creation and modification', TRUE),
            ('viewer', 'Read-only access', TRUE);
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM roles WHERE is_system = TRUE;")