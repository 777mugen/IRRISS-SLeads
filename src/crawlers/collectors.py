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
    限制：100 RPM (with API Key)
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
    特殊模式：从库页面提取 URL（支持搜索和翻页）
    
    使用场景：从论文库、索引页面提取所有论文链接
    限制：Reader 500 RPM
    示例库：https://single-cell-papers.bioinfo-assist.com
    
    工作流程：
    1. 搜索关键词获取结果页
    2. 翻页提取所有 URL
    3. 返回去重后的 URL 列表
    """
    
    # 常见的论文 URL 模式
    PAPER_URL_PATTERNS = [
        r'https://pubmed\.ncbi\.nlm\.nih\.gov/\d+/?',
        r'https://doi\.org/10\.[^\s<>"]+',
        r'https://www\.ncbi\.nlm\.nih\.gov/pmc/articles/PMC\d+',
    ]
    
    def __init__(
        self,
        library_url: str,
        keyword: Optional[str] = None,
        max_pages: int = 10,
        max_urls: int = 100,
        url_patterns: Optional[list[str]] = None
    ):
        """
        初始化库收集器
        
        Args:
            library_url: 库的基础 URL
            keyword: 搜索关键词（可选）
            max_pages: 最大翻页数
            max_urls: 最大 URL 数量
            url_patterns: URL 匹配模式列表
        """
        super().__init__()
        self.library_url = library_url.rstrip('/')
        self.keyword = keyword
        self.max_pages = max_pages
        self.max_urls = max_urls
        self.url_patterns = url_patterns or self.PAPER_URL_PATTERNS
    
    def _build_search_url(self, page: int = 1) -> str:
        """构建搜索 URL"""
        url = self.library_url
        params = []
        
        if self.keyword:
            params.append(f"q={self.keyword}")
        
        if page > 1:
            params.append(f"page={page}")
        
        if params:
            url += "/?" + "&".join(params)
        
        return url
    
    def _extract_urls_from_content(self, content: str) -> list[str]:
        """从内容中提取论文 URL"""
        urls = set()
        
        for pattern in self.url_patterns:
            for match in re.finditer(pattern, content):
                url = match.group(0).rstrip('.,;:!?)]}>')
                # 标准化 PubMed URL
                if 'pubmed.ncbi.nlm.nih.gov' in url:
                    # 提取 PMID
                    pmid_match = re.search(r'/(\d+)/?$', url)
                    if pmid_match:
                        pmid = pmid_match.group(1)
                        url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
                urls.add(url)
        
        return list(urls)
    
    def _extract_pagination_info(self, content: str) -> dict:
        """提取分页信息"""
        info = {
            'total': 0,
            'per_page': 20,
            'total_pages': 1
        }
        
        # 匹配 "当前共找到 123 篇文献"
        total_match = re.search(r'当前共找到\s*(\d+)\s*篇', content)
        if total_match:
            info['total'] = int(total_match.group(1))
            info['total_pages'] = (info['total'] + info['per_page'] - 1) // info['per_page']
        
        return info
    
    async def collect(self) -> list[str]:
        """
        从库中收集 URL（支持翻页）
        
        Returns:
            URL 列表
        """
        all_urls = set()
        
        # Step 1: 获取第一页，提取分页信息
        first_page_url = self._build_search_url(page=1)
        self.logger.info(f"从库获取模式: 读取 {first_page_url}")
        
        content = await self.jina.read(first_page_url)
        
        # 提取第一页的 URL
        page_urls = self._extract_urls_from_content(content)
        all_urls.update(page_urls)
        self.logger.info(f"第 1 页提取到 {len(page_urls)} 个 URL")
        
        # 提取分页信息
        page_info = self._extract_pagination_info(content)
        total_papers = page_info['total']
        total_pages = min(page_info['total_pages'], self.max_pages)
        
        self.logger.info(f"库中共有 {total_papers} 篇文献，共 {page_info['total_pages']} 页")
        self.logger.info(f"将读取前 {total_pages} 页")
        
        # Step 2: 翻页获取剩余 URL
        for page in range(2, total_pages + 1):
            if len(all_urls) >= self.max_urls:
                self.logger.info(f"已达到最大 URL 数量限制 ({self.max_urls})")
                break
            
            page_url = self._build_search_url(page=page)
            self.logger.info(f"读取第 {page} 页: {page_url}")
            
            try:
                content = await self.jina.read(page_url)
                page_urls = self._extract_urls_from_content(content)
                new_urls = [u for u in page_urls if u not in all_urls]
                all_urls.update(new_urls)
                self.logger.info(f"第 {page} 页提取到 {len(new_urls)} 个新 URL，累计 {len(all_urls)} 个")
            except Exception as e:
                self.logger.warning(f"读取第 {page} 页失败: {e}")
                continue
        
        result = list(all_urls)[:self.max_urls]
        self.logger.info(f"从库中共提取到 {len(result)} 个唯一 URL")
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


class SingleCellPapersCollector(LibraryCollector):
    """单细胞论文库收集器"""
    
    def __init__(self, keyword: str = "mIF", max_pages: int = 10, max_urls: int = 100):
        super().__init__(
            library_url="https://single-cell-papers.bioinfo-assist.com",
            keyword=keyword,
            max_pages=max_pages,
            max_urls=max_urls
        )


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
        """
        初始化多模式收集器
        
        Args:
            keywords: 关键词列表
            library_url: 库 URL（可选）
            max_results_per_mode: 每种模式的最大结果数
        """
        self.keywords = keywords
        self.library_url = library_url
        self.max_results = max_results_per_mode
        self.logger = get_logger()
    
    async def collect_all(self) -> list[dict]:
        """
        运行所有收集模式并合并去重
        
        Returns:
            [{'url': str, 'sources': ['search', 'library']}, ...]
        """
        from src.processors.url_deduplicator import URLDeduplicator
        
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
        deduplicator = URLDeduplicator()
        merged = deduplicator.merge_sources(urls_by_source)
        
        self.logger.info(
            f"收集完成: Search={len(urls_by_source.get('search', []))}, "
            f"Library={len(urls_by_source.get('library', []))}, "
            f"合并后={len(merged)}"
        )
        
        return merged
