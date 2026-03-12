"""add chinese translation fields

Revision ID: 20260313_cn_fields
Revises: 20260313_batch
Create Date: 2026-03-13 03:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '20260313_cn_fields'
down_revision: Union[str, None] = '20260313_batch'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """添加中文翻译字段到 paper_leads 表"""
    
    # 添加 institution_cn 字段
    op.add_column(
        'paper_leads',
        sa.Column('institution_cn', sa.Text, nullable=True)
    )
    
    # 添加 address_cn 字段
    op.add_column(
        'paper_leads',
        sa.Column('address_cn', sa.Text, nullable=True)
    )


def downgrade() -> None:
    """回滚：删除中文翻译字段"""
    
    # 删除字段
    op.drop_column('paper_leads', 'address_cn')
    op.drop_column('paper_leads', 'institution_cn')
