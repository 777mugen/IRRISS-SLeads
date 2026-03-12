"""
Full pipeline integration test.
完整管道集成测试。
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.crawlers.collectors import PubMedSearchCollector, SingleCellPapersCollector, MultiModeCollector
from src.processors.url_deduplicator import URLDeduplicator
from src.crawlers.content_fetcher import ContentFetcher
from src.pipeline import LeadPipeline
from src.exporters.csv_exporter import CSVExporter
from src.notifiers.feishu import FeishuNotifier
from src.logging_config import get_logger


async def test_url_collection():
    """测试 URL 收集"""
    print("\n" + "="*60)
    print("Step 1: URL 收集（多模式）")
    print("="*60)
    
    # 模式1: Search
    print("\n[模式1] Search 搜索...")
    search_collector = PubMedSearchCollector(
        keywords=["mIF", "immunofluorescence"],
        max_results=5
    )
    search_urls = await search_collector.collect()
    print(f"  ✅ Search 返回 {len(search_urls)} 个 URL")
    await search_collector.close()
    
    # 模式2: Library
    print("\n[模式2] Library 搜索...")
    library_collector = SingleCellPapersCollector(
        keyword="mIF",
        max_pages=1,
        max_urls=5
    )
    library_urls = await library_collector.collect()
    print(f"  ✅ Library 返回 {len(library_urls)} 个 URL")
    await library_collector.close()
    
    return {'search': search_urls, 'library': library_urls}


async def test_url_deduplication(urls_by_source: dict):
    """测试 URL 去重"""
    print("\n" + "="*60)
    print("Step 2: URL 去重")
    print("="*60)
    
    deduplicator = URLDeduplicator()
    
    # 合并并去重
    merged = deduplicator.merge_sources(urls_by_source)
    
    print(f"\n  Search: {len(urls_by_source.get('search', []))} 个")
    print(f"  Library: {len(urls_by_source.get('library', []))} 个")
    print(f"  合并后: {len(merged)} 个唯一 URL")
    
    # 显示统计
    stats = deduplicator.get_stats()
    print(f"\n  去重统计:")
    print(f"    - PMID 去重: {stats['seen_pmids']} 个")
    print(f"    - DOI 去重: {stats['seen_dois']} 个")
    print(f"    - URL 去重: {stats['seen_urls']} 个")
    
    return merged


async def test_content_fetching(urls: list[dict], max_count: int = 3):
    """测试内容获取（带 Fallback）"""
    print("\n" + "="*60)
    print(f"Step 3: 内容获取（前 {max_count} 个）")
    print("="*60)
    
    fetcher = ContentFetcher(enable_playwright=False)  # 先不启用 Playwright
    results = []
    
    for i, url_info in enumerate(urls[:max_count]):
        url = url_info['url']
        sources = url_info.get('sources', [])
        
        print(f"\n  [{i+1}/{max_count}] 获取: {url[:60]}...")
        result = await fetcher.fetch(url)
        
        if result['success']:
            print(f"    ✅ 成功 ({result['source']}, {len(result['content'])} 字符)")
            results.append(result)
        else:
            print(f"    ❌ 失败: {result.get('error', 'Unknown error')}")
    
    await fetcher.close()
    
    stats = fetcher.get_stats()
    print(f"\n  获取统计:")
    print(f"    - 总请求: {stats['total_requests']}")
    print(f"    - Jina 成功: {stats['jina_success']}")
    print(f"    - 成功率: {stats['success_rate']:.1f}%")
    
    return results


async def test_llm_extraction(contents: list[dict]):
    """测试 LLM 提取（带速率控制）"""
    print("\n" + "="*60)
    print("Step 4: LLM 提取")
    print("="*60)
    
    pipeline = LeadPipeline()
    results = []
    
    for i, content in enumerate(contents):
        print(f"\n  [{i+1}/{len(contents)}] 提取: {content['url'][:50]}...")
        
        try:
            result = await pipeline.process_paper(
                content['url'],
                content['content']
            )
            
            if result:
                title = result.get('title', 'N/A')[:40]
                grade = result.get('grade', 'N/A')
                print(f"    ✅ 提取成功: {title}... (等级: {grade})")
                results.append(result)
            else:
                print(f"    ⚠️  提取失败（可能是缺少必填字段）")
        except Exception as e:
            print(f"    ❌ 提取出错: {e}")
    
    await pipeline.close()
    
    print(f"\n  提取统计:")
    print(f"    - 成功: {len(results)}/{len(contents)}")
    
    return results


async def test_csv_export(leads: list[dict]):
    """测试 CSV 导出"""
    print("\n" + "="*60)
    print("Step 5: CSV 导出")
    print("="*60)
    
    from datetime import date
    
    exporter = CSVExporter()
    output_dir = Path("output/paper_leads")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    today = date.today()
    filename = f"paper_leads_test_{today}.csv"
    filepath = output_dir / filename
    
    # 写入 CSV
    with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
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
                import csv
                writer = csv.DictWriter(f, fieldnames=row.keys())
                writer.writeheader()
            
            writer.writerow(row)
    
    print(f"  ✅ CSV 已导出: {filepath}")
    print(f"  📊 共 {len(leads)} 条记录")
    
    return filepath


async def test_feishu_notification(stats: dict):
    """测试飞书通知"""
    print("\n" + "="*60)
    print("Step 6: 飞书通知")
    print("="*60)
    
    notifier = FeishuNotifier()
    success = await notifier.send_daily_summary(stats)
    await notifier.close()
    
    if success:
        print("  ✅ 飞书通知发送成功")
    else:
        print("  ⚠️  飞书通知发送失败（可能未配置）")
    
    return success


async def main():
    """运行完整流程测试"""
    logger = get_logger()
    logger.info("开始完整流程测试")
    
    print("\n" + "🔬 SLeads 完整流程测试")
    print("="*60)
    
    start_time = asyncio.get_event_loop().time()
    
    try:
        # Step 1: URL 收集
        urls_by_source = await test_url_collection()
        
        # Step 2: URL 去重
        merged_urls = await test_url_deduplication(urls_by_source)
        
        if not merged_urls:
            print("\n❌ 没有找到任何 URL，测试终止")
            return
        
        # Step 3: 内容获取（只测试前 3 个）
        contents = await test_content_fetching(merged_urls, max_count=3)
        
        if not contents:
            print("\n❌ 没有成功获取任何内容，测试终止")
            return
        
        # Step 4: LLM 提取
        leads = await test_llm_extraction(contents)
        
        # Step 5: CSV 导出
        if leads:
            csv_path = await test_csv_export(leads)
        else:
            print("\n⚠️  没有成功提取任何线索，跳过 CSV 导出")
            csv_path = None
        
        # Step 6: 飞书通知
        duration = asyncio.get_event_loop().time() - start_time
        await test_feishu_notification({
            'papers_found': len(merged_urls),
            'papers_processed': len(contents),
            'tenders_found': 0,
            'leads_exported': len(leads),
            'duration_seconds': duration
        })
        
        # 总结
        print("\n" + "="*60)
        print("✅ 测试完成")
        print("="*60)
        print(f"  ⏱️  总耗时: {duration:.1f} 秒")
        print(f"  📊 URL 收集: {len(merged_urls)} 个")
        print(f"  📄 内容获取: {len(contents)} 个")
        print(f"  🎯 线索提取: {len(leads)} 个")
        if csv_path:
            print(f"  📁 CSV 文件: {csv_path}")
        
    except Exception as e:
        logger.exception("测试失败")
        print(f"\n❌ 测试失败: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
