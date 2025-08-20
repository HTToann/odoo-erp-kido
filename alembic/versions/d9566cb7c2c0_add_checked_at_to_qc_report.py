"""add checked_at to qc_report

Revision ID: d9566cb7c2c0
Revises: e3d24f52a0d4
Create Date: 2025-08-20 11:02:58.787309

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd9566cb7c2c0'
down_revision: Union[str, None] = 'e3d24f52a0d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
