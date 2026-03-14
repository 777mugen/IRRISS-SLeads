"""
50 篇论文批量提取（V1 策略：不截断 + 长 Prompt）
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.crawlers.jina_client import JinaClient
from src.llm.batch_client import ZhiPuBatchClient
from src.prompts.batch_extraction import BATCH_EXTRACTION_PROMPT_V2


async def create_batch_for_50_papers():
    """创建 50 篇论文的批处理任务"""

    # 读取 DOI 列表
    doi_file = project_root / "tmp/test_set_50papers_20260314_210207.txt"
    with open(doi_file) as f:
        dois = [line.strip() for line in f if line.strip()]

    print(f"\n{'='*80}")
    print(f"🚀 50 篇论文批量提取（V1 策略）")
    print(f"{'='*80}\n")

    print(f"DOI 数量: {len(dois)}\n")

    # 初始化客户端
    jina_client = JinaClient()
    batch_client = ZhiPuBatchClient()

    # 准备批处理任务
    tasks = []
    stats = {
        'total': len(dois),
        'success': 0,
        'failed': 0,
        'errors': []
    }

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    for i, doi in enumerate(dois, 1):
        print(f"[{i}/{len(dois)}] 处理 DOI: {doi}")

        try:
            # Step 1: 使用 Jina Reader 获取论文内容（V1: 不截断）
            content = await jina_client.read_paper(f"https://doi.org/{doi}")

            if not content or len(content) < 100:
                print(f"  ❌ 内容过短或为空")
                stats['failed'] += 1
                stats['errors'].append({'doi': doi, 'error': 'content_too_short'})
                continue

            print(f"  ✅ 获取成功: {len(content)} 字符")

            # Step 2: 准备批处理任务（V1: 长 Prompt）
            task = {
                "custom_id": f"doi_{doi.replace('/', '_').replace('.', '_')}",
                "method": "POST",
                "url": "/v4/chat/completions",
                "body": {
                    "model": "glm-4-plus",
                    "messages": [
                        {
                            "role": "system",
                            "content": "你是一个专业的学术论文信息提取助手。"
                        },
                        {
                            "role": "user",
                            "content": BATCH_EXTRACTION_PROMPT_V2.replace(
                                "{markdown_content}",
                                content
                            )
                        }
                    ],
                    "temperature": 0.1
                }
            }

            tasks.append(task)
            stats['success'] += 1

        except Exception as e:
            print(f"  ❌ 失败: {e}")
            stats['failed'] += 1
            stats['errors'].append({'doi': doi, 'error': str(e)})

    print(f"\n{'='*80}")
    print(f"📊 统计")
    print(f"{'='*80}\n")
    print(f"成功: {stats['success']}/{stats['total']}")
    print(f"失败: {stats['failed']}/{stats['total']}\n")

    # 保存批处理文件
    batch_file = project_root / f"tmp/batch/v1_50papers_{timestamp}.jsonl"
    batch_file.parent.mkdir(parents=True, exist_ok=True)

    with open(batch_file, 'w') as f:
        for task in tasks:
            f.write(json.dumps(task, ensure_ascii=False) + '\n')

    print(f"✅ 批处理文件: {batch_file}\n")

    # 上传到智谱
    print(f"📤 上传到智谱 Batch API...")
    file_id = await batch_client.upload_file(batch_file)
    print(f"✅ File ID: {file_id}\n")

    # 创建批处理任务
    print(f"🚀 创建批处理任务...")
    batch_id = await batch_client.create_batch(file_id)
    print(f"✅ Batch ID: {batch_id}\n")

    # 保存批处理信息
    batch_info = {
        'timestamp': timestamp,
        'batch_id': batch_id,
        'file_id': file_id,
        'total_papers': stats['total'],
        'success': stats['success'],
        'failed': stats['failed'],
        'errors': stats['errors'],
        'strategy': 'V1 (不截断 + 长 Prompt)',
    }

    info_file = project_root / f"tmp/batch/batch_info_50papers_{timestamp}.json"
    with open(info_file, 'w') as f:
        json.dump(batch_info, f, indent=2, ensure_ascii=False)

    print(f"{'='*80}")
    print(f"✅ 批处理任务创建完成！")
    print(f"{'='*80}\n")
    print(f"Batch ID: {batch_id}")
    print(f"文件: {info_file}")
    print(f"状态: 等待处理（预计 10-30 分钟）\n")

    await jina_client.close()
    await batch_client.close()

    return batch_id


if __name__ == "__main__":
    asyncio.run(create_batch_for_50_papers())
