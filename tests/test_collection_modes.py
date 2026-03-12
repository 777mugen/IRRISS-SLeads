#!/usr/bin/env python3
"""
Test two collection modes with full workflow.
测试两种收集模式的完整工作流程。
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import config
from src.logging_config import setup_logging, get_logger
from src.crawlers.collectors import (
    SearchCollector, 
    LibraryCollector, 
    PubMedSearchCollector,
    SingleCellPapersCollector
)
from src.crawlers.jina_client import JinaClient


async def test_mode1_search():
    """
    模式1测试：默认模式 (Search → Reader)
    """
    setup_logging(log_level='INFO')
    logger = get_logger()
    
    print("\n" + "=" * 70)
    print("模式1: Search → Reader (默认模式)")
    print("=" * 70)
    
    # 使用 Search 搜索 PubMed
    keywords = ["Multiplex Immunofluorescence", "mIF"]
    collector = PubMedSearchCollector(keywords, max_results=10)
    
    try:
        # Step 1: Search 获取 URL
        print("\n[Step 1] Search 搜索关键词...")
        urls = await collector.collect()
        
        if not urls:
            print("未找到任何 URL")
            return []
        
        print(f"✅ 找到 {len(urls)} 个 URL")
        for i, url in enumerate(urls[:5], 1):
            print(f"  {i}. {url}")
        if len(urls) > 5:
            print(f"  ... 还有 {len(urls) - 5} 个")
        
        return urls
        
    finally:
        await collector.close()


async def test_mode2_library():
    """
    模式2测试：从库获取模式 (Library → Reader)
    支持搜索和翻页
    """
    setup_logging(log_level='INFO')
    logger = get_logger()
    
    print("\n" + "=" * 70)
    print("模式2: Library → Reader (从库获取模式)")
    print("支持: 搜索关键词 + 自动翻页")
    print("=" * 70)
    
    # 使用单细胞论文库，搜索 "mIF" 关键词
    collector = SingleCellPapersCollector(
        keyword="mIF",
        max_pages=3,      # 读取前 3 页
        max_urls=50       # 最多 50 个 URL
    )
    
    try:
        # Step 1: 读取库搜索结果（自动翻页）
        print("\n[Step 1] 搜索库页面并翻页提取 URL...")
        urls = await collector.collect()
        
        if not urls:
            print("未从库中提取到任何 URL")
            return []
        
        print(f"\n✅ 从库中提取到 {len(urls)} 个唯一 URL")
        print("\n前 10 个 URL:")
        for i, url in enumerate(urls[:10], 1):
            print(f"  {i}. {url}")
        
        return urls
        
    finally:
        await collector.close()


async def test_read_content(urls: list[str], max_read: int = 3):
    """
    测试 Reader 读取内容
    
    Args:
        urls: URL 列表
        max_read: 最多读取几篇
    """
    print("\n" + "=" * 70)
    print(f"Reader 读取论文内容 (前 {max_read} 篇)")
    print("=" * 70)
    
    jina = JinaClient()
    
    try:
        for i, url in enumerate(urls[:max_read], 1):
            print(f"\n[{i}/{min(len(urls), max_read)}] 读取: {url}")
            try:
                content = await jina.read(url)
                print(f"  ✅ 内容长度: {len(content)} 字符")
                # 提取标题
                title_match = content.split('\n')[0] if content else "N/A"
                print(f"  📄 标题: {title_match[:80]}...")
            except Exception as e:
                print(f"  ❌ 错误: {e}")
    finally:
        await jina.close()


async def main():
    """主函数"""
    print("=" * 70)
    print("URL 收集模式测试")
    print("=" * 70)
    
    # 测试模式1
    mode1_urls = await test_mode1_search()
    
    # 等待一下
    print("\n⏳ 等待 3 秒...")
    await asyncio.sleep(3)
    
    # 测试模式2
    mode2_urls = await test_mode2_library()
    
    # 测试 Reader 读取（使用模式2的 URL）
    if mode2_urls:
        print("\n⏳ 等待 3 秒...")
        await asyncio.sleep(3)
        await test_read_content(mode2_urls, max_read=3)
    
    print("\n" + "=" * 70)
    print("测试总结")
    print("=" * 70)
    print(f"模式1 (Search): {len(mode1_urls)} 个 URL")
    print(f"模式2 (Library): {len(mode2_urls)} 个 URL")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
