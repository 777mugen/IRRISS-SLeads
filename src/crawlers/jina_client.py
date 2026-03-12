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
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "text/event-stream",
        }
        self._client = httpx.AsyncClient(
            timeout=60.0,
            follow_redirects=True,
        )
    
    async def close(self):
        """关闭客户端"""
        await self._client.aclose()
    
    async def search(self, query: str, count: int = 10) -> list[str]:
        """
        使用 Jina Search API 搜索关键词
        
        Args:
            query: 搜索关键词
            count: 返回结果数量
            
        Returns:
            URL 列表
        """
        url = f"{self.SEARCH_URL}/{query}"
        params = {"count": count}
        
        response = await self._client.get(
            url, 
            headers=self.headers, 
            params=params
        )
        response.raise_for_status()
        
        # 解析响应，提取 URL
        # Jina Search 返回格式需要解析
        urls = []
        for line in response.text.strip().split("\n"):
            if line.startswith("data: "):
                # 解析 SSE 格式
                pass  # TODO: 实现解析逻辑
        
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
        
        # 使用 Accept: text/plain 获取纯文本而非 SSE
        headers = {**self.headers, "Accept": "text/plain"}
        
        response = await self._client.get(
            reader_url, 
            headers=headers
        )
        response.raise_for_status()
        
        # 如果返回 SSE 格式，解析它
        text = response.text
        if text.startswith("event:") or text.startswith("data:"):
            return self._parse_sse(text)
        
        return text
    
    def _parse_sse(self, sse_text: str) -> str:
        """解析 SSE 格式响应"""
        lines = sse_text.strip().split("\n")
        content_parts = []
        
        for line in lines:
            if line.startswith("data:"):
                import json
                try:
                    data_str = line[5:].strip()
                    if data_str:
                        data = json.loads(data_str)
                        if "content" in data:
                            content_parts.append(data["content"])
                        elif "text" in data:
                            content_parts.append(data["text"])
                except:
                    pass
        
        return "\n".join(content_parts) if content_parts else sse_text
    
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
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
