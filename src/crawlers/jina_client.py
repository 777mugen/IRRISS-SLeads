"""
Jina API client for web crawling and searching.
Jina API 客户端，用于网页抓取和搜索。
"""

import asyncio
from typing import Optional

import httpx

from src.config import config


class JinaClient:
    """
    Jina API 客户端
    
    使用 r.jina.ai 读取网页内容
    使用 s.jina.ai 搜索关键词
    """
    
    READER_URL = "https://r.jina.ai"
    SEARCH_URL = "https://s.jina.ai"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or config.jina_api_key
        self.headers = {}
        if self.api_key:
            self.headers["Authorization"] = f"Bearer {self.api_key}"
        self._client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)
    
    async def search(self, query: str, max_results: int = 10) -> list[str]:
        """
        使用 Jina Search API 搜索
        
        Args:
            query: 搜索查询
            max_results: 最大结果数
            
        Returns:
            URL 列表
        """
        import re
        
        search_url = f"{self.SEARCH_URL}/{query}"
        
        response = await self._client.get(
            search_url, 
            headers=self.headers
        )
        response.raise_for_status()
        
        content = response.text
        
        # 从搜索结果中提取所有 URL
        urls = []
        # 匹配 http/https URL
        url_pattern = r'https?://[^\s<>"\)\]\}]+'
        
        for match in re.finditer(url_pattern, content):
            url = match.group(0)
            # 清理 URL 尾部的标点
            url = url.rstrip('.,;:!?)]>}')
            
            # 过滤：只保留有效的 URL
            if url not in urls and len(url) < 500:
                # 过滤掉查询参数过多的 URL
                if url.count('?') <= 1 and url.count('&') <= 3:
                    urls.append(url)
                    if len(urls) >= max_results:
                        break
        
        return urls
    
    async def read(self, url: str) -> str:
        """
        使用 Jina Reader API 读取网页内容
        
        Args:
            url: 要读取的网页 URL
            
        Returns:
            网页的 Markdown 内容
        """
        reader_url = f"{self.READER_URL}/{url}"
        
        response = await self._client.get(
            reader_url, 
            headers=self.headers
        )
        response.raise_for_status()
        
        return response.text
    
    async def read_batch(self, urls: list[str]) -> dict[str, str]:
        """
        批量读取多个网页
        
        Args:
            urls: URL 列表
            
        Returns:
            {url: content} 字典
        """
        results = {}
        
        # 并发请求，限制并发数
        semaphore = asyncio.Semaphore(5)
        
        async def read_with_semaphore(url: str) -> tuple[str, str]:
            async with semaphore:
                try:
                    content = await self.read(url)
                    return url, content
                except Exception as e:
                    return url, f"Error: {str(e)}"
        
        tasks = [read_with_semaphore(url) for url in urls]
        responses = await asyncio.gather(*tasks)
        
        for url, content in responses:
            results[url] = content
        
        return results
    
    async def close(self):
        """关闭客户端"""
        if self._client:
            await self._client.aclose()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
