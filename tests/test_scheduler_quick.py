#!/usr/bin/env python3
"""Quick test for scheduler - only processes 3 papers."""
import asyncio
from src.scheduler.scheduler import TaskScheduler
from src.logging_config import setup_logging

setup_logging(log_level='INFO')


async def test_daily_task_quick():
    """Quick test with limited papers"""
    print("Testing run_daily_task (quick - 3 papers max)...")
    
    # 临时修改爬虫配置
    from src.crawlers.pubmed import PubMedCrawler
    original_run = PubMedCrawler.run
    
    async def limited_run(self, days_back=7, max_papers=3):
        """Run with limited papers for quick test"""
        self.logger.info(f"PubMed 爬虫启动 (快速测试), 回溯 {days_back} 天")
        
        query = self.build_search_query(self.keywords)
        urls = await self.search_urls(query, max_results=max_papers)
        
        if not urls:
            self.logger.warning("未发现任何论文 URL")
            return []
        
        papers = await self.fetch_papers(urls)
        successful = [p for p in papers if p['status'] == 'success']
        
        self.logger.info(f"成功抓取 {len(successful)}/{len(papers)} 篇论文")
        return successful
    
    PubMedCrawler.run = limited_run
    
    scheduler = TaskScheduler()
    await scheduler.run_daily_task()
    print("Daily task completed!")


async def test_full_export():
    """Test full export"""
    print("\nTesting run_full_export...")
    scheduler = TaskScheduler()
    await scheduler.run_full_export()
    print("Full export completed!")


async def main():
    print("=" * 60)
    print("Scheduler Quick Test")
    print("=" * 60)
    await test_daily_task_quick()
    await test_full_export()
    print("\n" + "=" * 60)
    print("All quick tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
