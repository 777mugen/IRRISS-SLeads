"""add retry fields to raw_markdown

Revision ID: 20260314_retry
Revises: 20260313_batch
Create Date: 2026-03-14 23:40:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '20260314_retry'
down_revision: Union[str, None] = '20260313_batch'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """添加重试相关字段到 raw_markdown 表"""
    
    # 添加 retry_count 字段（重试次数）
    op.add_column(
        'raw_markdown',
        sa.Column('retry_count', sa.Integer, server_default='0', nullable=False)
    )
    
    # 添加 last_retry_at 字段（最后重试时间）
    op.add_column(
        'raw_markdown',
        sa.Column('last_retry_at', sa.DateTime, nullable=True)
    )
    
    # 创建索引（用于快速查询可重试的论文）
    op.create_index(
        'idx_raw_markdown_retry', 
        'raw_markdown', 
        ['processing_status', 'retry_count', 'processed_at']
    )


def downgrade() -> None:
    """回滚：删除重试相关字段"""
    
    # 删除索引
    op.drop_index('idx_raw_markdown_retry', table_name='raw_markdown')
    
    # 删除字段
    op.drop_column('raw_markdown', 'last_retry_at')
    op.drop_column('raw_markdown', 'retry_count')
