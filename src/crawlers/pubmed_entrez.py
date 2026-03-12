"""
PubMed Entrez API Client
PubMed Entrez API 客户端

Official documentation: https://www.ncbi.nlm.nih.gov/books/NBK25500/
"""

import asyncio
import xml.etree.ElementTree as ET
from typing import List, Dict, Optional
from datetime import date

import httpx

from src.logging_config import get_logger


class PubMedEntrezClient:
    """
    PubMed Entrez API 客户端
    
    使用官方 API 搜索论文，获取 PMID 列表
    """
    
    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    
    def __init__(
        self, 
        email: str = "Shane@irriss.com", 
        tool: str = "IRRISS-SLeads",
        api_key: Optional[str] = None
    ):
        """
        初始化客户端
        
        Args:
            email: 联系邮箱（NCBI 要求）
            tool: 工具名称（NCBI 要求）
            api_key: NCBI API Key（可选，有 Key 速率限制更高）
        """
        self.email = email
        self.tool = tool
        self.api_key = api_key
        self.logger = get_logger()
        self._http = httpx.AsyncClient(timeout=30.0)
        
        # 速率限制
        # 无 Key: 3 requests/second
        # 有 Key: 10 requests/second
        self._rate_limit = 0.1 if api_key else 0.33
        self._last_request_time = 0
    
    async def close(self):
        """关闭客户端"""
        await self._http.aclose()
    
    async def _rate_limit_wait(self):
        """等待速率限制"""
        current_time = asyncio.get_event_loop().time()
        elapsed = current_time - self._last_request_time
        
        if elapsed < self._rate_limit:
            await asyncio.sleep(self._rate_limit - elapsed)
        
        self._last_request_time = asyncio.get_event_loop().time()
    
    async def search(
        self,
        query: str,
        max_results: int = 100,
        date_range: Optional[tuple[int, int]] = None
    ) -> List[str]:
        """
        搜索论文，返回 PMID 列表
        
        Args:
            query: 搜索查询（关键词组合）
            max_results: 最大结果数
            date_range: 时间范围 (start_year, end_year)
            
        Returns:
            PMID 列表
            
        Example:
            >>> client = PubMedEntrezClient()
            >>> pmids = await client.search(
            ...     query='"Multiplex Immunofluorescence" OR "mIF"',
            ...     max_results=100,
            ...     date_range=(2024, 2026)
            ... )
        """
        await self._rate_limit_wait()
        
        params = {
            "db": "pubmed",
            "term": query,
            "retmax": max_results,
            "retmode": "json",
            "email": self.email,
            "tool": self.tool,
            "sort": "pub_date"
        }
        
        if self.api_key:
            params["api_key"] = self.api_key
        
        # 添加时间范围筛选
        if date_range:
            start_year, end_year = date_range
            params["datetype"] = "pdat"
            params["mindate"] = f"{start_year}/01/01"
            params["maxdate"] = f"{end_year}/12/31"
        
        self.logger.info(f"PubMed 搜索: {query[:50]}... (max={max_results})")
        
        try:
            response = await self._http.get(
                f"{self.BASE_URL}/esearch.fcgi",
                params=params
            )
            response.raise_for_status()
            
            data = response.json()
            pmids = data.get("esearchresult", {}).get("idlist", [])
            
            self.logger.info(f"搜索结果: {len(pmids)} 个 PMID")
            return pmids
            
        except Exception as e:
            self.logger.error(f"PubMed 搜索失败: {e}")
            return []
    
    async def fetch_details(self, pmids: List[str]) -> List[Dict]:
        """
        获取论文详情
        
        Args:
            pmids: PMID 列表
            
        Returns:
            论文详情列表 [{pmid, doi, title, abstract, ...}, ...]
        """
        if not pmids:
            return []
        
        await self._rate_limit_wait()
        
        params = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "xml",
            "email": self.email,
            "tool": self.tool
        }
        
        if self.api_key:
            params["api_key"] = self.api_key
        
        self.logger.info(f"获取论文详情: {len(pmids)} 篇")
        
        try:
            response = await self._http.get(
                f"{self.BASE_URL}/efetch.fcgi",
                params=params
            )
            response.raise_for_status()
            
            # 解析 XML
            papers = self._parse_xml(response.text)
            
            self.logger.info(f"成功解析 {len(papers)} 篇论文")
            return papers
            
        except Exception as e:
            self.logger.error(f"获取论文详情失败: {e}")
            return []
    
    def _parse_xml(self, xml_content: str) -> List[Dict]:
        """
        解析 PubMed XML 响应
        
        Args:
            xml_content: XML 内容
            
        Returns:
            论文列表
        """
        papers = []
        
        try:
            root = ET.fromstring(xml_content)
            
            for article in root.findall(".//PubmedArticle"):
                paper = {}
                
                # PMID
                pmid_elem = article.find(".//PMID")
                paper["pmid"] = pmid_elem.text if pmid_elem is not None else None
                
                # DOI
                article_elem = article.find(".//Article")
                if article_elem is not None:
                    for eloc in article_elem.findall(".//ELocationID"):
                        if eloc.get("EIdType") == "doi":
                            paper["doi"] = eloc.text
                            break
                
                # Title
                title_elem = article.find(".//ArticleTitle")
                paper["title"] = title_elem.text if title_elem is not None else None
                
                # Abstract
                abstract_elem = article.find(".//Abstract/AbstractText")
                paper["abstract"] = abstract_elem.text if abstract_elem is not None else None
                
                # Publication Date
                pub_date_elem = article.find(".//PubDate")
                if pub_date_elem is not None:
                    year = pub_date_elem.find("Year")
                    month = pub_date_elem.find("Month")
                    day = pub_date_elem.find("Day")
                    
                    if year is not None:
                        date_str = year.text
                        if month is not None:
                            date_str += f"-{month.text}"
                        else:
                            date_str += "-01"
                        if day is not None:
                            date_str += f"-{day.text}"
                        else:
                            date_str += "-01"
                        paper["published_at"] = date_str
                
                # Authors
                authors = []
                for author in article.findall(".//Author"):
                    author_data = {}
                    
                    lastname = author.find("LastName")
                    forename = author.find("ForeName")
                    
                    if lastname is not None and forename is not None:
                        author_data["name"] = f"{forename.text} {lastname.text}"
                    
                    affiliation = author.find(".//AffiliationInfo/Affiliation")
                    if affiliation is not None:
                        author_data["affiliation"] = affiliation.text
                    
                    if author_data:
                        authors.append(author_data)
                
                paper["authors"] = authors
                
                # 只添加有 PMID 的论文
                if paper.get("pmid"):
                    papers.append(paper)
        
        except ET.ParseError as e:
            self.logger.error(f"XML 解析失败: {e}")
        
        return papers
    
    async def search_and_fetch(
        self,
        query: str,
        max_results: int = 100,
        date_range: Optional[tuple[int, int]] = None
    ) -> List[Dict]:
        """
        搜索并获取论文详情（一步到位）
        
        Args:
            query: 搜索查询
            max_results: 最大结果数
            date_range: 时间范围
            
        Returns:
            论文详情列表
        """
        # Step 1: 搜索
        pmids = await self.search(query, max_results, date_range)
        
        if not pmids:
            return []
        
        # Step 2: 获取详情
        papers = await self.fetch_details(pmids)
        
        return papers
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
