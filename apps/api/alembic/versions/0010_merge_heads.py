"""merge all branches into single head

Revision ID: 0010
Revises: 0004, 0005, 0006, 0007, 0008, 0009
"""

from collections.abc import Sequence

revision: str = "0010"
down_revision: str | Sequence[str] | None = ("0004", "0005", "0006", "0007", "0008", "0009")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
