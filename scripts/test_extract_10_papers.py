"""
测试提取流程（小规模：10 篇论文）
"""

import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.crawlers.pubmed_entrez import PubMedEntrezClient
from src.logging_config import get_logger


async def test_extraction():
    """测试提取 10 篇论文"""
    logger = get_logger()
    
    logger.info("=" * 80)
    logger.info("测试提取 10 篇论文")
    logger.info("=" * 80)
    
    async with PubMedEntrezClient() as client:
        # 搜索 10 篇论文
        query = '"Multiplex Immunofluorescence" OR "mIF"'
        logger.info(f"搜索关键词: {query}")
        
        papers = await client.search_and_fetch(
            query=query,
            max_results=10,
            date_range=(2024, 2026)
        )
        
        logger.info(f"找到 {len(papers)} 篇论文")
        
        # 打印结果
        for i, paper in enumerate(papers[:5], 1):
            logger.info(f"\n[{i}] PMID: {paper.get('pmid')}")
            logger.info(f"    DOI: {paper.get('doi')}")
            logger.info(f"    标题: {paper.get('title', 'N/A')[:80]}")
            logger.info(f"    发表日期: {paper.get('published_at')}")
            logger.info(f"    作者数: {len(paper.get('authors', []))}")


if __name__ == "__main__":
    asyncio.run(test_extraction())
