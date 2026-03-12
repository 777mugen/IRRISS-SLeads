"""add batch processing fields to raw_markdown

Revision ID: 20260313_batch
Revises: refactor_data_source
Create Date: 2026-03-13 00:45:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '20260313_batch'
down_revision: Union[str, None] = 'refactor_data_source'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """添加批量处理相关字段到 raw_markdown 表"""
    
    # 添加 processing_status 字段
    op.add_column(
        'raw_markdown',
        sa.Column('processing_status', sa.String(20), server_default='pending', nullable=False)
    )
    
    # 添加 batch_id 字段
    op.add_column(
        'raw_markdown',
        sa.Column('batch_id', sa.Text, nullable=True)
    )
    
    # 添加 processed_at 字段
    op.add_column(
        'raw_markdown',
        sa.Column('processed_at', sa.DateTime, nullable=True)
    )
    
    # 添加 error_message 字段
    op.add_column(
        'raw_markdown',
        sa.Column('error_message', sa.Text, nullable=True)
    )
    
    # 创建索引
    op.create_index('idx_raw_markdown_processing_status', 'raw_markdown', ['processing_status'])
    op.create_index('idx_raw_markdown_batch_id', 'raw_markdown', ['batch_id'])


def downgrade() -> None:
    """回滚：删除批量处理相关字段"""
    
    # 删除索引
    op.drop_index('idx_raw_markdown_batch_id', table_name='raw_markdown')
    op.drop_index('idx_raw_markdown_processing_status', table_name='raw_markdown')
    
    # 删除字段
    op.drop_column('raw_markdown', 'error_message')
    op.drop_column('raw_markdown', 'processed_at')
    op.drop_column('raw_markdown', 'batch_id')
    op.drop_column('raw_markdown', 'processing_status')
