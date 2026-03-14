"""
下载 V1, V2, V3 的提取结果
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.llm.batch_client import ZhiPuBatchClient


async def download_results():
    """下载所有结果"""
    
    client = ZhiPuBatchClient()
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    print(f"\n{'='*60}")
    print(f"📥 下载 Batch 结果")
    print(f"{'='*60}\n")
    
    # V1
    print(f"V1 (不截断+长)...")
    v1 = await client.get_batch('batch_2032780943455563776')
    print(f"  状态: {v1['status']}")
    if v1.get('output_file_id'):
        v1_file = project_root / f"tmp/batch/v1_result_{timestamp}.jsonl"
        await client.download_result(v1['output_file_id'], v1_file)
        print(f"  ✅ 已下载: {v1_file}")
    else:
        print(f"  ❌ 无 output_file_id")
    
    # V2
    print(f"\nV2 (截断+短)...")
    v2 = await client.get_batch('batch_2032783655034036224')
    print(f"  状态: {v2['status']}")
    if v2.get('output_file_id'):
        v2_file = project_root / f"tmp/batch/v2_result_{timestamp}.jsonl"
        await client.download_result(v2['output_file_id'], v2_file)
        print(f"  ✅ 已下载: {v2_file}")
    else:
        print(f"  ⏳ V2 还在处理中，请稍后重试")
    
    # V3
    print(f"\nV3 (截断+长)...")
    v3 = await client.get_batch('batch_2032780944905207808')
    print(f"  状态: {v3['status']}")
    if v3.get('output_file_id'):
        v3_file = project_root / f"tmp/batch/v3_result_{timestamp}.jsonl"
        await client.download_result(v3['output_file_id'], v3_file)
        print(f"  ✅ 已下载: {v3_file}")
    else:
        print(f"  ❌ 无 output_file_id")
    
    await client.close()
    
    print(f"\n{'='*60}")
    print(f"✅ 完成！")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    asyncio.run(download_results())
