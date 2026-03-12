"""
Tender (招标) crawler.
招标爬虫。
"""

from datetime import datetime, timedelta
from typing import Optional

from src.crawlers.jina_client import JinaClient
from src.config import config
from src.logging_config import get_logger


class TenderCrawler:
    """
    招标爬虫
    
    使用 Jina Search 搜索招标信息
    支持多个招标平台
    """
    
    # 默认招标关键词
    DEFAULT_KEYWORDS = [
        "免疫荧光",
        "mIF",
        "病理",
        "病理诊断",
        "医学检测",
        "流式细胞",
        "质谱",
    ]
    
    # 招标平台
    TENDER_SITES = [
        "ccgp.gov.cn",           # 中国政府采购网
        "cebpubservice.com",     # 中国招标投标公共服务平台
        "bidcenter.com.cn",      # 招标中心
    ]
    
    def __init__(self, keywords: Optional[list[str]] = None):
        """
        初始化招标爬虫
        
        Args:
            keywords: 招标关键词列表
        """
        self.logger = get_logger()
        self.jina = JinaClient()
        self.keywords = keywords or config.tender_keywords or self.DEFAULT_KEYWORDS
    
    async def search_tenders(
        self, 
        days_back: int = 7,
        max_results: int = 20
    ) -> list[dict]:
        """
        搜索招标信息
        
        Args:
            days_back: 回溯天数
            max_results: 最大结果数
            
        Returns:
            招标公告列表
        """
        all_results = []
        results_per_keyword = max(1, max_results // len(self.keywords))
        
        for keyword in self.keywords:
            query = f'"{keyword}" 招标 公告'
            
            self.logger.info(f"搜索招标: {query}")
            
            urls = await self.jina.search(
                query=query,
                max_results=results_per_keyword,
                site=None  # 不限制站点
            )
            
            for url in urls:
                all_results.append({
                    'url': url,
                    'keyword': keyword,
                    'status': 'pending',
                    'content': None
                })
        
        # URL 去重
        seen = set()
        unique_results = []
        for r in all_results:
            if r['url'] not in seen:
                seen.add(r['url'])
                unique_results.append(r)
        
        self.logger.info(f"搜索到 {len(unique_results)} 条招标信息")
        return unique_results[:max_results]
    
    async def fetch_tender(self, url: str) -> dict:
        """
        获取招标详情
        
        Args:
            url: 招标公告 URL
            
        Returns:
            招标详情
        """
        try:
            content = await self.jina.read(url)
            return {
                'url': url,
                'content': content,
                'status': 'success'
            }
        except Exception as e:
            self.logger.error(f"获取招标失败 ({url}): {e}")
            return {
                'url': url,
                'content': '',
                'status': 'failed',
                'error': str(e)
            }
    
    async def run(
        self,
        days_back: int = 7,
        max_tenders: int = 20
    ) -> list[dict]:
        """
        运行招标爬虫
        
        Args:
            days_back: 回溯天数
            max_tenders: 最大数量
            
        Returns:
            招标列表（含内容）
        """
        import asyncio
        
        # 搜索
        tenders = await self.search_tenders(days_back, max_tenders)
        
        # 获取内容（并发控制）
        semaphore = asyncio.Semaphore(3)
        
        async def fetch_with_semaphore(tender: dict) -> dict:
            async with semaphore:
                result = await self.fetch_tender(tender['url'])
                tender.update(result)
                return tender
        
        tasks = [fetch_with_semaphore(t) for t in tenders]
        tenders = await asyncio.gather(*tasks)
        
        successful = [t for t in tenders if t['status'] == 'success']
        self.logger.info(f"成功获取 {len(successful)}/{len(tenders)} 条招标")
        
        return list(tenders)
    
    async def close(self):
        await self.jina.close()
