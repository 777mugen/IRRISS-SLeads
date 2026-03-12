---
title: Playwright Fallback & URL Deduplication
type: feat
status: active
date: 2026-03-12
---

# Playwright Fallback & URL Deduplication

## Overview

增强爬虫系统的健壮性，添加 Playwright 作为反爬应对方案，并实现多模式 URL 去重机制。

## Problem Statement / Motivation

### 当前问题

1. **反爬问题**：部分网站（如 ScienceDirect DOI 链接）返回 "Just a moment..." 反爬页面，Jina Reader 无法获取内容
2. **重复问题**：模式1 (Search) 和模式2 (Library) 可能返回相同的论文 URL，导致重复处理

### 测试中发现的反爬情况

```
[2/3] 读取: https://doi.org/10.1016/j.tranon.2025.102647
  ✅ 内容长度: 1685 字符
  📄 标题: Title: Just a moment......   ← 反爬页面
```

## Proposed Solution

### 1. Playwright Fallback 机制

当 Jina Reader 失败或返回反爬页面时，自动切换到 Playwright：

```
Jina Reader 尝试
    ↓
失败/反爬检测？
    ↓ 是
Playwright Fallback
    ↓
返回内容
```

### 2. URL 去重机制

在 Pipeline 层面实现去重，确保同一 URL 只处理一次：

```
模式1 URLs ──┐
             ├──→ 去重合并 ──→ 处理
模式2 URLs ──┘
```

## Technical Approach

### Phase 1: Playwright Fallback 实现

#### 1.1 创建 Playwright 客户端

**文件**: `src/crawlers/playwright_client.py`

```python
"""
Playwright fallback client for anti-crawling scenarios.
Playwright 客户端，用于应对反爬场景。
"""

import asyncio
from typing import Optional
from playwright.async_api import async_playwright, Browser, Page

class PlaywrightClient:
    """
    Playwright 客户端
    
    使用场景：Jina Reader 遇到反爬时的备选方案
    限制：较慢（约 5-10 秒/页面），但能绕过大多数反爬
    """
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self._browser: Optional[Browser] = None
        self._playwright = None
    
    async def _ensure_browser(self):
        """确保浏览器已启动"""
        if self._browser is None:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=self.headless
            )
    
    async def read(self, url: str, wait_selector: str = "body") -> str:
        """
        使用 Playwright 读取页面内容
        
        Args:
            url: 目标 URL
            wait_selector: 等待的 CSS 选择器
            
        Returns:
            页面文本内容
        """
        await self._ensure_browser()
        
        page = await self._browser.new_page()
        try:
            # 设置合理的超时
            page.set_default_timeout(30000)
            
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
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
```

#### 1.2 修改 JinaClient 添加 Fallback

**文件**: `src/crawlers/jina_client.py`

```python
async def read_with_fallback(
    self, 
    url: str, 
    playwright_client: Optional['PlaywrightClient'] = None
) -> tuple[str, str]:
    """
    读取网页内容，支持 Playwright fallback
    
    Args:
        url: 目标 URL
        playwright_client: Playwright 客户端（可选）
        
    Returns:
        (content, source) - 内容和来源 ('jina' | 'playwright')
    """
    try:
        content = await self.read(url)
        
        # 检测反爬页面
        if self._is_anti_crawl(content):
            self.logger.warning(f"检测到反爬页面: {url}")
            raise Exception("Anti-crawl detected")
        
        return content, 'jina'
        
    except Exception as e:
        if playwright_client:
            self.logger.info(f"Jina 失败，尝试 Playwright: {url}")
            content = await playwright_client.read(url)
            return content, 'playwright'
        raise

def _is_anti_crawl(self, content: str) -> bool:
    """检测是否为反爬页面"""
    anti_crawl_indicators = [
        "Just a moment",
        "Checking your browser",
        "Please enable JavaScript",
        "Cloudflare",
        "Access denied",
    ]
    
    content_lower = content.lower()
    return any(indicator.lower() in content_lower for indicator in anti_crawl_indicators)
```

#### 1.3 创建统一的内容获取器

**文件**: `src/crawlers/content_fetcher.py`

```python
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
    
    def __init__(self, enable_playwright: bool = True):
        self.logger = get_logger()
        self.jina = JinaClient()
        self.playwright = PlaywrightClient() if enable_playwright else None
        self.enable_playwright = enable_playwright
    
    async def fetch(self, url: str) -> dict:
        """
        获取页面内容
        
        Args:
            url: 目标 URL
            
        Returns:
            {
                'content': str,
                'source': 'jina' | 'playwright',
                'success': bool,
                'error': Optional[str]
            }
        """
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
            return result
            
        except Exception as e:
            self.logger.warning(f"Jina Reader 失败 ({url}): {e}")
        
        # 尝试 Playwright fallback
        if self.enable_playwright and self.playwright:
            try:
                self.logger.info(f"尝试 Playwright fallback: {url}")
                content = await self.playwright.read(url)
                
                result['content'] = content
                result['source'] = 'playwright'
                result['success'] = True
                return result
                
            except Exception as e:
                result['error'] = f"Playwright failed: {str(e)}"
                self.logger.error(f"Playwright 也失败 ({url}): {e}")
        else:
            result['error'] = "Playwright not enabled"
        
        return result
    
    def _is_anti_crawl(self, content: str) -> bool:
        """检测反爬页面"""
        indicators = [
            "just a moment",
            "checking your browser",
            "please enable javascript",
            "cloudflare",
            "access denied",
            "captcha",
        ]
        content_lower = content.lower()
        # 内容太短可能是反爬
        if len(content) < 500:
            return True
        return any(ind in content_lower for ind in indicators)
    
    async def close(self):
        """关闭所有客户端"""
        await self.jina.close()
        if self.playwright:
            await self.playwright.close()
```

