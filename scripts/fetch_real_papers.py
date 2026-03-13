"""
获取真实论文数据 - 优化版（优先中国作者）
"""

import asyncio
import httpx
from datetime import datetime, timedelta
from src.db.models import RawMarkdown
from src.db.utils import get_session
from src.crawlers.jina_client import JinaClient
import xml.etree.ElementTree as ET


async def search_pubmed_papers(query: str, max_results: int = 20):
    """搜索 PubMed 论文"""
    
    print(f"\n🔍 搜索 PubMed: {query}")
    
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
            
            # 提取作者和国籍
            authors = []
            affiliations = []
            for author in article.findall(".//Author"):
                lastname = author.find("LastName")
                forename = author.find("ForeName")
                if lastname is not None and forename is not None:
                    authors.append(f"{forename.text} {lastname.text}")
            
            for affiliation in article.findall(".//AffiliationInfo/Affiliation"):
                if affiliation.text:
                    affiliations.append(affiliation.text)
            
            # 判断是否包含中国作者
            is_chinese = any(
                any(keyword in aff.lower() for keyword in 
                    ['china', 'beijing', 'shanghai', 'guangzhou', 'shenzhen', 
                     'nanjing', 'wuhan', 'chengdu', 'hangzhou', 'tianjin'])
                for aff in affiliations
            )
            
            if doi:
                papers.append({
                    'pmid': pmid,
                    'doi': doi,
                    'title': title,
                    'authors': authors,
                    'affiliations': affiliations,
                    'is_chinese': is_chinese
                })
        
        print(f"✅ 获取到 {len(papers)} 篇论文详情")
        
        # 优先返回中国作者论文
        chinese_papers = [p for p in papers if p['is_chinese']]
        other_papers = [p for p in papers if not p['is_chinese']]
        
        print(f"   - 包含中国作者: {len(chinese_papers)} 篇")
        print(f"   - 其他: {len(other_papers)} 篇")
        
        # 优先返回中国作者论文
        return chinese_papers + other_papers


async def main():
    print("\n" + "="*60)
    print("🚀 获取真实论文数据（优化版）")
    print("="*60)
    
    # 1. 搜索论文（多个关键词，提高中国作者概率）
    queries = [
        "multiplex immunofluorescence China",
        "spatial proteomics Beijing",
        "tumor microenvironment Shanghai",
        "cancer immunotherapy Guangzhou"
    ]
    
    all_pmids = []
    for query in queries:
        pmids = await search_pubmed_papers(query, max_results=10)
        all_pmids.extend(pmids)
        await asyncio.sleep(1)
    
    # 去重
    all_pmids = list(set(all_pmids))[:50]  # 最多 50 篇
    
    # 2. 获取详情
    papers = await fetch_paper_details(all_pmids)
    
    # 3. 获取 Markdown（前 20 篇）
    print(f"\n📥 获取 Markdown 内容（目标 20 篇）...")
    
    papers_with_markdown = []
    async with JinaClient() as jina:
        for i, paper in enumerate(papers[:30], 1):  # 尝试 30 篇，成功 20 篇即可
            doi = paper['doi']
            title = paper.get('title', 'Unknown')
            title_display = title[:50] if title else 'Unknown'
            is_chinese = "🇨🇳" if paper['is_chinese'] else "🌍"
            
            try:
                print(f"  [{i}/{min(30, len(papers))}] {is_chinese} PMID {paper['pmid']} - {title_display}...")

                doi_url = f"https://doi.org/{doi}"
                markdown = await jina.read_paper(doi_url)  # ✅ 使用优化的 read_paper 方法

                # 检查是否被反爬虫拦截
                if "Just a moment" in markdown or len(markdown) < 200:
                    print(f"  ⚠️  跳过（内容异常）")
                    continue
                
                papers_with_markdown.append({
                    **paper,
                    'markdown': markdown,
                    'url': doi_url
                })
                
                print(f"  ✅ 成功（{len(markdown)} 字符）")
                
                # 达到 20 篇即可停止
                if len(papers_with_markdown) >= 20:
                    break
                
                await asyncio.sleep(2)
            
            except Exception as e:
                print(f"  ❌ 失败: {str(e)[:50]}")
    
    print(f"\n✅ 成功获取 {len(papers_with_markdown)} 篇论文")
    
    if len(papers_with_markdown) < 20:
        print(f"⚠️  未达到 20 篇目标，尝试增加搜索关键词或调整时间范围")
    
    if not papers_with_markdown:
        print("❌ 没有获取到任何论文")
        return
    
    # 统计中国作者论文
    chinese_count = sum(1 for p in papers_with_markdown if p['is_chinese'])
    print(f"\n📊 中国作者论文: {chinese_count}/{len(papers_with_markdown)}")
    
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
