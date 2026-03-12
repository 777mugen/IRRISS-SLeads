"""
PubMed crawler for paper lead discovery.
PubMed 论文爬虫。
"""

import asyncio
import re
from datetime import date, datetime, timedelta
from typing import Optional
from urllib.parse import quote_plus, urljoin

import httpx

from src.config import config
from src.logging_config import get_logger
from src.crawlers.jina_client import JinaClient


class PubMedCrawler:
    """
    PubMed 论文爬虫
    
    使用 Jina Search 发现论文 URL
    使用 Jina Reader 读取页面内容
    """
    
    BASE_URL = "https://pubmed.ncbi.nlm.nih.gov"
    SEARCH_URL = "https://pubmed.ncbi.nlm.nih.gov/?term={query}&filter=dates.yr[{start}-{end}]"
    
    def __init__(self):
        self.logger = get_logger()
        self.jina = JinaClient()
        self.keywords = self._load_keywords()
        self._http = httpx.AsyncClient(timeout=30.0, follow_redirects=True)
    
    def _load_keywords(self) -> list[str]:
        """加载搜索关键词"""
        kw_config = config.keywords
        keywords = []
        
        # 英文核心关键词
        english_core = kw_config.get('english', {}).get('core', [])
        keywords.extend(english_core)
        
        # 中文关键词（用于补充）
        chinese_core = kw_config.get('chinese', {}).get('core', [])
        keywords.extend(chinese_core)
        
        return keywords
    
    async def close(self):
        """关闭客户端"""
        await self.jina.close()
        await self._http.aclose()
    
    def build_search_query(self, keywords: list[str]) -> str:
        """
        构建搜索查询
        
        Args:
            keywords: 关键词列表
            
        Returns:
            URL 编码的查询字符串
        """
        # 用 OR 连接关键词
        query = " OR ".join(f'"{kw}"' for kw in keywords[:5])  # 限制前5个关键词
        return query
    
    async def search_urls(
        self, 
        query: str, 
        start_year: int = 2024,
        end_year: int | None = None,
        max_results: int = 100
    ) -> list[str]:
        """
        搜索 PubMed 论文 URL
        
        Args:
            query: 搜索查询
            start_year: 起始年份
            end_year: 结束年份（默认当前年）
            max_results: 最大结果数
            
        Returns:
            论文 URL 列表
        """
        if end_year is None:
            end_year = date.today().year
        
        search_url = self.SEARCH_URL.format(
            query=quote_plus(query),
            start=start_year,
            end=end_year
        )
        
        self.logger.info(f"搜索 PubMed: {query}")
        
        try:
            # 使用 Jina Reader 读取搜索结果页
            content = await self.jina.read(search_url)
            
            # 提取论文 URL
            urls = self._extract_pubmed_urls(content, max_results)
            
            self.logger.info(f"发现 {len(urls)} 个论文 URL")
            return urls
            
        except Exception as e:
            self.logger.error(f"搜索失败: {e}")
            return []
    
    def _extract_pubmed_urls(self, content: str, max_results: int = 100) -> list[str]:
        """
        从搜索结果页提取论文 URL
        
        Args:
            content: 页面内容 (Markdown)
            max_results: 最大结果数
            
        Returns:
            URL 列表
        """
        urls = []
        
        # 匹配 PubMed 论文链接
        # 格式: https://pubmed.ncbi.nlm.nih.gov/12345678/
        pattern = r'https://pubmed\.ncbi\.nlm\.nih\.gov/(\d+)/?'
        
        for match in re.finditer(pattern, content):
            pmid = match.group(1)
            url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
            if url not in urls:
                urls.append(url)
                if len(urls) >= max_results:
                    break
        
        return urls
    
    async def fetch_paper(self, url: str) -> dict:
        """
        获取单篇论文内容
        
        Args:
            url: 论文 URL
            
        Returns:
            论文数据字典
        """
        try:
            content = await self.jina.read(url)
            
            return {
                'url': url,
                'content': content,
                'status': 'success',
                'fetched_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"抓取论文失败 {url}: {e}")
            return {
                'url': url,
                'content': None,
                'status': 'failed',
                'error': str(e)
            }
    
    async def fetch_papers(
        self, 
        urls: list[str], 
        concurrency: int = 5
    ) -> list[dict]:
        """
        批量抓取论文
        
        Args:
            urls: URL 列表
            concurrency: 并发数
            
        Returns:
            论文数据列表
        """
        semaphore = asyncio.Semaphore(concurrency)
        
        async def fetch_with_limit(url: str) -> dict:
            async with semaphore:
                return await self.fetch_paper(url)
        
        tasks = [fetch_with_limit(url) for url in urls]
        results = await asyncio.gather(*tasks)
        
        return list(results)
    
    async def run(
        self, 
        days_back: int = 7,
        max_papers: int = 50
    ) -> list[dict]:
        """
        运行爬虫
        
        Args:
            days_back: 回溯天数
            max_papers: 最大论文数
            
        Returns:
            论文数据列表
        """
        self.logger.info(f"PubMed 爬虫启动，回溯 {days_back} 天")
        
        # 构建搜索查询
        query = self.build_search_query(self.keywords)
        
        # 搜索 URL
        urls = await self.search_urls(query, max_results=max_papers)
        
        if not urls:
            self.logger.warning("未发现任何论文 URL")
            return []
        
        # 抓取论文内容
        papers = await self.fetch_papers(urls)
        
        # 过滤失败的
        successful = [p for p in papers if p['status'] == 'success']
        
        self.logger.info(f"成功抓取 {len(successful)}/{len(papers)} 篇论文")
        
        return successful
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
