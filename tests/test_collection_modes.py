#!/usr/bin/env python3
"""
Test two collection modes.
测试两种收集模式。
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import config
from src.logging_config import setup_logging, get_logger
from src.crawlers.collectors import SearchCollector, LibraryCollector, PubMedSearchCollector
from src.crawlers.jina_client import JinaClient


async def test_mode1_search():
    """
    模式1测试：默认模式 (Search → Reader)
    """
    setup_logging(log_level='INFO')
    logger = get_logger()
    
    print("\n" + "=" * 60)
    print("模式1: Search → Reader (默认模式)")
    print("=" * 60)
    
    # 使用 Search 搜索 PubMed
    keywords = ["Multiplex Immunofluorescence", "mIF"]
    collector = PubMedSearchCollector(keywords, max_results=5)
    
    try:
        # Step 1: Search 获取 URL
        print("\n[Step 1] Search 搜索关键词...")
        urls = await collector.collect()
        
        if not urls:
            print("未找到任何 URL")
            return
        
        print(f"找到 {len(urls)} 个 URL:")
        for i, url in enumerate(urls, 1):
            print(f"  {i}. {url}")
        
        # Step 2: Reader 读取内容
        print("\n[Step 2] Reader 读取内容...")
        jina = JinaClient()
        
        for i, url in enumerate(urls[:3], 1):
            print(f"\n读取 {i}/{min(len(urls), 3)}: {url}")
            content = await jina.read(url)
            print(f"  内容长度: {len(content)} 字符")
            print(f"  前 200 字符: {content[:200]}...")
        
        await jina.close()
        print("\n✅ 模式1测试完成!")
        
    finally:
        await collector.close()


async def test_mode2_library():
    """
    模式2测试：从库获取模式 (Library → Reader)
    """
    setup_logging(log_level='INFO')
    logger = get_logger()
    
    print("\n" + "=" * 60)
    print("模式2: Library → Reader (从库获取模式)")
    print("=" * 60)
    
    # 从论文库提取 URL
    library_url = "https://single-cell-papers.bioinfo-assist.com"
    collector = LibraryCollector(library_url, max_urls=10)
    
    try:
        # Step 1: Reader 读取库页面
        print(f"\n[Step 1] 读取库页面: {library_url}")
        urls = await collector.collect()
        
        if not urls:
            print("未从库中提取到任何 URL")
            return
        
        print(f"从库中提取到 {len(urls)} 个 URL:")
        for i, url in enumerate(urls[:10], 1):
            print(f"  {i}. {url}")
        
        # Step 2: Reader 读取内容
        print("\n[Step 2] Reader 读取论文内容...")
        jina = JinaClient()
        
        for i, url in enumerate(urls[:3], 1):
            print(f"\n读取 {i}/{min(len(urls), 3)}: {url}")
            try:
                content = await jina.read(url)
                print(f"  内容长度: {len(content)} 字符")
            except Exception as e:
                print(f"  错误: {e}")
        
        await jina.close()
        print("\n✅ 模式2测试完成!")
        
    finally:
        await collector.close()


async def main():
    """主函数"""
    print("=" * 60)
    print("URL 收集模式测试")
    print("=" * 60)
    
    # 测试模式1
    await test_mode1_search()
    
    # 等待一下
    print("\n等待 5 秒...")
    await asyncio.sleep(5)
    
    # 测试模式2
    await test_mode2_library()
    
    print("\n" + "=" * 60)
    print("所有测试完成!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
