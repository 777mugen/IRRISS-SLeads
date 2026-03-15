#!/usr/bin/env python3
"""查询批处理任务状态"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.llm.batch_client import ZhiPuBatchClient

async def check_batch(batch_id: str):
    async with ZhiPuBatchClient() as client:
        batch = await client.get_batch(batch_id)
        print(f"\n批处理任务: {batch_id}")
        print(f"状态: {batch.get('status')}")
        print(f"进度: {batch.get('completed', 0)}/{batch.get('total', 0)}")
        print(f"创建时间: {batch.get('created_at')}")
        
        if batch.get('error_file_id'):
            print(f"❌ 错误文件: {batch.get('error_file_id')}")
        
        if batch.get('output_file_id'):
            print(f"✅ 输出文件: {batch.get('output_file_id')}")
        
        # 打印完整响应（调试用）
        import json
        print("\n完整信息:")
        print(json.dumps(batch, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python scripts/check_batch.py <batch_id>")
        sys.exit(1)
    
    batch_id = sys.argv[1]
    asyncio.run(check_batch(batch_id))
