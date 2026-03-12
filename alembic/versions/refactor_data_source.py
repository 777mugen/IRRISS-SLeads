"""
Refactor data source and extraction layer

Revision ID: refactor_data_source
Revises: 
Create Date: 2026-03-12 21:20:00

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers, used by Alembic.
revision = 'refactor_data_source'
down_revision = '5474eda25abe'
branch_labels = None
depends_on = None


def upgrade():
    """重构数据库架构"""
    
    # ============================================================
    # Phase 1: 清空现有数据（按用户要求）
    # ============================================================
    
    # 注意：TRUNCATE 会清空所有数据，不可恢复！
    op.execute("TRUNCATE TABLE paper_leads CASCADE;")
    op.execute("TRUNCATE TABLE tender_leads CASCADE;")
    op.execute("TRUNCATE TABLE crawled_urls CASCADE;")
    
    # ============================================================
    # Phase 2: 新建 raw_markdown 表
    # ============================================================
    
    op.create_table(
        'raw_markdown',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('doi', sa.String(), unique=True, nullable=False),
        sa.Column('pmid', sa.String(), nullable=True),
        sa.Column('markdown_content', sa.Text(), nullable=False),
        sa.Column('source_url', sa.String(), nullable=False),
        sa.Column('fetched_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )
    
    # 创建索引
    op.create_index('idx_raw_markdown_doi', 'raw_markdown', ['doi'])
    op.create_index('idx_raw_markdown_pmid', 'raw_markdown', ['pmid'])
    
    # ============================================================
    # Phase 3: 修改 paper_leads 表
    # ============================================================
    
    # 移除 keywords_matched 字段
    op.drop_column('paper_leads', 'keywords_matched')
    
    # 新增字段
    op.add_column('paper_leads', sa.Column('source', sa.String(50), server_default='PubMed'))
    op.add_column('paper_leads', sa.Column('article_url', sa.String(), nullable=True))
    
    # 添加 DOI 唯一约束
    op.create_unique_constraint('unique_doi', 'paper_leads', ['doi'])
    
    # 创建索引
    op.create_index('idx_paper_leads_source', 'paper_leads', ['source'])
    
    # ============================================================
    # Phase 4: 新建 feedback 表
    # ============================================================
    
    op.create_table(
        'feedback',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('paper_lead_id', sa.Integer(), sa.ForeignKey('paper_leads.id', ondelete='CASCADE')),
        sa.Column('accuracy', sa.String(10), nullable=True),
        sa.Column('demand_match', sa.String(10), nullable=True),
        sa.Column('contact_validity', sa.String(10), nullable=True),
        sa.Column('deal_speed', sa.String(10), nullable=True),
        sa.Column('deal_price', sa.String(10), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # 创建索引
    op.create_index('idx_feedback_paper_lead_id', 'feedback', ['paper_lead_id'])


def downgrade():
    """回滚数据库架构"""
    
    # 删除 feedback 表
    op.drop_index('idx_feedback_paper_lead_id', 'feedback')
    op.drop_table('feedback')
    
    # 恢复 paper_leads 表
    op.drop_index('idx_paper_leads_source', 'paper_leads')
    op.drop_constraint('unique_doi', 'paper_leads', type_='unique')
    op.drop_column('paper_leads', 'article_url')
    op.drop_column('paper_leads', 'source')
    op.add_column('paper_leads', sa.Column('keywords_matched', sa.ARRAY(sa.Text()), nullable=True))
    
    # 删除 raw_markdown 表
    op.drop_index('idx_raw_markdown_pmid', 'raw_markdown')
    op.drop_index('idx_raw_markdown_doi', 'raw_markdown')
    op.drop_table('raw_markdown')
    
    # 注意：TRUNCATE 的数据无法恢复！
