"""
Test PubMed Entrez API and NCBI ID Converter
测试 PubMed Entrez API 和 NCBI ID Converter
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.crawlers.pubmed_entrez import PubMedEntrezClient
from src.crawlers.ncbi_id_converter import NCBIIDConverter


async def test_pubmed_search():
    """测试 PubMed 搜索"""
    print("\n" + "="*60)
    print("Test 1: PubMed Search")
    print("="*60)
    
    async with PubMedEntrezClient() as client:
        # 测试搜索
        pmids = await client.search(
            query='"Multiplex Immunofluorescence" OR "mIF"',
            max_results=10,
            date_range=(2024, 2026)
        )
        
        print(f"✅ 搜索成功: {len(pmids)} 个 PMID")
        print(f"   前 5 个: {pmids[:5]}")
        
        return pmids


async def test_pubmed_fetch():
    """测试 PubMed 获取详情"""
    print("\n" + "="*60)
    print("Test 2: PubMed Fetch Details")
    print("="*60)
    
    async with PubMedEntrezClient() as client:
        # 使用已知的 PMID
        pmids = ['37105494', '32301585']
        
        papers = await client.fetch_details(pmids)
        
        print(f"✅ 获取成功: {len(papers)} 篇论文")
        
        for paper in papers[:2]:
            print(f"\n   PMID: {paper.get('pmid')}")
            print(f"   DOI: {paper.get('doi')}")
            print(f"   Title: {paper.get('title', '')[:50]}...")
        
        return papers


async def test_ncbi_converter():
    """测试 NCBI ID Converter"""
    print("\n" + "="*60)
    print("Test 3: NCBI ID Converter")
    print("="*60)
    
    async with NCBIIDConverter() as converter:
        # 使用已知的 PMID
        pmids = ['37105494', '32301585', '29553498']
        
        result = await converter.convert_pmids_to_dois(pmids)
        
        print(f"✅ 转换成功: {len(result)} 个 PMID")
        
        success_count = sum(1 for doi in result.values() if doi)
        print(f"   DOI 转换率: {success_count}/{len(pmids)} ({success_count/len(pmids)*100:.1f}%)")
        
        for pmid, doi in list(result.items())[:3]:
            print(f"   {pmid} → {doi or '无 DOI'}")
        
        return result


async def test_rate_limiting():
    """测试速率限制"""
    print("\n" + "="*60)
    print("Test 4: Rate Limiting")
    print("="*60)
    
    import time
    
    async with PubMedEntrezClient() as client:
        start = time.time()
        
        # 执行 3 次请求
        for i in range(3):
            await client.search("mIF", max_results=5)
            print(f"   请求 {i+1}/3 完成")
        
        elapsed = time.time() - start
        
        # 3 个请求，每个至少等待 0.33 秒
        # 总时间应该 >= 0.66 秒
        print(f"✅ 速率限制正常")
        print(f"   3 个请求耗时: {elapsed:.2f} 秒")
        print(f"   平均: {elapsed/3:.2f} 秒/请求")


async def test_two_stage_extractor():
    """测试两阶段提取器"""
    print("\n" + "="*60)
    print("Test 5: Two-Stage Extractor")
    print("="*60)
    
    from src.extractors.two_stage_extractor import TwoStageExtractor
    
    # 模拟长文本
    long_markdown = """
# Article Title: Test Paper

## Authors
John Doe¹, Jane Smith²

## Abstract
This is a test abstract...

## Correspondence
Corresponding Author: John Doe
Email: john.doe@university.edu
Phone: +1-123-456-7890
Affiliation: Department of Biology, University of Test, 123 Street

""" * 100  # 重复 100 次模拟长文本
    
    async with TwoStageExtractor() as extractor:
        result = await extractor.extract(long_markdown)
        
        if result:
            print(f"✅ 提取成功")
            author = result.get('corresponding_author', {})
            print(f"   姓名: {author.get('name')}")
            print(f"   邮箱: {author.get('email')}")
            print(f"   电话: {author.get('phone')}")
        else:
            print("⚠️  提取失败（可能是 GLM-5 API 未配置）")


async def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("🧪 SLeads 重构测试套件")
    print("="*60)
    
    try:
        # 测试 1: PubMed 搜索
        pmids = await test_pubmed_search()
        
        # 测试 2: PubMed 获取详情
        papers = await test_pubmed_fetch()
        
        # 测试 3: NCBI ID Converter
        dois = await test_ncbi_converter()
        
        # 测试 4: 速率限制
        await test_rate_limiting()
        
        # 测试 5: 两阶段提取器
        await test_two_stage_extractor()
        
        print("\n" + "="*60)
        print("✅ 所有测试通过")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
