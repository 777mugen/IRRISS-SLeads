"""
URL collectors for different modes.
URL 收集器，支持两种模式。
"""

import re
from abc import ABC, abstractmethod
from typing import Optional

from src.crawlers.jina_client import JinaClient
from src.logging_config import get_logger


class URLCollector(ABC):
    """URL 收集器基类"""
    
    def __init__(self):
        self.logger = get_logger()
        self.jina = JinaClient()
    
    async def close(self):
        """关闭客户端"""
        await self.jina.close()
    
    @abstractmethod
    async def collect(self) -> list[str]:
        """收集 URL 列表"""
        pass


class SearchCollector(URLCollector):
    """
    默认模式：通过 Jina Search 搜索关键词获取 URL
    
    使用场景：搜索特定主题的论文
    限制：100 RPM
    """
    
    def __init__(
        self,
        query: str,
        site: Optional[str] = None,
        max_results: int = 10
    ):
        super().__init__()
        self.query = query
        self.site = site
        self.max_results = max_results
    
    async def collect(self) -> list[str]:
        """
        使用 Jina Search 搜索关键词
        
        Returns:
            URL 列表
        """
        self.logger.info(f"Search 模式: 搜索 '{self.query}'")
        
        urls = await self.jina.search(
            query=self.query,
            max_results=self.max_results,
            site=self.site
        )
        
        self.logger.info(f"Search 返回 {len(urls)} 个 URL")
        return urls


class LibraryCollector(URLCollector):
    """
    特殊模式：从库页面提取 URL
    
    使用场景：从论文库、索引页面提取所有论文链接
    限制：Reader 500 RPM
    示例库：https://single-cell-papers.bioinfo-assist.com
    """
    
    # 常见的论文 URL 模式
    PAPER_URL_PATTERNS = [
        r'https://pubmed\.ncbi\.nlm\.nih\.gov/\d+/?',
        r'https://doi\.org/10\.[^\s]+',
        r'https://www\.ncbi\.nlm\.nih\.gov/pmc/articles/PMC\d+',
        r'https://\w+\.sciencedoi\.org/\S+',
        r'https://www\.\w+\.org/doi/\S+',
    ]
    
    def __init__(
        self,
        library_url: str,
        url_patterns: Optional[list[str]] = None,
        max_urls: int = 100
    ):
        super().__init__()
        self.library_url = library_url
        self.url_patterns = url_patterns or self.PAPER_URL_PATTERNS
        self.max_urls = max_urls
    
    async def collect(self) -> list[str]:
        """
        从库页面提取 URL
        
        Returns:
            URL 列表
        """
        self.logger.info(f"从库获取模式: 读取 {self.library_url}")
        
        # 读取库页面内容
        content = await self.jina.read(self.library_url)
        
        # 从内容中提取所有论文 URL
        urls = set()
        for pattern in self.url_patterns:
            for match in re.finditer(pattern, content):
                url = match.group(0).rstrip('.,;:!?)]}>')
                urls.add(url)
                
                if len(urls) >= self.max_urls:
                    break
            
            if len(urls) >= self.max_urls:
                break
        
        result = list(urls)[:self.max_urls]
        self.logger.info(f"从库中提取到 {len(result)} 个 URL")
        return result


class PubMedSearchCollector(SearchCollector):
    """PubMed 搜索收集器"""
    
    def __init__(self, keywords: list[str], max_results: int = 20):
        # 构建搜索查询
        query = " OR ".join(f'"{kw}"' for kw in keywords[:5])
        super().__init__(
            query=query,
            site="pubmed.ncbi.nlm.nih.gov",
            max_results=max_results
        )
