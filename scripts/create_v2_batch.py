"""
创建 V2 batch 任务（截断 + 精简 Prompt）
使用 feature/metadata-extraction-v2 分支的精简 Prompt
"""

import asyncio
import json
import sys
import subprocess
from pathlib import Path
from datetime import datetime

# 添加项目根目录
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.crawlers.jina_client import JinaClient
from src.processors.content_truncator import ContentTruncator
from src.llm.batch_client import ZhiPuBatchClient
from src.logging_config import get_logger


# 19 篇成功的论文（排除失败的 1 篇）
TEST_DOIS = [
    "10.1021/acs.jmedchem.5c03498",
    "10.3389/fonc.2026.1728876",
    "10.1097/CM9.0000000000004035",
    "10.1021/jacsau.5c01509",
    "10.3389/fcimb.2026.1747682",
    "10.7150/thno.124789",
    "10.1136/jitc-2025-014040",
    "10.3748/wjg.v32.i9.115259",
    "10.2196/86322",
    "10.1038/s41556-026-01907-x",
    "10.4103/bc.bc_65_24",
    "10.21037/jgo-2025-750",
    "10.1007/s43630-026-00863-7",
    "10.1158/0008-5472.CAN-25-3806",
    # "10.1186/s13058-026-02251-6",  # 失败
    "10.21037/tcr-2025-1389",
    "10.21037/tcr-2025-1-2580",
    "10.21037/tcr-2025-aw-2287",
    "10.32604/or.2026.071122",
    "10.1158/2159-8290.CD-25-1907",
]


async def create_v2_batch():
    """创建 V2 batch 任务"""
    
    logger = get_logger()
    
    print(f"\n{'='*60}")
    print(f"🚀 创建 V2 Batch 任务（截断 + 精简 Prompt）")
    print(f"{'='*60}\n")
    
    # 从 V1/V3 batch 文件中读取内容（避免重复爬取）
    v3_batch_file = project_root / "tmp/batch/v3_20papers_20260314_192837.jsonl"
    
    if not v3_batch_file.exists():
        print(f"❌ V3 batch 文件不存在: {v3_batch_file}")
        return
    
    # 获取 V2 的精简 Prompt
    prompt_v2_file = Path("/tmp/prompt_v2.md")
    if not prompt_v2_file.exists():
        # 从 git 提取
        subprocess.run([
            "git", "show", 
            "feature/metadata-extraction-v2:docs/Batch Prompt v3 (Simplified).md"
        ], stdout=open(prompt_v2_file, 'w'), check=True)
    
    prompt_v2 = prompt_v2_file.read_text()
    print(f"✅ V2 Prompt 长度: {len(prompt_v2):,} 字符\n")
    
    # 读取 V3 batch 文件（已经截断的内容）
    v3_tasks = []
    with open(v3_batch_file) as f:
        for line in f:
            task = json.loads(line)
            v3_tasks.append(task)
    
    print(f"✅ 读取到 {len(v3_tasks)} 个任务\n")
    
    # 创建 V2 batch 文件（使用截断的内容 + 精简 Prompt）
    v2_tasks = []
    for task in v3_tasks:
        # V3 的 content 已经是截断后的内容
        content = task['body']['messages'][1]['content']
        custom_id = task['custom_id']
        
        v2_task = {
            "custom_id": custom_id,
            "method": "POST",
            "url": "/v4/chat/completions",
            "body": {
                "model": "glm-4-plus",
                "messages": [
                    {"role": "system", "content": prompt_v2},
                    {"role": "user", "content": content}
                ]
            }
        }
        v2_tasks.append(v2_task)
    
    # 保存 V2 batch 文件
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    v2_file = project_root / f"tmp/batch/v2_19papers_{timestamp}.jsonl"
    v2_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(v2_file, 'w') as f:
        for task in v2_tasks:
            f.write(json.dumps(task, ensure_ascii=False) + '\n')
    
    print(f"✅ V2 Batch 文件: {v2_file}\n")
    
    # 上传到智谱
    print(f"📤 上传到智谱 Batch API...\n")
    
    batch_client = ZhiPuBatchClient()
    
    v2_file_id = await batch_client.upload_file(v2_file)
    print(f"✅ V2 File ID: {v2_file_id}")
    
    v2_batch_id = await batch_client.create_batch(
        v2_file_id, 
        metadata={'version': 'v2', 'papers': '19'}
    )
    print(f"✅ V2 Batch ID: {v2_batch_id}")
    
    # 保存 Batch 信息
    batch_info = {
        'timestamp': timestamp,
        'v2_batch_id': v2_batch_id,
        'v2_file_id': v2_file_id,
        'v2_file': str(v2_file),
        'test_dois': TEST_DOIS,
    }
    
    info_file = project_root / f"tmp/batch/batch_info_v2_{timestamp}.json"
    with open(info_file, 'w') as f:
        json.dump(batch_info, f, indent=2, ensure_ascii=False)
    
    print(f"\n📄 Batch 信息: {info_file}")
    print(f"\n✅ V2 Batch 创建完成！")
    print(f"   V2 Batch ID: {v2_batch_id}")
    
    await batch_client.close()


if __name__ == "__main__":
    asyncio.run(create_v2_batch())
