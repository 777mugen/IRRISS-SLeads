"""
Database models for Sales Lead Discovery System.
销售线索发现系统数据库模型。
"""

from datetime import datetime, date
from typing import Optional, List

from sqlalchemy import (
    String, Text, Integer, Boolean, DateTime, Date, 
    ForeignKey, Index, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """SQLAlchemy declarative base"""
    pass


class CrawledURL(Base):
    """
    已抓取 URL 记录表
    用于增量控制，避免重复抓取
    """
    __tablename__ = "crawled_urls"

    url: Mapped[str] = mapped_column(Text, primary_key=True)
    source_type: Mapped[str] = mapped_column(String(20), nullable=False)  # 'paper' | 'tender'
    crawled_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # 'success' | 'failed' | 'skipped'


class PaperLead(Base):
    """
    论文线索表
    """
    __tablename__ = "paper_leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_url: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    pmid: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # PubMed ID
    doi: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # DOI 标识符
    title: Mapped[str] = mapped_column(Text, nullable=False)
    published_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    # 通讯作者信息
    name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # 通讯作者姓名
    institution: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # 通讯作者单位（英文）
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # 通讯作者地址（中文，合并单位+地址）
    email: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # 通讯作者邮箱
    phone: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # 通讯作者电话
    # 全部作者信息（JSON 格式）
    all_authors: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON 格式的全部作者信息
    keywords_matched: Mapped[Optional[List[str]]] = mapped_column(ARRAY(Text), nullable=True)
    score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    grade: Mapped[Optional[str]] = mapped_column(String(1), nullable=True)  # 'A' | 'B' | 'C' | 'D'
    feedback_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, default="未处理")
    strategy_version: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow
    )

    __table_args__ = (
        Index('ix_paper_leads_grade', 'grade'),
        Index('ix_paper_leads_feedback_status', 'feedback_status'),
        Index('ix_paper_leads_created_at', 'created_at'),
        Index('ix_paper_leads_pmid', 'pmid'),
    )


class TenderLead(Base):
    """
    招标线索表
    """
    __tablename__ = "tender_leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_url: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    announcement_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    project_name: Mapped[str] = mapped_column(Text, nullable=False)
    published_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    organization: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    email: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    org_only: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    budget_info: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    keywords_matched: Mapped[Optional[List[str]]] = mapped_column(ARRAY(Text), nullable=True)
    score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    grade: Mapped[Optional[str]] = mapped_column(String(1), nullable=True)
    feedback_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, default="未处理")
    strategy_version: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow
    )

    __table_args__ = (
        Index('ix_tender_leads_grade', 'grade'),
        Index('ix_tender_leads_feedback_status', 'feedback_status'),
        Index('ix_tender_leads_created_at', 'created_at'),
    )


class StrategyVersion(Base):
    """
    策略版本记录表
    用于策略版本管理和回退
    """
    __tablename__ = "strategy_versions"

    version: Mapped[str] = mapped_column(String(10), primary_key=True)
    config_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    change_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    changed_by: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


class RawMarkdown(Base):
    """
    原始 Markdown 存储表
    
    存储从 Jina Reader 获取的原始 Markdown 内容
    支持字段补齐时重新提取
    支持批量处理任务状态跟踪
    """
    __tablename__ = "raw_markdown"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    doi: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    pmid: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    markdown_content: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    
    # 批量处理状态跟踪
    processing_status: Mapped[str] = mapped_column(
        String(20), 
        nullable=False, 
        server_default="pending"
    )  # pending/processing/completed/failed
    batch_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    fetched_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_raw_markdown_doi', 'doi'),
        Index('idx_raw_markdown_pmid', 'pmid'),
        Index('idx_raw_markdown_processing_status', 'processing_status'),
        Index('idx_raw_markdown_batch_id', 'batch_id'),
    )


class Feedback(Base):
    """
    销售反馈表
    
    记录销售对每条线索的反馈（好/中/差）
    用于优化评分策略
    """
    __tablename__ = "feedback"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    paper_lead_id: Mapped[int] = mapped_column(Integer, ForeignKey('paper_leads.id', ondelete='CASCADE'))
    
    # 5个反馈维度（好/中/差）
    accuracy: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # 线索准确性
    demand_match: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # 需求匹配度
    contact_validity: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # 联系方式有效性
    deal_speed: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # 成交速度
    deal_price: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # 成交价格
    
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # 销售备注
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    
    __table_args__ = (
        Index('idx_feedback_paper_lead_id', 'paper_lead_id'),
    )
