#!/usr/bin/env python3
"""
上传并执行批处理任务
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.llm.batch_client import ZhiPuBatchClient
from src.logging_config import get_logger

async def upload_and_process(file_path: Path, label: str):
    """上传并处理批处理文件"""
    logger = get_logger()
    
    async with ZhiPuBatchClient() as client:
        # 上传文件
        logger.info(f"上传文件: {file_path}")
        file_id = await client.upload_file(file_path)
        logger.info(f"✅ 文件已上传: file_id={file_id}")
        
        # 创建批处理任务
        batch_id = await client.create_batch(file_id)
        logger.info(f"✅ 批处理任务已创建: {label} - batch_id={batch_id}")
        
        # 等待完成
        logger.info(f"⏳ 等待批处理完成...")
        batch = await client.wait_for_completion(
            batch_id,
            poll_interval=30,
            max_wait=3600
        )
        
        # 下载结果
        output_file_id = batch.get('output_file_id')
        if not output_file_id:
            logger.error("批处理任务完成但没有输出文件")
            return None
        
        output_path = Path(f"tmp/comparison_test/results_{label}_{batch_id}.jsonl")
        await client.download_result(output_file_id, output_path)
        logger.info(f"✅ 结果已下载: {output_path}")
        
        return output_path

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python scripts/upload_batch.py <label> <file_path>")
        print("示例: python scripts/upload_batch.py old tmp/comparison_test/old_style.jsonl")
        sys.exit(1)
    
    label = sys.argv[1]
    file_path = Path(sys.argv[2])
    
    if not file_path.exists():
        print(f"❌ 文件不存在: {file_path}")
        sys.exit(1)
    
    asyncio.run(upload_and_process(file_path, label))
