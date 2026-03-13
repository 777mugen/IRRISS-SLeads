"""
提交批处理任务 - 使用 Prompt v2
"""

import asyncio
from pathlib import Path
from src.llm.batch_client import ZhiPuBatchClient
from src.logging_config import get_logger


async def submit_batch_task():
    """提交批处理任务"""
    logger = get_logger()
    
    # 批处理文件路径
    batch_file = Path("tmp/batch_review/batch_2032279874147844096/09_input_prompt_v2.jsonl")
    
    if not batch_file.exists():
        logger.error(f"批处理文件不存在: {batch_file}")
        return
    
    logger.info(f"📝 批处理文件: {batch_file}")
    logger.info(f"📊 文件大小: {batch_file.stat().st_size / 1024:.1f} KB")
    
    # 上传并创建批处理任务
    async with ZhiPuBatchClient() as client:
        # 上传文件
        logger.info("\n📤 上传文件到智谱...")
        file_id = await client.upload_file(batch_file)
        logger.info(f"✅ 文件已上传: file_id={file_id}")
        
        # 创建批处理任务
        logger.info("\n🚀 创建批处理任务...")
        batch_id = await client.create_batch(
            input_file_id=file_id,
            metadata={
                "description": "Prompt v2 - 20 篇论文提取",
                "version": "v2",
                "papers": 20
            }
        )
        logger.info(f"✅ 批处理任务已创建: batch_id={batch_id}")
        
        # 获取初始状态
        batch_info = await client.get_batch(batch_id)
        logger.info(f"\n📊 任务状态:")
        logger.info(f"  - batch_id: {batch_id}")
        logger.info(f"  - status: {batch_info.get('status')}")
        logger.info(f"  - created_at: {batch_info.get('created_at')}")
        logger.info(f"  - request_counts: {batch_info.get('request_counts')}")
        
        logger.info(f"\n⏳ 预计处理时间: 30-40 分钟")
        logger.info(f"📝 监控命令: python -m src.monitoring.batch_monitor {batch_id}")
        
        return batch_id


if __name__ == "__main__":
    batch_id = asyncio.run(submit_batch_task())
    print(f"\n✅ 批处理任务已提交: {batch_id}")