### Phase 2: URL 去重机制

#### 2.1 创建 URL 去重器

**文件**: `src/processors/url_deduplicator.py`

```python
"""
URL deduplication utilities.
URL 去重工具。
"""

import re
from typing import Optional
from urllib.parse import urlparse

class URLDeduplicator:
    """
    URL 去重器
    
    基于 URL 的规范化形式进行去重
    支持 DOI 和 PubMed URL 的等价识别
    """
    
    # PMID 提取模式
    PMID_PATTERN = re.compile(r'pubmed\.ncbi\.nlm\.nih\.gov/(\d+)')
    DOI_PATTERN = re.compile(r'doi\.org/(10\.[^\s]+)')
    
    def __init__(self):
        self._seen_urls: set[str] = set()
        self._seen_pmids: set[str] = set()
        self._seen_dois: set[str] = set()
    
    def normalize_url(self, url: str) -> str:
        """
        规范化 URL
        
        - 移除尾部斜杠
        - 统一小写域名
        - 移除常见追踪参数
        """
        url = url.strip().rstrip('/')
        parsed = urlparse(url)
        
        # 统一域名小写
        netloc = parsed.netloc.lower()
        
        # 移除常见追踪参数
        tracking_params = {'utm_source', 'utm_medium', 'utm_campaign', 'ref', 'source'}
        if parsed.query:
            params = [p for p in parsed.query.split('&') 
                     if not any(p.startswith(f"{tp}=") for tp in tracking_params)]
            query = '&'.join(params) if params else ''
        else:
            query = ''
        
        # 重建 URL
        normalized = f"{parsed.scheme}://{netloc}{parsed.path}"
        if query:
            normalized += f"?{query}"
        
        return normalized
    
    def extract_identifier(self, url: str) -> tuple[Optional[str], Optional[str]]:
        """
        从 URL 提取标识符
        
        Returns:
            (type, id) - 例如 ('pmid', '12345') 或 ('doi', '10.1234/abc')
        """
        # 尝试提取 PMID
        pmid_match = self.PMID_PATTERN.search(url)
        if pmid_match:
            return ('pmid', pmid_match.group(1))
        
        # 尝试提取 DOI
        doi_match = self.DOI_PATTERN.search(url)
        if doi_match:
            doi = doi_match.group(1).rstrip('.,;:')
            return ('doi', doi)
        
        return (None, None)
    
    def is_duplicate(self, url: str) -> bool:
        """
        检查 URL 是否重复
        
        去重逻辑：
        1. 基于 PMID 去重（同一 PMID 的不同 URL 视为相同）
        2. 基于 DOI 去重（同一 DOI 的不同 URL 视为相同）
        3. 基于规范化 URL 去重
        """
        # 提取标识符
        id_type, id_value = self.extract_identifier(url)
        
        if id_type == 'pmid' and id_value:
            if id_value in self._seen_pmids:
                return True
            self._seen_pmids.add(id_value)
        
        if id_type == 'doi' and id_value:
            if id_value in self._seen_dois:
                return True
            self._seen_dois.add(id_value)
        
        # 规范化 URL 去重
        normalized = self.normalize_url(url)
        if normalized in self._seen_urls:
            return True
        
        self._seen_urls.add(normalized)
        return False
    
    def deduplicate(self, urls: list[str]) -> list[str]:
        """
        去重 URL 列表
        
        Args:
            urls: URL 列表
            
        Returns:
            去重后的 URL 列表（保持原顺序）
        """
        seen = set()
        result = []
        
        for url in urls:
            if not self.is_duplicate(url):
                result.append(url)
        
        return result
    
    def merge_sources(
        self, 
        urls_by_source: dict[str, list[str]]
    ) -> list[dict]:
        """
        合并多个来源的 URL 并标记来源
        
        Args:
            urls_by_source: {'mode1': [urls], 'mode2': [urls]}
            
        Returns:
            [{'url': str, 'sources': ['mode1', 'mode2']}, ...]
        """
        url_sources: dict[str, list[str]] = {}
        
        for source, urls in urls_by_source.items():
            for url in urls:
                normalized = self.normalize_url(url)
                if normalized not in url_sources:
                    url_sources[normalized] = []
                if source not in url_sources[normalized]:
                    url_sources[normalized].append(source)
        
        return [
            {'url': url, 'sources': sources}
            for url, sources in url_sources.items()
        ]
    
    def reset(self):
        """重置去重状态"""
        self._seen_urls.clear()
        self._seen_pmids.clear()
        self._seen_dois.clear()
```

