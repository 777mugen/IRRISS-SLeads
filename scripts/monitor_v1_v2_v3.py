"""
监控 V1, V2, V3 三个 Batch 任务
"""

import asyncio
import json
from pathlib import Path
from datetime import datetime

import sys
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.llm.batch_client import ZhiPuBatchClient


async def monitor_all():
    """监控三个 batch 任务"""
    
    # Batch IDs
    v1_batch_id = "batch_2032780943455563776"
    v2_batch_id = "batch_2032783655034036224"
    v3_batch_id = "batch_2032780944905207808"
    
    print(f"\n{'='*60}")
    print(f"📊 监控 V1, V2, V3 Batch 任务")
    print(f"{'='*60}\n")
    
    print(f"V1 (不截断+长): {v1_batch_id}")
    print(f"V2 (截断+短): {v2_batch_id}")
    print(f"V3 (截断+长): {v3_batch_id}\n")
    
    client = ZhiPuBatchClient()
    
    # 轮询检查
    while True:
        print(f"\n⏳ 检查状态... ({datetime.now().strftime('%H:%M:%S')})")
        
        # 检查 V1
        v1 = await client.get_batch_status(v1_batch_id)
        print(f"  V1: {v1['status']}")
        
        # 检查 V2
        v2 = await client.get_batch_status(v2_batch_id)
        print(f"  V2: {v2['status']}")
        
        # 检查 V3
        v3 = await client.get_batch_status(v3_batch_id)
        print(f"  V3: {v3['status']}")
        
        # 如果都完成，下载结果
        if all([v['status'] == 'completed' for v in [v1, v2, v3]]):
            print(f"\n✅ 所有 Batch 都已完成！\n")
            
            # 下载结果
            results = {
                'v1': await client.download_file(v1['output_file_id']) if v1.get('output_file_id') else None,
                'v2': await client.download_file(v2['output_file_id']) if v2.get('output_file_id') else None,
                'v3': await client.download_file(v3['output_file_id']) if v3.get('output_file_id') else None,
            }
            
            # 保存结果
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            for version, result in results.items():
                if result:
                    file = project_root / f"tmp/batch/{version}_result_{timestamp}.jsonl"
                    file.write_text(result)
                    print(f"✅ {version.upper()} 结果: {file}")
            
            break
        
        # 等待 30 秒
        await asyncio.sleep(30)
    
    await client.close()
    
    print(f"\n{'='*60}")
    print(f"✅ 完成！")
    print(f"{'='*60}\n")
    
    print(f"下一步：对比 V1, V2, V3 的提取准确性")


if __name__ == "__main__":
    asyncio.run(monitor_all())
