"""
手动重试脚本
重试失败的批处理论文
"""

import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.processors.retry_manager import RetryManager
from src.pipeline_batch import BatchPipeline
from src.logging_config import get_logger


async def retry_failed_papers():
    """重试失败的论文"""
    logger = get_logger()
    
    print(f"\n{'='*80}")
    print(f"🔄 批处理失败重试")
    print(f"{'='*80}\n")
    
    # 1. 创建重试管理器
    retry_manager = RetryManager(max_retries=3)
    
    # 2. 获取统计信息
    stats = await retry_manager.get_retry_stats()
    
    print(f"当前状态:")
    print(f"  - 可重试: {stats['failed_no_retry']} 篇")
    print(f"  - 已达最大重试次数: {stats['failed_max_retries']} 篇")
    print(f"  - 总重试次数: {stats['total_retries']} 次\n")
    
    # 3. 检查是否有可重试的论文
    if stats['failed_no_retry'] == 0:
        print("✅ 没有可重试的论文\n")
        return
    
    # 4. 询问用户
    confirm = input(f"是否重试 {stats['failed_no_retry']} 篇失败论文? (y/n): ")
    
    if confirm.lower() != 'y':
        print("❌ 已取消\n")
        return
    
    # 5. 获取可重试的论文
    papers = await retry_manager.get_failed_papers(limit=50)
    
    print(f"\n找到 {len(papers)} 篇可重试论文:")
    for i, paper in enumerate(papers[:10], 1):
        print(f"  [{i}] {paper.doi}")
        print(f"      失败次数: {paper.retry_count}")
        print(f"      错误: {paper.error_message[:50] if paper.error_message else 'N/A'}")
    
    if len(papers) > 10:
        print(f"  ... 还有 {len(papers) - 10} 篇\n")
    
    # 6. 标记为待重试
    print(f"\n标记为待重试状态...")
    await retry_manager.mark_for_retry(papers)
    print(f"✅ 已标记 {len(papers)} 篇论文\n")
    
    # 7. 运行批处理
    print(f"开始批处理重试...\n")
    
    pipeline = BatchPipeline()
    
    result = await pipeline.run_batch_extraction(
        limit=len(papers),
        wait_for_completion=True,
        max_wait_minutes=60
    )
    
    # 8. 显示结果
    print(f"\n{'='*80}")
    print(f"📊 重试结果")
    print(f"{'='*80}\n")
    
    print(f"批处理 ID: {result['batch_id']}")
    print(f"总论文数: {result['total_papers']}")
    print(f"成功: {result['successful']}")
    print(f"失败: {result['failed']}\n")
    
    # 9. 获取最新统计
    new_stats = await retry_manager.get_retry_stats()
    
    print(f"最新状态:")
    print(f"  - 可重试: {new_stats['failed_no_retry']} 篇")
    print(f"  - 已达最大重试次数: {new_stats['failed_max_retries']} 篇\n")
    
    print(f"{'='*80}\n")


if __name__ == "__main__":
    asyncio.run(retry_failed_papers())
