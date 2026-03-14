"""
等待 V2 完成并下载结果
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.llm.batch_client import ZhiPuBatchClient


async def wait_for_v2():
    """等待 V2 完成"""
    
    client = ZhiPuBatchClient()
    v2_batch_id = 'batch_2032783655034036224'
    
    print(f"\n{'='*60}")
    print(f"⏳ 等待 V2 完成")
    print(f"{'='*60}\n")
    
    max_wait = 60  # 最多等待 60 分钟
    interval = 30  # 每 30 秒检查一次
    
    for i in range(max_wait // interval):
        v2 = await client.get_batch(v2_batch_id)
        status = v2['status']
        
        print(f"[{i+1}] V2 状态: {status}")
        
        if status == 'completed':
            print(f"\n✅ V2 完成！")
            
            # 下载结果
            if v2.get('output_file_id'):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_file = project_root / f"tmp/batch/v2_result_{timestamp}.jsonl"
                await client.download_result(v2['output_file_id'], output_file)
                print(f"✅ V2 结果已下载: {output_file}")
                break
        elif status == 'failed':
            print(f"\n❌ V2 失败！")
            break
        else:
            print(f"   等待 {interval} 秒后重试...")
            await asyncio.sleep(interval)
    else:
        print(f"\n⏰ 超时！V2 在 {max_wait} 分钟内未完成")
    
    await client.close()


if __name__ == "__main__":
    asyncio.run(wait_for_v2())
