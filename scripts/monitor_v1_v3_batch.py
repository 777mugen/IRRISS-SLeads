"""
监控 Batch 任务并下载结果
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.llm.batch_client import ZhiPuBatchClient
from src.logging_config import get_logger


async def monitor_batches():
    """监控 batch 任务"""
    
    logger = get_logger()
    
    # 读取 batch 信息
    batch_info_file = project_root / "tmp/batch/batch_info_20260314_191929.json"
    with open(batch_info_file) as f:
        batch_info = json.load(f)
    
    v1_batch_id = batch_info['v1_batch_id']
    v3_batch_id = batch_info['v3_batch_id']
    
    print(f"\n{'='*60}")
    print(f"📊 监控 Batch 任务")
    print(f"{'='*60}\n")
    
    print(f"V1 Batch: {v1_batch_id}")
    print(f"V3 Batch: {v3_batch_id}\n")
    
    # 初始化客户端
    client = ZhiPuBatchClient()
    
    # 轮询状态
    while True:
        print(f"⏳ 检查状态... ({datetime.now().strftime('%H:%M:%S')})")
        
        # 检查 V1
        v1_status = await client.get_batch_status(v1_batch_id)
        print(f"  V1: {v1_status['status']}")
        
        # 检查 V3
        v3_status = await client.get_batch_status(v3_batch_id)
        print(f"  V3: {v3_status['status']}\n")
        
        # 如果都完成了，退出
        if v1_status['status'] == 'completed' and v3_status['status'] == 'completed':
            print(f"✅ 两个 Batch 都已完成！\n")
            
            # 下载结果
            print(f"📥 下载结果...")
            
            v1_output_file_id = v1_status.get('output_file_id')
            v3_output_file_id = v3_status.get('output_file_id')
            
            if v1_output_file_id:
                v1_result = await client.download_file(v1_output_file_id)
                v1_result_file = project_root / f"tmp/batch/v1_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
                v1_result_file.write_text(v1_result)
                print(f"✅ V1 结果已保存: {v1_result_file}")
            
            if v3_output_file_id:
                v3_result = await client.download_file(v3_output_file_id)
                v3_result_file = project_root / f"tmp/batch/v3_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
                v3_result_file.write_text(v3_result)
                print(f"✅ V3 结果已保存: {v3_result_file}")
            
            break
        
        # 等待 30 秒
        await asyncio.sleep(30)
    
    await client.close()
    
    print(f"\n{'='*60}")
    print(f"✅ 完成！")
    print(f"{'='*60}\n")
    
    print(f"下一步：")
    print(f"1. 打开原始论文（浏览器）")
    print(f"2. 对比 V1 和 V3 的提取结果")
    print(f"3. 检查准确性")


if __name__ == "__main__":
    asyncio.run(monitor_batches())
