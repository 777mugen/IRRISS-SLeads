"""
获取真实论文数据 - 简化版
"""

import asyncio
import httpx
from datetime import datetime, timedelta
from src.db.models import RawMarkdown
from src.db.utils import get_session
from src.crawlers.jina_client import JinaClient
import xml.etree.ElementTree as ET


async def search_pubmed_papers(query: str, max_results: int = 10):
    """搜索 PubMed 论文"""
    
    print(f"\n🔍 搜索 PubMed: {query}")
    
    # 构建搜索 URL
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    
    # 搜索
    search_url = f"{base_url}/esearch.fcgi"
    params = {
        "db": "pubmed",
        "term": query,
        "retmax": max_results,
        "datetype": "pdat",
        "mindate": "2024/01/01",
        "maxdate": datetime.now().strftime("%Y/%m/%d"),
        "retmode": "json"
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(search_url, params=params)
        data = response.json()
        
        pmids = data.get("esearchresult", {}).get("idlist", [])
        print(f"✅ 找到 {len(pmids)} 篇论文")
        
        return pmids


async def fetch_paper_details(pmids: list):
    """获取论文详情"""
    
    print(f"\n📖 获取论文详情...")
    
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    fetch_url = f"{base_url}/efetch.fcgi"
    
    params = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "xml"
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(fetch_url, params=params)
        
        # 解析 XML
        root = ET.fromstring(response.content)
        
        papers = []
        for article in root.findall(".//PubmedArticle"):
            # 提取 PMID
            pmid = article.find(".//PMID").text
            
            # 提取 DOI
            doi_elem = article.find(".//ArticleId[@IdType='doi']")
            doi = doi_elem.text if doi_elem is not None else None
            
            # 提取标题
            title_elem = article.find(".//ArticleTitle")
            title = title_elem.text if title_elem is not None else "Unknown"
            
            if doi:
                papers.append({
                    'pmid': pmid,
                    'doi': doi,
                    'title': title
                })
        
        print(f"✅ 获取到 {len(papers)} 篇论文详情")
        
        return papers


async def main():
    print("\n" + "="*60)
    print("🚀 获取真实论文数据")
    print("="*60)
    
    # 1. 搜索论文（关键词：multiplex immunofluorescence）
    pmids = await search_pubmed_papers("multiplex immunofluorescence", max_results=10)
    
    if not pmids:
        print("❌ 没有找到论文")
        return
    
    # 2. 获取详情
    papers = await fetch_paper_details(pmids[:5])  # 只取 5 篇
    
    # 3. 获取 Markdown
    print(f"\n📥 获取 Markdown 内容...")
    
    papers_with_markdown = []
    async with JinaClient() as jina:
        for i, paper in enumerate(papers, 1):
            doi = paper['doi']
            title = paper['title'][:50]
            
            try:
                print(f"  [{i}/{len(papers)}] PMID {paper['pmid']} - {title}...")
                
                doi_url = f"https://doi.org/{doi}"
                markdown = await jina.read(doi_url)
                
                papers_with_markdown.append({
                    **paper,
                    'markdown': markdown,
                    'url': doi_url
                })
                
                print(f"  ✅ 成功（{len(markdown)} 字符）")
                
                await asyncio.sleep(2)
            
            except Exception as e:
                print(f"  ❌ 失败: {str(e)[:50]}")
    
    print(f"\n✅ 成功获取 {len(papers_with_markdown)} 篇论文")
    
    if not papers_with_markdown:
        print("❌ 没有获取到任何论文")
        return
    
    # 4. 存储到数据库
    print(f"\n💾 存储到数据库...")
    async with get_session() as session:
        for paper in papers_with_markdown:
            raw = RawMarkdown(
                doi=paper['doi'],
                pmid=paper['pmid'],
                markdown_content=paper['markdown'],
                source_url=paper['url'],
                processing_status='pending'
            )
            session.add(raw)
        
        await session.commit()
    
    print(f"✅ 已存储 {len(papers_with_markdown)} 篇论文到数据库")
    
    print("\n" + "="*60)
    print("✅ 真实数据获取完成！")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
