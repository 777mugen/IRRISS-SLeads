"""add all_authors_info field

Revision ID: 20260313_add_authors_info
Revises: 20260313_remove_obsolete
Create Date: 2026-03-13 21:33:00

添加 all_authors_info 字段（英文版本）
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260313_add_authors_info'
down_revision = '20260313_remove_obsolete'
branch_labels = None
depends_on = None


def upgrade():
    """添加 all_authors_info 字段"""
    op.add_column(
        'paper_leads',
        sa.Column('all_authors_info', sa.Text, nullable=True)
    )


def downgrade():
    """回滚：删除 all_authors_info 字段"""
    op.drop_column('paper_leads', 'all_authors_info')
