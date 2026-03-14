"""
提交 48 篇论文批处理任务（V1 策略）
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.llm.batch_client import ZhiPuBatchClient


async def submit_batch():
    """提交批处理任务"""

    client = ZhiPuBatchClient()

    timestamp = "20260314_210521"

    print(f"\n{'='*80}")
    print(f"📤 提交 48 篇论文批处理任务")
    print(f"{'='*80}\n")

    # 上传文件
    batch_file = project_root / f"tmp/batch/v1_50papers_20260314_210521_upload.jsonl"
    print(f"文件: {batch_file}")
    print(f"大小: {batch_file.stat().st_size / 1024 / 1024:.1f} MB\n")

    print(f"📤 上传到智谱 Batch API...")
    file_id = await client.upload_file(batch_file)
    print(f"✅ File ID: {file_id}\n")

    # 创建批处理任务
    print(f"🚀 创建批处理任务...")
    batch_id = await client.create_batch(file_id)
    print(f"✅ Batch ID: {batch_id}\n")

    # 保存批处理信息
    batch_info = {
        'timestamp': timestamp,
        'batch_id': batch_id,
        'file_id': file_id,
        'total_papers': 48,
        'strategy': 'V1 (不截断 + 长 Prompt)',
        'created_at': datetime.now().isoformat(),
    }

    info_file = project_root / f"tmp/batch/batch_info_50papers_{timestamp}.json"
    with open(info_file, 'w') as f:
        import json
        json.dump(batch_info, f, indent=2)

    print(f"{'='*80}")
    print(f"✅ 批处理任务已提交！")
    print(f"{'='*80}\n")
    print(f"Batch ID: {batch_id}")
    print(f"文件: {info_file}")
    print(f"状态: 等待处理（预计 10-30 分钟）\n")

    await client.close()

    return batch_id


if __name__ == "__main__":
    asyncio.run(submit_batch())
