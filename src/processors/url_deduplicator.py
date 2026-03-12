"""
URL deduplication utilities.
URL 去重工具。
"""

import re
from typing import Optional
from urllib.parse import urlparse, parse_qs, urlencode


class URLDeduplicator:
    """
    URL 去重器
    
    基于 URL 的规范化形式进行去重
    支持 DOI 和 PubMed URL 的等价识别
    """
    
    # PMID 提取模式
    PMID_PATTERN = re.compile(r'pubmed\.ncbi\.nlm\.nih\.gov/(\d+)')
    DOI_PATTERN = re.compile(r'doi\.org/(10\.[^\s]+)', re.IGNORECASE)
    
    # 追踪参数（需要移除）
    TRACKING_PARAMS = {
        'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
        'ref', 'source', 'from', 'fbclid', 'gclid', 'msclkid'
    }
    
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
        - 移除 fragment
        """
        url = url.strip().rstrip('/')
        parsed = urlparse(url)
        
        # 统一域名小写
        netloc = parsed.netloc.lower()
        
        # 移除 www 前缀（可选）
        if netloc.startswith('www.'):
            netloc = netloc[4:]
        
        # 移除追踪参数
        query = ''
        if parsed.query:
            params = parse_qs(parsed.query, keep_blank_values=True)
            filtered = {
                k: v for k, v in params.items()
                if k.lower() not in self.TRACKING_PARAMS
            }
            if filtered:
                query = urlencode(filtered, doseq=True)
        
        # 重建 URL（不包含 fragment）
        path = parsed.path.rstrip('/')
        normalized = f"{parsed.scheme}://{netloc}{path}"
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
            # URL 解码
            from urllib.parse import unquote
            doi = unquote(doi)
            return ('doi', doi.lower())
        
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
        
        # 基于 PMID 去重
        if id_type == 'pmid' and id_value:
            if id_value in self._seen_pmids:
                return True
            self._seen_pmids.add(id_value)
        
        # 基于 DOI 去重
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
        # 使用 PMID/DOI 作为主键
        url_sources: dict[str, list[str]] = {}
        original_urls: dict[str, str] = {}  # 保存原始 URL
        
        for source, urls in urls_by_source.items():
            for url in urls:
                # 提取标识符作为主键
                id_type, id_value = self.extract_identifier(url)
                
                if id_type and id_value:
                    # 使用标识符作为主键
                    key = f"{id_type}:{id_value}"
                else:
                    # 使用规范化 URL 作为主键
                    key = self.normalize_url(url)
                
                if key not in url_sources:
                    url_sources[key] = []
                    original_urls[key] = url
                
                if source not in url_sources[key]:
                    url_sources[key].append(source)
        
        return [
            {'url': original_urls[key], 'sources': sources}
            for key, sources in url_sources.items()
        ]
    
    def get_stats(self) -> dict:
        """获取去重统计"""
        return {
            'seen_urls': len(self._seen_urls),
            'seen_pmids': len(self._seen_pmids),
            'seen_dois': len(self._seen_dois),
        }
    
    def reset(self):
        """重置去重状态"""
        self._seen_urls.clear()
        self._seen_pmids.clear()
        self._seen_dois.clear()
