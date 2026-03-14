"""
获取 50 篇真实论文进行测试
从 PubMed 搜索最近 30 天的肿瘤学论文
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.crawlers.pubmed_entrez import PubMedEntrezClient


async def fetch_real_papers():
    """获取 50 篇真实论文"""

    client = PubMedEntrezClient()

    # 搜索最近 30 天的肿瘤学论文
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)

    print(f"\n{'='*80}")
    print(f"🔍 搜索真实论文（PubMed API）")
    print(f"{'='*80}\n")

    print(f"搜索条件:")
    print(f"  - 关键词: oncology OR cancer")
    print(f"  - 时间范围: {start_date.strftime('%Y/%m/%d')} - {end_date.strftime('%Y/%m/%d')}")
    print(f"  - 数量: 50 篇\n")

    # 搜索论文
    papers = await client.search_papers(
        query="oncology[Title/Abstract] OR cancer[Title/Abstract]",
        max_results=50,
        date_range=(start_date, end_date)
    )

    print(f"✅ 找到 {len(papers)} 篇论文\n")

    # 提取 DOI 列表
    dois = []
    pmids = []

    for paper in papers:
        doi = paper.get('doi')
        pmid = paper.get('pmid')

        if doi:
            dois.append(doi)
            pmids.append(pmid)
            print(f"  [{len(dois)}] PMID: {pmid} - DOI: {doi}")
        else:
            print(f"  ⚠️  跳过无 DOI 论文: PMID {pmid}")

    # 保存 DOI 列表
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = project_root / f"tmp/real_papers_{timestamp}.json"

    import json

    with open(output_file, 'w') as f:
        json.dump({
            'timestamp': timestamp,
            'total': len(dois),
            'papers': [
                {'pmid': pmid, 'doi': doi}
                for pmid, doi in zip(pmids, dois)
            ]
        }, f, indent=2)

    print(f"\n✅ 保存到: {output_file}")
    print(f"   - 总数: {len(dois)} 篇真实论文\n")

    await client.close()

    return dois, pmids


if __name__ == "__main__":
    asyncio.run(fetch_real_papers())
