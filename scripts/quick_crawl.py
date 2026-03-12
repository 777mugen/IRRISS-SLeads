#!/usr/bin/env python3
"""Quick crawl and export for demo."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import config
from src.logging_config import setup_logging, get_logger
from src.crawlers.pubmed import PubMedCrawler
from src.pipeline import LeadPipeline
from src.exporters.csv_exporter import CSVExporter
from src.db.utils import get_session
from src.db.models import PaperLead
from sqlalchemy import select


async def quick_crawl_and_export():
    """Crawl a few papers and export to CSV."""
    setup_logging(log_level='INFO')
    logger = get_logger()
    
    logger.info("=" * 60)
    logger.info("快速爬取演示")
    logger.info("=" * 60)
    
    pipeline = LeadPipeline()
    exporter = CSVExporter()
    crawler = PubMedCrawler()
    
    try:
        # 1. 爬取论文
        logger.info("开始 PubMed 爬取...")
        papers = await crawler.run(days_back=30, max_papers=5)
        
        if not papers:
            logger.warning("未抓取到任何论文")
            return
        
        logger.info(f"抓取到 {len(papers)} 篇论文")
        
        # 2. 处理论文
        processed_leads = []
        for paper in papers:
            if paper['status'] == 'success':
                result = await pipeline.process_paper(
                    paper['url'],
                    paper['content']
                )
                if result:
                    processed_leads.append(result)
        
        logger.info(f"成功处理 {len(processed_leads)}/{len(papers)} 篇论文")
        
        # 3. 导出 CSV
        async with get_session() as session:
            result = await session.execute(
                select(PaperLead)
                .order_by(PaperLead.score.desc().nullslast())
                .limit(20)
            )
            all_leads = result.scalars().all()
        
        if all_leads:
            leads_data = [
                {
                    'name': l.name,
                    'institution': l.institution,
                    'email': l.email,
                    'phone': l.phone,
                    'address': l.address,
                    'title': l.title,
                    'published_at': l.published_at,
                    'grade': l.grade,
                    'keywords_matched': l.keywords_matched,
                    'source_url': l.source_url,
                }
                for l in all_leads
            ]
            
            filepath = exporter.export_paper_leads(leads_data)
            logger.info(f"CSV 导出完成: {filepath}")
            
            # 打印表格
            print("\n" + "=" * 100)
            print(f"{'姓名':<15} {'单位':<30} {'邮箱':<30} {'等级':<5} {'分数':<5}")
            print("=" * 100)
            for l in all_leads:
                name = (l.name or 'N/A')[:15]
                inst = (l.institution or 'N/A')[:30]
                email = (l.email or 'N/A')[:30]
                grade = l.grade or 'N/A'
                score = str(l.score) if l.score else 'N/A'
                print(f"{name:<15} {inst:<30} {email:<30} {grade:<5} {score:<5}")
            print("=" * 100)
            print(f"共 {len(all_leads)} 条线索")
        else:
            logger.warning("没有可导出的线索")
        
    finally:
        await pipeline.close()
        await crawler.close()


if __name__ == "__main__":
    asyncio.run(quick_crawl_and_export())
