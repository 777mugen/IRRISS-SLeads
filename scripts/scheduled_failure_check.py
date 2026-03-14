"""
定时任务：检查失败论文并通知
每小时运行一次
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.processors.failure_analyzer import FailureAnalyzer
from scripts.feishu_notifier import FeishuNotifier
from src.logging_config import get_logger


async def check_and_notify():
    """
    检查失败论文并通知
    
    逻辑：
    1. 检查失败论文
    2. 如果有达到最大重试次数的论文，立即通知
    3. 否则，每日发送摘要
    """
    logger = get_logger()
    logger.info("="*80)
    logger.info("定时任务：检查失败论文")
    logger.info("="*80)
    
    try:
        # 1. 检查失败情况
        analyzer = FailureAnalyzer()
        retry_stats = await analyzer.check_retry_attempts()
        
        logger.info(f"重试统计: {retry_stats}")
        
        # 2. 初始化飞书通知器
        notifier = FeishuNotifier()
        
        # 3. 判断是否需要通知
        if retry_stats['needs_manual_review']:
            # 有需要人工复核的论文，立即发送详细报告
            logger.info("发现需要人工复核的论文，发送详细报告...")
            await notifier.notify_batch_failures()
        
        elif retry_stats['max_retry_count'] > 0:
            # 有失败但未达最大重试次数，发送摘要
            logger.info("有失败论文，发送每日摘要...")
            await notifier.send_daily_summary()
        
        else:
            # 没有失败论文
            logger.info("没有失败的论文，不发送通知")
        
        logger.info("✅ 定时任务完成")
        logger.info("="*80 + "\n")
    
    except Exception as e:
        logger.error(f"定时任务执行失败: {e}", exc_info=True)
        raise


async def main():
    """主函数"""
    await check_and_notify()


if __name__ == "__main__":
    asyncio.run(main())
