"""
Playwright fallback client for anti-crawling scenarios.
Playwright 客户端，用于应对反爬场景。
"""

import asyncio
from typing import Optional

from src.logging_config import get_logger


class PlaywrightClient:
    """
    Playwright 客户端
    
    使用场景：Jina Reader 遇到反爬时的备选方案
    限制：较慢（约 5-10 秒/页面），但能绕过大多数反爬
    """
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self._browser = None
        self._playwright = None
        self.logger = get_logger()
    
    async def _ensure_browser(self):
        """确保浏览器已启动"""
        if self._browser is None:
            from playwright.async_api import async_playwright
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=self.headless
            )
            self.logger.info("Playwright 浏览器已启动")
    
    async def read(self, url: str, wait_selector: str = "body", timeout: int = 30000) -> str:
        """
        使用 Playwright 读取页面内容
        
        Args:
            url: 目标 URL
            wait_selector: 等待的 CSS 选择器
            timeout: 超时时间（毫秒）
            
        Returns:
            页面文本内容
        """
        await self._ensure_browser()
        
        page = await self._browser.new_page()
        try:
            # 设置合理的超时
            page.set_default_timeout(timeout)
            
            # 访问页面
            await page.goto(url, wait_until="networkidle")
            
            # 等待内容加载
            await page.wait_for_selector(wait_selector, timeout=10000)
            
            # 获取页面文本
            content = await page.inner_text("body")
            
            return content
        finally:
            await page.close()
    
    async def close(self):
        """关闭浏览器"""
        if self._browser:
            await self._browser.close()
            self._browser = None
            self.logger.info("Playwright 浏览器已关闭")
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
