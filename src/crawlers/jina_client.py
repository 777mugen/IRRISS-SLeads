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
    
    async def search(self, query: str, max_results: int = 10, site: str = None) -> list[str]:
        """
        使用 Jina Search API 搜索
        
        Args:
            query: 搜索查询
            max_results: 最大结果数
            site: 限制站点（如 "pubmed.ncbi.nlm.nih.gov"）
            
        Returns:
            URL 列表
        """
        import re
        import json
        
        search_url = f"{self.SEARCH_URL}/"
        
        # 构建请求体
        payload = {
            "q": query,
            "num": max_results
        }
        
        # 设置请求头
        headers = {
            **self.headers,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # 如果指定了站点，添加 X-Site header
        if site:
            headers["X-Site"] = site
        
        response = await self._client.post(
            search_url, 
            headers=headers,
            json=payload
        )
        
        if response.status_code != 200:
            # 如果 POST 失败，回退到 GET 方式
            get_url = f"{self.SEARCH_URL}/{query}"
            get_headers = {**self.headers, "Accept": "application/json"}
            if site:
                get_headers["X-Site"] = site
            
            response = await self._client.get(get_url, headers=get_headers)
        
        content = response.text
        
        # 尝试解析 JSON 响应
        urls = []
        try:
            data = response.json()
            # 从 JSON 结构中提取 URL
            if isinstance(data, dict) and 'data' in data:
                for item in data.get('data', []):
                    if isinstance(item, dict) and 'url' in item:
                        urls.append(item['url'])
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and 'url' in item:
                        urls.append(item['url'])
        except:
            # 如果不是 JSON，从文本中提取 URL
            url_pattern = r'https?://[^\s<>"\)\]\}]+'
            for match in re.finditer(url_pattern, content):
                url = match.group(0)
                url = url.rstrip('.,;:!?)]>}')
                if url not in urls and len(url) < 500:
                    if url.count('?') <= 1 and url.count('&') <= 3:
                        urls.append(url)
                        if len(urls) >= max_results:
                            break
        
        return urls[:max_results]
    
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

    async def read_paper(self, doi_url: str) -> str:
        """
        读取学术论文 DOI 链接（优化版）

        特点:
        - 模拟浏览器减少反爬
        - 去除图片和链接
        - 利用缓存提升速度

        Args:
            doi_url: DOI 链接（如 "https://doi.org/10.1234/example"）

        Returns:
            Markdown 格式的论文内容（无图片、无链接）
        """
        reader_url = f"{self.READER_URL}/{doi_url}"

        # 针对学术论文优化的 Headers
        headers = {
            **self.headers,
            'Accept': 'text/plain',
            'X-Respond-With': 'markdown',
            'X-Respond-Timing': 'resource-idle',
            'X-Timeout': '60',
            'X-Engine': 'browser',  # 模拟浏览器，减少反爬
            'X-Cache-Tolerance': '3600',  # 1小时缓存
            'X-Remove-Selector': (
                'nav, aside, footer, .sidebar, '
                '.advertisement, .comments, '
                '.related-articles, .social-share, '
                'img, a img, figure'
            ),
            'X-Retain-Links': 'none',  # 去除链接
            'X-Retain-Images': 'none',  # 去除图片
            'X-With-Generated-Alt': 'false',
            'X-Locale': 'en-US',
            'X-Referer': 'https://doi.org/',
            'X-Token-Budget': '50000',
            'X-Robots-Txt': 'false'
        }

        response = await self._client.get(reader_url, headers=headers, timeout=65)
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
