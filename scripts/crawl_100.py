"""
爬取100条数据并导出CSV
"""

import asyncio
import csv
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.crawlers.collectors import PubMedSearchCollector, MultiModeCollector
from src.processors.url_deduplicator import URLDeduplicator
from src.crawlers.content_fetcher import ContentFetcher
from src.pipeline import LeadPipeline
from src.notifiers.feishu import FeishuNotifier
from src.logging_config import get_logger


async def main():
    logger = get_logger()
    logger.info("开始爬取100条数据")
    
    print("\n🔬 SLeads 数据爬取 (100条)")
    print("=" * 60)
    
    start_time = asyncio.get_event_loop().time()
    
    # Step 1: URL 收集
    print("\n[1/6] 收集 URL...")
    collector = MultiModeCollector(
        keywords=["Multiplex Immunofluorescence", "mIF", "immunofluorescence"],
        max_results_per_mode=60
    )
    urls = await collector.collect_all()
    await collector.close() if hasattr(collector, 'close') else None
    print(f"  ✅ 收集到 {len(urls)} 个 URL")
    
    # Step 2: URL 去重（已在 collect_all 中完成）
    print("\n[2/6] 准备 URL...")
    urls_to_process = urls[:100]
    print(f"  📊 将处理前 {len(urls_to_process)} 个")
    
    # Step 3: 内容获取
    print("\n[3/6] 获取页面内容...")
    fetcher = ContentFetcher(enable_playwright=False)
    contents = []
    
    for i, url_info in enumerate(urls_to_process):
        url = url_info['url']
        print(f"  [{i+1}/{len(urls_to_process)}] {url[:50]}...", end="", flush=True)
        
        result = await fetcher.fetch(url)
        if result['success']:
            contents.append(result)
            print(" ✅")
        else:
            print(" ❌")
        
        # 每10个显示进度
        if (i + 1) % 10 == 0:
            print(f"  📊 进度: {len(contents)}/{i+1} 成功")
    
    await fetcher.close()
    print(f"\n  ✅ 成功获取 {len(contents)} 个页面")
    
    # Step 4: LLM 提取
    print("\n[4/6] LLM 提取...")
    pipeline = LeadPipeline()
    leads = []
    
    for i, content in enumerate(contents):
        print(f"  [{i+1}/{len(contents)}] 提取中...", end="", flush=True)
        
        try:
            result = await pipeline.process_paper(
                content['url'],
                content['content']
            )
            
            if result:
                leads.append(result)
                print(f" ✅ {result.get('title', 'N/A')[:30]}...")
            else:
                print(" ⚠️ 提取失败")
        except Exception as e:
            print(f" ❌ {str(e)[:50]}")
        
        # 每10个显示进度
        if (i + 1) % 10 == 0:
            print(f"  📊 进度: {len(leads)}/{i+1} 成功")
    
    await pipeline.close()
    print(f"\n  ✅ 成功提取 {len(leads)} 条线索")
    
    # Step 5: CSV 导出
    print("\n[5/6] 导出 CSV...")
    output_dir = Path("output/paper_leads")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    today = date.today()
    csv_path = output_dir / f"paper_leads_{today}.csv"
    
    with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = None
        for lead in leads:
            row = {
                'PMID': lead.get('pmid', ''),
                'DOI': lead.get('doi', ''),
                '文章标题': lead.get('title', ''),
                '发表时间': lead.get('published_at', ''),
                '通讯作者姓名': lead.get('corresponding_author', {}).get('name', ''),
                '通讯作者单位': lead.get('corresponding_author', {}).get('affiliation', ''),
                '通讯作者邮箱': lead.get('corresponding_author', {}).get('email', ''),
                '等级': lead.get('grade', ''),
                '分数': lead.get('score', ''),
                '来源链接': lead.get('source_url', ''),
            }
            
            if writer is None:
                writer = csv.DictWriter(f, fieldnames=row.keys())
                writer.writeheader()
            
            writer.writerow(row)
    
    print(f"  ✅ CSV 已导出: {csv_path}")
    print(f"  📊 共 {len(leads)} 条记录")
    
    # Step 6: 飞书通知
    print("\n[6/6] 发送飞书通知...")
    duration = asyncio.get_event_loop().time() - start_time
    
    notifier = FeishuNotifier()
    success = await notifier.send_daily_summary({
        'papers_found': len(urls_to_process),
        'papers_processed': len(contents),
        'tenders_found': 0,
        'leads_exported': len(leads),
        'duration_seconds': duration
    })
    await notifier.close()
    
    if success:
        print("  ✅ 飞书通知发送成功")
    else:
        print("  ⚠️ 飞书通知发送失败")
    
    # 总结
    print("\n" + "=" * 60)
    print("✅ 爬取完成")
    print("=" * 60)
    print(f"  ⏱️  总耗时: {duration:.1f} 秒 ({duration/60:.1f} 分钟)")
    print(f"  📊 URL 收集: {len(urls_to_process)} 个")
    print(f"  📄 内容获取: {len(contents)} 个")
    print(f"  🎯 线索提取: {len(leads)} 个")
    print(f"  📁 CSV 文件: {csv_path}")


if __name__ == "__main__":
    asyncio.run(main())
