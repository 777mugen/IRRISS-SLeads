"""add all_authors_info_cn field

Revision ID: 20260313_authors_cn
Revises: 20260313_cn_fields
Create Date: 2026-03-13 07:25:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '20260313_authors_cn'
down_revision: Union[str, None] = '20260313_cn_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """添加 all_authors_info_cn 字段"""
    
    # 添加 all_authors_info_cn 字段
    op.add_column(
        'paper_leads',
        sa.Column('all_authors_info_cn', sa.Text, nullable=True)
    )


def downgrade() -> None:
    """回滚：删除 all_authors_info_cn 字段"""
    
    op.drop_column('paper_leads', 'all_authors_info_cn')
