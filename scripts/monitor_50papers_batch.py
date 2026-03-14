"""
自动监控 50 篇论文批处理任务
每 30 分钟检查一次状态
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
import json

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.llm.batch_client import ZhiPuBatchClient


BATCH_ID = "batch_2032808049382653952"
TOTAL_PAPERS = 48
CHECK_INTERVAL = 1800  # 30 分钟（秒）


async def monitor_batch():
    """监控批处理任务"""

    client = ZhiPuBatchClient()

    print(f"\n{'='*80}")
    print(f"📊 50 篇论文批处理任务监控")
    print(f"{'='*80}\n")

    print(f"Batch ID: {BATCH_ID}")
    print(f"论文数量: {TOTAL_PAPERS} 篇")
    print(f"策略: V1 (不截断 + 长 Prompt)")
    print(f"检查间隔: 每 {CHECK_INTERVAL // 60} 分钟\n")

    check_count = 0
    max_checks = 10  # 最多检查 10 次（5 小时）

    while check_count < max_checks:
        check_count += 1

        print(f"\n{'='*80}")
        print(f"🔍 检查 #{check_count}/{max_checks} @ {datetime.now().strftime('%H:%M')}")
        print(f"{'='*80}\n")

        # 获取批处理状态
        batch = await client.get_batch(BATCH_ID)
        status = batch['status']

        print(f"状态: {status}")
        print(f"已处理: {batch.get('request_counts', {}).get('completed', 0)}/{TOTAL_PAPERS}")

        if status == 'completed':
            print(f"\n✅ 批处理完成！\n")

            # 下载结果
            if batch.get('output_file_id'):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_file = project_root / f"tmp/batch/v1_50papers_{timestamp}.jsonl"
                await client.download_result(batch['output_file_id'], output_file)
                print(f"✅ 结果已下载: {output_file}\n")

            # 解析结果
                results = []
                with open(output_file) as f:
                    for line in f:
                        results.append(json.loads(line))

                # 生成报告
                report = {
                    'timestamp': timestamp,
                    'total_papers': TOTAL_PAPERS,
                    'completed': len(results),
                    'success_rate': f"{len(results)}/{TOTAL_PAPERS:.1%}",
                    'batch_id': BATCH_ID,
                    'results': results[:5],  # 只保存前5个作为示例
                }

                report_file = project_root / f"tmp/batch/50papers_monitor_{timestamp}.json"
                with open(report_file,
'w') as f:
                    json.dump(report, f, indent=2)

                print(f"📄 监控报告: {report_file}\n")

            break

        elif status == 'failed':
            print(f"\n❌ 批处理失败！\n")
            print(f"错误信息: {batch.get('errors')}\n")
            break

        else:
            # 等待下一次检查
            print(f"\n⏳ 等待 {CHECK_INTERVAL // 60} 分钟后再次检查...\n")
            await asyncio.sleep(CHECK_INTERVAL)

    await client.close()

    print(f"\n{'='*80}")
    print(f"✅ 监控结束")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    asyncio.run(monitor_batch())
