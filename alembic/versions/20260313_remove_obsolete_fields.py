"""remove obsolete fields

Revision ID: 20260313_remove_obsolete
Revises: 20260313_add_batch_processing
Create Date: 2026-03-13 21:30:00

删除过时的字段：
- institution（通讯作者单位，不再需要）
- all_authors（旧版本 JSON 格式，已有 all_authors_info 替代）
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260313_remove_obsolete'
down_revision = '20260313_authors_cn'  # 修正为最新的 head
branch_labels = None
depends_on = None


def upgrade():
    """删除过时字段"""
    # 删除 institution 字段
    op.drop_column('paper_leads', 'institution')
    
    # 删除 all_authors 字段
    op.drop_column('paper_leads', 'all_authors')


def downgrade():
    """恢复字段（如果需要回退）"""
    # 恢复 institution 字段
    op.add_column('paper_leads', 
        sa.Column('institution', sa.Text, nullable=True)
    )
    
    # 恢复 all_authors 字段
    op.add_column('paper_leads',
        sa.Column('all_authors', sa.Text, nullable=True)
    )
