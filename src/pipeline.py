"""
Pipeline for end-to-end lead processing.
端到端线索处理管道。
"""

import asyncio
from datetime import date, datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from src.config import config
from src.db.models import CrawledURL, PaperLead, TenderLead
from src.db.utils import get_session
from src.extractors.paper_extractor import PaperExtractor
from src.extractors.tender_extractor import TenderExtractor
from src.scoring.paper_scorer import PaperScorer
from src.scoring.tender_scorer import TenderScorer
from src.processors.normalizer import normalize_lead, deduplicate_key
from src.logging_config import get_logger


class LeadPipeline:
    """线索处理管道"""
    
    def __init__(self):
        self.logger = get_logger()
        self.paper_extractor = PaperExtractor()
        self.tender_extractor = TenderExtractor()
        self.paper_scorer = PaperScorer()
        self.tender_scorer = TenderScorer()
    
    async def is_url_crawled(self, url: str, only_success: bool = False) -> bool:
        """检查 URL 是否已抓取
        
        Args:
            url: 要检查的 URL
            only_success: 如果为 True，只检查成功的记录
            
        Returns:
            bool: URL 是否已抓取
        """
        async with get_session() as session:
            result = await session.execute(
                select(CrawledURL).where(CrawledURL.url == url)
            )
            crawled = result.scalar_one_or_none()
            if crawled is None:
                return False
            if only_success:
                return crawled.status == 'success'
            return True
    
    async def mark_url_crawled(
        self, 
        url: str, 
        source_type: str, 
        status: str = 'success'
    ):
        """标记 URL 为已抓取"""
        async with get_session() as session:
            crawled = CrawledURL(
                url=url,
                source_type=source_type,
                status=status
            )
            session.add(crawled)
    
    async def process_paper(
        self, 
        url: str, 
        content: str
    ) -> Optional[dict]:
        """
        处理论文线索
        
        Args:
            url: 论文 URL
            content: 页面内容
            
        Returns:
            处理后的线索数据，如果验证失败返回 None
        """
        # 检查是否已成功抓取（允许重试失败的）
        if await self.is_url_crawled(url, only_success=True):
            self.logger.debug(f"URL 已成功抓取，跳过: {url}")
            return None
        
        # 提取字段
        extracted = await self.paper_extractor.extract(content)
        
        if extracted.get('error') or extracted.get('_validation_error'):
            self.logger.warning(f"提取失败: {url} - {extracted.get('error') or extracted.get('_validation_error')}")
            await self.mark_url_crawled(url, 'paper', 'failed')
            return None
        
        # 标准化数据
        normalized = normalize_lead(extracted, 'paper')
        normalized['source_url'] = url
        
        # 评分
        score, grade = self.paper_scorer.score_lead(normalized)
        normalized['score'] = score
        normalized['grade'] = grade
        
        # 入库
        await self.save_paper_lead(normalized)
        await self.mark_url_crawled(url, 'paper', 'success')
        
        self.logger.info(f"论文入库: {normalized.get('title', 'N/A')[:50]} - 等级 {grade}")
        
        return normalized
    
    async def save_paper_lead(self, lead: dict):
        """保存论文线索到数据库"""
        import json
        
        # 处理通讯作者信息
        corresponding = lead.get('corresponding_author') or {}
        
        # 处理全部作者信息
        all_authors = lead.get('all_authors')
        all_authors_json = json.dumps(all_authors, ensure_ascii=False) if all_authors else None
        
        async with get_session() as session:
            paper = PaperLead(
                source_url=lead['source_url'],
                pmid=lead.get('pmid'),
                doi=lead.get('doi'),
                title=lead.get('title', ''),
                published_at=lead.get('published_at'),
                # 通讯作者信息
                name=corresponding.get('name') if corresponding else lead.get('name'),
                institution=corresponding.get('institution') if corresponding else lead.get('institution'),
                address=corresponding.get('address') if corresponding else lead.get('address'),
                email=corresponding.get('email') if corresponding else lead.get('email'),
                phone=corresponding.get('phone') if corresponding else lead.get('phone'),
                # 全部作者
                all_authors=all_authors_json,
                keywords_matched=lead.get('keywords_matched', []),
                score=lead.get('score'),
                grade=lead.get('grade'),
                feedback_status='未处理',
                strategy_version='v1',
            )
            session.add(paper)
    
    async def process_tender(
        self, 
        url: str, 
        content: str
    ) -> Optional[dict]:
        """
        处理招标线索
        
        Args:
            url: 公告 URL
            content: 页面内容
            
        Returns:
            处理后的线索数据
        """
        # 检查是否已成功抓取（允许重试失败的）
        if await self.is_url_crawled(url, only_success=True):
            self.logger.debug(f"URL 已成功抓取，跳过: {url}")
            return None
        
        # 提取字段
        extracted = await self.tender_extractor.extract(content)
        
        if extracted.get('error') or extracted.get('_validation_error'):
            self.logger.warning(f"提取失败: {url}")
            await self.mark_url_crawled(url, 'tender', 'failed')
            return None
        
        # 标准化数据
        normalized = normalize_lead(extracted, 'tender')
        normalized['source_url'] = url
        
        # 评分
        score, grade = self.tender_scorer.score_lead(normalized)
        normalized['score'] = score
        normalized['grade'] = grade
        
        # 入库
        await self.save_tender_lead(normalized)
        await self.mark_url_crawled(url, 'tender', 'success')
        
        self.logger.info(f"招标入库: {normalized.get('project_name', 'N/A')[:50]} - 等级 {grade}")
        
        return normalized
    
    async def save_tender_lead(self, lead: dict):
        """保存招标线索到数据库"""
        async with get_session() as session:
            tender = TenderLead(
                source_url=lead['source_url'],
                announcement_id=lead.get('announcement_id'),
                project_name=lead.get('project_name', ''),
                published_at=lead.get('published_at'),
                organization=lead.get('organization'),
                address=lead.get('address'),
                email=lead.get('email'),
                name=lead.get('name'),
                phone=lead.get('phone'),
                org_only=lead.get('org_only', False),
                budget_info=lead.get('budget_info'),
                keywords_matched=lead.get('keywords_matched', []),
                score=lead.get('score'),
                grade=lead.get('grade'),
                feedback_status='未处理',
                strategy_version='v1',
            )
            session.add(tender)
    
    async def close(self):
        """关闭资源"""
        await self.paper_extractor.close()
        await self.tender_extractor.close()
