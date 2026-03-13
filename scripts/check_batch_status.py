"""
检查批处理任务状态
"""

import asyncio
from src.llm.batch_client import ZhiPuBatchClient
from src.logging_config import get_logger


async def check_batch_status():
    """检查批处理任务状态"""
    logger = get_logger()
    
    batch_id = "batch_2032437832023674880"
    
    async with ZhiPuBatchClient() as client:
        batch = await client.get_batch(batch_id)
        
        status = batch.get('status')
        total = batch.get('request_counts', {}).get('total', 0)
        completed = batch.get('request_counts', {}).get('completed', 0)
        failed = batch.get('request_counts', {}).get('failed', 0)
        
        print(f"\n{'='*60}")
        print(f"📊 批处理任务状态")
        print(f"{'='*60}")
        print(f"  批次 ID: {batch_id}")
        print(f"  状态: {status}")
        print(f"  总数: {total}")
        print(f"  完成: {completed}")
        print(f"  失败: {failed}")
        print(f"  进度: {completed}/{total} ({completed/total*100:.1f}%)")
        print(f"  创建时间: {batch.get('created_at')}")
        
        if status == 'completed':
            print(f"\n✅ 任务已完成！")
            print(f"  输出文件: {batch.get('output_file_id')}")
            if batch.get('error_file_id'):
                print(f"  错误文件: {batch.get('error_file_id')}")
        elif status == 'in_progress':
            print(f"\n⏳ 任务处理中...")
            elapsed = (asyncio.get_event_loop().time() - batch.get('created_at', 0) / 1000) / 60
            print(f"  已运行: {elapsed:.1f} 分钟")
            print(f"  预计还需: {max(0, 30 - elapsed):.1f} 分钟")
        elif status == 'validating':
            print(f"\n🔍 任务验证中...")
        elif status == 'failed':
            print(f"\n❌ 任务失败！")
            print(f"  错误文件: {batch.get('error_file_id')}")
        
        print(f"{'='*60}\n")


if __name__ == "__main__":
    asyncio.run(check_batch_status())
