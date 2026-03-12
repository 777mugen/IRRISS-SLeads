"""
Unified content fetcher with fallback support.
统一的内容获取器，支持 fallback。
"""

from typing import Optional

from src.crawlers.jina_client import JinaClient
from src.crawlers.playwright_client import PlaywrightClient
from src.logging_config import get_logger


class ContentFetcher:
    """
    统一内容获取器
    
    优先使用 Jina Reader（快速）
    失败时自动切换到 Playwright（绕过反爬）
    """
    
    # 反爬检测指示词
    ANTI_CRAWL_INDICATORS = [
        "just a moment",
        "checking your browser",
        "please enable javascript",
        "cloudflare",
        "access denied",
        "captcha",
        "verify you are human",
        "robot check",
    ]
    
    def __init__(self, enable_playwright: bool = True, min_content_length: int = 500):
        """
        初始化内容获取器
        
        Args:
            enable_playwright: 是否启用 Playwright fallback
            min_content_length: 最小有效内容长度（小于此值视为失败）
        """
        self.logger = get_logger()
        self.jina = JinaClient()
        self.playwright = PlaywrightClient() if enable_playwright else None
        self.enable_playwright = enable_playwright
        self.min_content_length = min_content_length
        
        # 统计信息
        self._stats = {
            'total_requests': 0,
            'jina_success': 0,
            'jina_failed': 0,
            'playwright_success': 0,
            'playwright_failed': 0,
        }
    
    def _is_anti_crawl(self, content: str) -> bool:
        """检测反爬页面"""
        # 内容太短可能是反爬
        if len(content) < self.min_content_length:
            return True
        
        content_lower = content.lower()
        return any(ind in content_lower for ind in self.ANTI_CRAWL_INDICATORS)
    
    async def fetch(self, url: str) -> dict:
        """
        获取页面内容
        
        Args:
            url: 目标 URL
            
        Returns:
            {
                'url': str,
                'content': str,
                'source': 'jina' | 'playwright',
                'success': bool,
                'error': Optional[str]
            }
        """
        self._stats['total_requests'] += 1
        
        result = {
            'url': url,
            'content': '',
            'source': None,
            'success': False,
            'error': None
        }
        
        # 尝试 Jina Reader
        try:
            content = await self.jina.read(url)
            
            # 检测反爬
            if self._is_anti_crawl(content):
                raise Exception("Anti-crawl page detected")
            
            result['content'] = content
            result['source'] = 'jina'
            result['success'] = True
            self._stats['jina_success'] += 1
            return result
            
        except Exception as e:
            self.logger.warning(f"Jina Reader 失败 ({url}): {e}")
            self._stats['jina_failed'] += 1
        
        # 尝试 Playwright fallback
        if self.enable_playwright and self.playwright:
            try:
                self.logger.info(f"尝试 Playwright fallback: {url}")
                content = await self.playwright.read(url)
                
                # 再次检测反爬
                if self._is_anti_crawl(content):
                    raise Exception("Anti-crawl page still detected")
                
                result['content'] = content
                result['source'] = 'playwright'
                result['success'] = True
                self._stats['playwright_success'] += 1
                return result
                
            except Exception as e:
                result['error'] = f"Playwright failed: {str(e)}"
                self.logger.error(f"Playwright 也失败 ({url}): {e}")
                self._stats['playwright_failed'] += 1
        else:
            result['error'] = "Playwright not enabled"
        
        return result
    
    async def fetch_batch(self, urls: list[str], concurrency: int = 3) -> list[dict]:
        """
        批量获取页面内容
        
        Args:
            urls: URL 列表
            concurrency: 并发数
            
        Returns:
            结果列表
        """
        semaphore = asyncio.Semaphore(concurrency)
        
        async def fetch_with_semaphore(url: str) -> dict:
            async with semaphore:
                return await self.fetch(url)
        
        tasks = [fetch_with_semaphore(url) for url in urls]
        return await asyncio.gather(*tasks)
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            **self._stats,
            'success_rate': (
                (self._stats['jina_success'] + self._stats['playwright_success']) 
                / max(self._stats['total_requests'], 1) * 100
            )
        }
    
    async def close(self):
        """关闭所有客户端"""
        await self.jina.close()
        if self.playwright:
            await self.playwright.close()