#### 2.2 集成到收集器

**文件**: `src/crawlers/collectors.py` (修改)

```python
from src.processors.url_deduplicator import URLDeduplicator

class MultiModeCollector:
    """
    多模式收集器
    
    同时运行多种收集模式，自动去重合并结果
    """
    
    def __init__(
        self,
        keywords: list[str],
        library_url: Optional[str] = None,
        max_results_per_mode: int = 50
    ):
        self.keywords = keywords
        self.library_url = library_url
        self.max_results = max_results_per_mode
        self.deduplicator = URLDeduplicator()
        self.logger = get_logger()
    
    async def collect_all(self) -> list[dict]:
        """
        运行所有收集模式并合并去重
        
        Returns:
            [{'url': str, 'sources': ['search', 'library']}, ...]
        """
        urls_by_source = {}
        
        # 模式1: Search
        try:
            search_collector = PubMedSearchCollector(
                self.keywords, 
                max_results=self.max_results
            )
            urls_by_source['search'] = await search_collector.collect()
            await search_collector.close()
        except Exception as e:
            self.logger.error(f"Search 模式失败: {e}")
            urls_by_source['search'] = []
        
        # 模式2: Library
        if self.library_url:
            try:
                library_collector = SingleCellPapersCollector(
                    keyword=self.keywords[0] if self.keywords else None,
                    max_urls=self.max_results
                )
                urls_by_source['library'] = await library_collector.collect()
                await library_collector.close()
            except Exception as e:
                self.logger.error(f"Library 模式失败: {e}")
                urls_by_source['library'] = []
        
        # 合并去重
        merged = self.deduplicator.merge_sources(urls_by_source)
        
        self.logger.info(
            f"收集完成: Search={len(urls_by_source.get('search', []))}, "
            f"Library={len(urls_by_source.get('library', []))}, "
            f"合并后={len(merged)}"
        )
        
        return merged
```

## Acceptance Criteria

### Phase 1: Playwright Fallback

- [ ] `PlaywrightClient` 类实现完成
- [ ] `ContentFetcher` 统一获取器实现
- [ ] 反爬页面检测逻辑（检测 "Just a moment" 等）
- [ ] Jina → Playwright 自动切换
- [ ] 添加 `playwright` 依赖到 `requirements.txt`
- [ ] 单元测试：反爬检测
- [ ] 集成测试：ScienceDirect DOI 链接能正确获取

### Phase 2: URL Deduplication

- [ ] `URLDeduplicator` 类实现
- [ ] PMID 提取和去重
- [ ] DOI 提取和去重
- [ ] URL 规范化（移除追踪参数、统一格式）
- [ ] `MultiModeCollector` 多模式收集器
- [ ] 单元测试：各种 URL 格式的去重
- [ ] 集成测试：模式1 + 模式2 合并去重

## Success Metrics

1. **反爬成功率**: 对 ScienceDirect 等反爬网站的获取成功率 > 90%
2. **去重准确率**: 重复 URL 100% 被识别
3. **性能影响**: Playwright fallback 平均耗时 < 10 秒/页面

## Dependencies & Risks

### 依赖

| 依赖 | 版本 | 用途 |
|------|------|------|
| playwright | >= 1.40.0 | 浏览器自动化 |
| playwright-browser | chromium | 浏览器引擎 |

### 风险

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| Playwright 较慢 | 处理时间增加 | 只在 Jina 失败时使用 |
| 浏览器内存占用 | 长时间运行可能 OOM | 定期重启浏览器实例 |
| 反爬检测升级 | Playwright 也可能被封 | 添加随机延迟、轮换 User-Agent |

## Implementation Notes

### Playwright 安装

```bash
pip install playwright
playwright install chromium
```

### 反爬检测模式

需要检测的常见反爬标识：
- "Just a moment..." (Cloudflare)
- "Checking your browser"
- "Please enable JavaScript"
- 内容长度 < 500 字符（可能被截断）

### URL 等价性

以下 URL 应被视为相同：
- `https://pubmed.ncbi.nlm.nih.gov/12345/`
- `https://pubmed.ncbi.nlm.nih.gov/12345`
- `https://www.pubmed.ncbi.nlm.nih.gov/12345/`
- `https://doi.org/10.1234/abc` 和 `https://dx.doi.org/10.1234/abc`

## Sources & References

### Internal References

- 现有实现: `src/crawlers/jina_client.py`
- 现有实现: `src/crawlers/collectors.py`
- 测试发现反爬: ScienceDirect DOI 链接返回 "Just a moment..."

### External References

- Playwright 文档: https://playwright.dev/python/
- Jina Reader API: https://jina.ai/reader/
- 常见反爬检测: https://github.com/monkeyMimic/anti-crawler-detection
