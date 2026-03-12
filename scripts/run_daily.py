#!/usr/bin/env python3
"""
Run daily lead discovery task.
运行每日线索发现任务。
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import config
from src.logging_config import setup_logging, get_logger
from src.crawlers.pubmed import PubMedCrawler
from src.pipeline import LeadPipeline


async def run_daily_task():
    """运行每日任务"""
    # 初始化日志
    setup_logging(log_level=config.log_level)
    logger = get_logger()
    
    logger.info("=" * 60)
    logger.info("销售线索发现系统 - 每日任务启动")
    logger.info("=" * 60)
    
    pipeline = LeadPipeline()
    
    try:
        # 1. PubMed 论文爬取
        logger.info("开始 PubMed 论文爬取...")
        
        async with PubMedCrawler() as crawler:
            papers = await crawler.run(days_back=7, max_papers=20)
            
            logger.info(f"抓取到 {len(papers)} 篇论文，开始处理...")
            
            processed = 0
            for paper in papers:
                result = await pipeline.process_paper(
                    paper['url'], 
                    paper['content']
                )
                if result:
                    processed += 1
            
            logger.info(f"论文处理完成: {processed}/{len(papers)} 入库成功")
        
        # 2. TODO: 招标网站爬取
        logger.info("招标网站爬取 - 待实现")
        
        logger.info("每日任务完成")
        
    except Exception as e:
        logger.error(f"任务失败: {e}", exc_info=True)
        raise
    finally:
        await pipeline.close()


def main():
    """主入口"""
    asyncio.run(run_daily_task())


if __name__ == "__main__":
    main()
