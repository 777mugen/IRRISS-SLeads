"""
测试批量处理流程 - 获取 10 篇测试论文
"""

import asyncio
from datetime import datetime
from src.pipeline import LeadPipeline
from src.config import config
from src.logging_config import get_logger


async def test_batch_extraction():
    """
    测试批量提取流程
    
    步骤：
    1. 从 PubMed 搜索论文
    2. 获取 Markdown
    3. 存储到 raw_markdown
    """
    logger = get_logger()
    pipeline = LeadPipeline()
    
    print("\n" + "="*60)
    print("🧪 批量处理测试 - 获取 10 篇论文")
    print("="*60)
    
    try:
        # 1. 运行每日任务（会自动搜索、获取、存储）
        print("\n📋 Step 1: 运行每日爬取任务...")
        print("  搜索关键词:", config.pubmed.search_terms)
        
        # 模拟每日任务（限制 10 篇）
        from src.crawlers.pubmed_entrez import PubMedEntrezClient
        from src.crawlers.jina_client import JinaClient
        from src.db.models import RawMarkdown
        from src.db.utils import get_session
        
        # 搜索论文
        async with PubMedEntrezClient() as client:
            pmids = await client.search(
                query="multiplex immunofluorescence",
                max_results=10
            )
        
        print(f"✅ 找到 {len(pmids)} 个 PMID")
        
        if not pmids:
            print("❌ 没有找到论文")
            return
        
        # 获取详情
        async with PubMedEntrezClient() as client:
            papers_data = await client.fetch_details(pmids)
        
        print(f"✅ 获取到 {len(papers_data)} 篇论文详情")
        
        # 获取 Markdown
        papers = []
        async with JinaClient() as jina:
            for i, paper in enumerate(papers_data[:5], 1):  # 只取 5 篇
                doi = paper.get('doi')
                pmid = paper.get('pmid')
                title = paper.get('title', 'Unknown')[:50]
                
                if not doi:
                    print(f"  [{i}/5] PMID {pmid} - 跳过（无 DOI）")
                    continue
                
                try:
                    print(f"  [{i}/5] PMID {pmid} - {title}...")
                    
                    doi_url = f"https://doi.org/{doi}"
                    markdown = await jina.read(doi_url)
                    
                    papers.append({
                        'doi': doi,
                        'pmid': pmid,
                        'markdown': markdown,
                        'url': doi_url
                    })
                    
                    print(f"  ✅ 成功（{len(markdown)} 字符）")
                    
                    await asyncio.sleep(2)
                
                except Exception as e:
                    print(f"  ❌ 失败: {str(e)[:50]}")
        
        print(f"\n✅ 成功获取 {len(papers)} 篇论文")
        
        if not papers:
            print("❌ 没有获取到任何论文")
            return
        
        # 存储到数据库
        print(f"\n💾 存储到数据库...")
        async with get_session() as session:
            for paper in papers:
                raw = RawMarkdown(
                    doi=paper['doi'],
                    pmid=paper['pmid'],
                    markdown_content=paper['markdown'],
                    source_url=paper['url'],
                    processing_status='pending'
                )
                session.add(raw)
            
            await session.commit()
        
        print(f"✅ 已存储 {len(papers)} 篇论文")
        
        # 检查数据库状态
        from sqlalchemy import select, func
        async with get_session() as session:
            result = await session.execute(
                select(
                    RawMarkdown.processing_status,
                    func.count(RawMarkdown.id)
                ).group_by(RawMarkdown.processing_status)
            )
            
            stats = dict(result.all())
            print(f"\n📊 数据库状态:")
            for status, count in stats.items():
                print(f"  - {status}: {count}")
        
        print("\n" + "="*60)
        print("✅ 测试数据准备完成！")
        print("="*60)
        
    except Exception as e:
        logger.error(f"测试失败: {e}", exc_info=True)
        raise
    finally:
        await pipeline.close()


if __name__ == "__main__":
    asyncio.run(test_batch_extraction())
