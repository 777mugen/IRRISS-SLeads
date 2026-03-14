"""merge_heads

Revision ID: 01259386b6bf
Revises: 20260313_add_authors_info, 20260314_retry
Create Date: 2026-03-15 04:06:37.862651

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '01259386b6bf'
down_revision: Union[str, Sequence[str], None] = ('20260313_add_authors_info', '20260314_retry')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
