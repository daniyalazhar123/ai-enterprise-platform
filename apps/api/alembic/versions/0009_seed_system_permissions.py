"""seed system permissions and assign to roles

Revision ID: 0009
Revises: 0002
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0009"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO permissions (resource, action, is_system) VALUES
            ('users', '*', TRUE),
            ('roles', '*', TRUE),
            ('permissions', '*', TRUE),
            ('audit', 'read', TRUE);
        """
    )

    op.execute(
        """
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id FROM roles r, permissions p WHERE r.name = 'superadmin';
        """
    )

    op.execute(
        """
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id FROM roles r, permissions p
        WHERE r.name = 'admin' AND p.resource = 'users';
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM role_permissions;")
    op.execute("DELETE FROM permissions WHERE is_system = TRUE;")