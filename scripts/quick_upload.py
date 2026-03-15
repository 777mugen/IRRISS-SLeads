#!/usr/bin/env python3
"""
快速上传并监控（简化版）
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.llm.batch_client import ZhiPuBatchClient
from src.logging_config import get_logger


async def quick_test(file_path: Path, label: str):
    """快速测试"""
    logger = get_logger()
    
    async with ZhiPuBatchClient() as client:
        # 上传
        logger.info(f"\n{'=' * 60}")
        logger.info(f"{label}: 上传文件")
        logger.info(f"{'=' * 60}")
        
        file_id = await client.upload_file(file_path)
        logger.info(f"✅ 文件已上传: {file_id}")
        
        # 创建批处理
        batch_id = await client.create_batch(file_id)
        logger.info(f"✅ 批处理已创建: {batch_id}")
        
        # 等待完成（更快轮询）
        logger.info(f"⏳ 等待完成（每30秒检查）...")
        
        for i in range(60):  # 最多等待30分钟
            await asyncio.sleep(30)
            batch = await client.get_batch(batch_id)
            status = batch.get('status')
            completed = batch.get('request_counts', {}).get('completed', 0)
            total = batch.get('request_counts', {}).get('total', 0)
            
            logger.info(f"  [{i+1}] 状态: {status}, 进度: {completed}/{total}")
            
            if status == "completed":
                # 下载结果
                output_file_id = batch.get('output_file_id')
                if output_file_id:
                    timestamp = datetime.now().strftime("%H%M%S")
                    output_path = Path(f"tmp/quick_comparison/results_{label}_{timestamp}.jsonl")
                    await client.download_result(output_file_id, output_path)
                    logger.info(f"✅ {label} 完成！结果: {output_path}")
                    return output_path
                else:
                    logger.error(f"❌ {label} 没有输出文件")
                    return None
            elif status in ["failed", "expired", "cancelled"]:
                logger.error(f"❌ {label} 失败: {status}")
                return None
        
        logger.error(f"❌ {label} 超时")
        return None


async def main():
    logger = get_logger()
    
    # 找到最新文件
    quick_dir = Path("tmp/quick_comparison")
    old_files = sorted(quick_dir.glob("old_*.jsonl"), reverse=True)
    new_files = sorted(quick_dir.glob("new_*.jsonl"), reverse=True)
    
    if not old_files or not new_files:
        logger.error("找不到测试文件")
        return
    
    old_file = old_files[0]
    new_file = new_files[0]
    
    logger.info(f"使用文件:")
    logger.info(f"  旧方式: {old_file}")
    logger.info(f"  新方式: {new_file}")
    
    # 并发执行
    results = await asyncio.gather(
        quick_test(old_file, "旧方式"),
        quick_test(new_file, "新方式")
    )
    
    old_result, new_result = results
    
    if old_result and new_result:
        logger.info(f"\n{'=' * 60}")
        logger.info("✅ 两个任务都完成了！")
        logger.info(f"{'=' * 60}")
        logger.info(f"旧方式结果: {old_result}")
        logger.info(f"新方式结果: {new_result}")
        
        # 快速分析
        analyze_quick(old_result, new_result)


def analyze_quick(old_file: Path, new_file: Path):
    """快速分析"""
    logger = get_logger()
    
    logger.info(f"\n{'=' * 60}")
    logger.info("快速分析")
    logger.info(f"{'=' * 60}")
    
    old_success = 0
    new_success = 0
    total = 0
    
    with open(old_file, 'r') as f:
        for line in f:
            data = json.loads(line)
            total += 1
            try:
                content = data['response']['body']['choices'][0]['message']['content']
                json.loads(content)
                old_success += 1
            except:
                pass
    
    with open(new_file, 'r') as f:
        for line in f:
            data = json.loads(line)
            try:
                content = data['response']['body']['choices'][0]['message']['content']
                json.loads(content)
                new_success += 1
            except:
                pass
    
    logger.info(f"总文章数: {total}")
    logger.info(f"旧方式: {old_success}/{total} ({old_success/total*100:.0f}%)")
    logger.info(f"新方式: {new_success}/{total} ({new_success/total*100:.0f}%)")
    logger.info(f"改进: {(new_success-old_success)/total*100:+.0f}%")


if __name__ == "__main__":
    asyncio.run(main())
