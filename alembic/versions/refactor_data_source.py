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
    # Phase 1: 备份现有数据（安全措施）
    # ============================================================
    
    # 创建备份表
    op.execute("""
        CREATE TABLE paper_leads_backup_20260312 AS 
        SELECT * FROM paper_leads;
    """)
    
    op.execute("""
        CREATE TABLE tender_leads_backup_20260312 AS 
        SELECT * FROM tender_leads;
    """)
    
    op.execute("""
        CREATE TABLE crawled_urls_backup_20260312 AS 
        SELECT * FROM crawled_urls;
    """)
    
    # 清空现有数据（使用 DELETE 而不是 TRUNCATE，支持事务回滚）
    op.execute("DELETE FROM paper_leads;")
    op.execute("DELETE FROM tender_leads;")
    op.execute("DELETE FROM crawled_urls;")
    
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
    
    # 恢复备份的数据（如果需要）
    # 取消注释以下行来恢复数据：
    # op.execute("INSERT INTO paper_leads SELECT * FROM paper_leads_backup_20260312;")
    # op.execute("INSERT INTO tender_leads SELECT * FROM tender_leads_backup_20260312;")
    # op.execute("INSERT INTO crawled_urls SELECT * FROM crawled_urls_backup_20260312;")
    
    # 删除备份表（可选）
    # op.execute("DROP TABLE IF EXISTS paper_leads_backup_20260312;")
    # op.execute("DROP TABLE IF EXISTS tender_leads_backup_20260312;")
    # op.execute("DROP TABLE IF EXISTS crawled_urls_backup_20260312;")
