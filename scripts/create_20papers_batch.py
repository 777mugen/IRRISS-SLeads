"""
创建 20 篇论文的 V1 vs V3 batch 任务
只关注准确性
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.crawlers.jina_client import JinaClient
from src.processors.content_truncator import ContentTruncator
from src.llm.batch_client import ZhiPuBatchClient
from src.logging_config import get_logger


# 20 篇论文（从之前的 batch 结果中获取）
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
    "10.1186/s13058-026-02251-6",
    "10.21037/tcr-2025-1389",
    "10.21037/tcr-2025-1-2580",
    "10.21037/tcr-2025-aw-2287",
    "10.32604/or.2026.071122",
    "10.1158/2159-8290.CD-25-1907",
]


async def create_20_paper_batch():
    """创建 20 篇论文的 batch 任务"""
    
    logger = get_logger()
    
    print(f"\n{'='*60}")
    print(f"🚀 创建 20 篇论文的 Batch 任务")
    print(f"{'='*60}\n")
    
    # 初始化
    jina_client = JinaClient()
    truncator = ContentTruncator()
    batch_client = ZhiPuBatchClient()
    
    # 加载 Prompt
    prompt_file = project_root / "docs/Batch Prompt v2.md"
    prompt = prompt_file.read_text()
    
    # 准备数据
    v1_tasks = []
    v3_tasks = []
    
    for i, doi in enumerate(TEST_DOIS, 1):
        print(f"[{i}/20] 处理 DOI: {doi}")
        
        try:
            # 爬取内容
            doi_url = f"https://doi.org/{doi}"
            original_content = await jina_client.read_paper(doi_url)
            
            # V1: 不截断
            v1_content = original_content
            v1_tasks.append({
                'custom_id': f'doi_{doi.replace("/", "_")}',
                'content': v1_content
            })
            
            # V3: 截断
            v3_content = truncator.extract_metadata_section(original_content)
            v3_tasks.append({
                'custom_id': f'doi_{doi.replace("/", "_")}',
                'content': v3_content
            })
            
            print(f"  ✅ V1: {len(v1_content):,} | V3: {len(v3_content):,}\n")
            
        except Exception as e:
            print(f"  ❌ 失败: {e}\n")
            continue
    
    print(f"\n{'='*60}")
    print(f"📊 统计")
    print(f"{'='*60}\n")
    print(f"成功: {len(v1_tasks)}/20 篇")
    
    # 创建 Batch 文件
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # V1 Batch 文件
    v1_file = project_root / f"tmp/batch/v1_20papers_{timestamp}.jsonl"
    v1_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(v1_file, 'w') as f:
        for task in v1_tasks:
            batch_item = {
                "custom_id": task['custom_id'],
                "method": "POST",
                "url": "/v4/chat/completions",
                "body": {
                    "model": "glm-4-plus",
                    "messages": [
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": task['content']}
                    ]
                }
            }
            f.write(json.dumps(batch_item, ensure_ascii=False) + '\n')
    
    print(f"\n✅ V1 Batch 文件: {v1_file}")
    
    # V3 Batch 文件
    v3_file = project_root / f"tmp/batch/v3_20papers_{timestamp}.jsonl"
    
    with open(v3_file, 'w') as f:
        for task in v3_tasks:
            batch_item = {
                "custom_id": task['custom_id'],
                "method": "POST",
                "url": "/v4/chat/completions",
                "body": {
                    "model": "glm-4-plus",
                    "messages": [
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": task['content']}
                    ]
                }
            }
            f.write(json.dumps(batch_item, ensure_ascii=False) + '\n')
    
    print(f"✅ V3 Batch 文件: {v3_file}")
    
    # 上传到智谱
    print(f"\n📤 上传到智谱 Batch API...\n")
    
    # 上传 V1 文件
    v1_file_id = await batch_client.upload_file(v1_file)
    print(f"✅ V1 File ID: {v1_file_id}")
    
    # 创建 V1 Batch
    v1_batch_id = await batch_client.create_batch(v1_file_id, metadata={'version': 'v1', 'papers': '20'})
    print(f"✅ V1 Batch ID: {v1_batch_id}")
    
    # 上传 V3 文件
    v3_file_id = await batch_client.upload_file(v3_file)
    print(f"✅ V3 File ID: {v3_file_id}")
    
    # 创建 V3 Batch
    v3_batch_id = await batch_client.create_batch(v3_file_id, metadata={'version': 'v3', 'papers': '20'})
    print(f"✅ V3 Batch ID: {v3_batch_id}")
    
    # 保存 Batch ID
    batch_info = {
        'timestamp': timestamp,
        'v1_batch_id': v1_batch_id,
        'v3_batch_id': v3_batch_id,
        'test_dois': TEST_DOIS,
        'v1_file': str(v1_file),
        'v3_file': str(v3_file),
        'v1_file_id': v1_file_id,
        'v3_file_id': v3_file_id,
    }
    
    info_file = project_root / f"tmp/batch/batch_info_20papers_{timestamp}.json"
    with open(info_file, 'w') as f:
        json.dump(batch_info, f, indent=2, ensure_ascii=False)
    
    print(f"\n📄 Batch 信息: {info_file}")
    print(f"\n⏳ 等待 Batch 完成（约 10-15 分钟）...")
    print(f"   V1: {v1_batch_id}")
    print(f"   V3: {v3_batch_id}")
    
    await jina_client.close()
    await batch_client.close()
    
    return batch_info


if __name__ == "__main__":
    asyncio.run(create_20_paper_batch())
