#!/usr/bin/env python3
"""
快速测试：只用 3 篇文章，快速对比
"""

import json
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from src.config import config
from src.prompts.batch_extraction import BATCH_EXTRACTION_PROMPT_V1

def get_test_papers(limit: int = 3):
    """获取测试文章"""
    db_url = config.database_url.replace('+asyncpg', '')
    engine = create_engine(db_url)
    
    with engine.connect() as conn:
        result = conn.execute(
            text("""
                SELECT doi, pmid, markdown_content 
                FROM raw_markdown 
                WHERE processing_status = 'completed' 
                LIMIT :limit
            """),
            {"limit": limit}
        )
        papers = result.fetchall()
    
    return papers

def build_files(papers, output_dir: Path):
    """构建对比文件"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    old_file = output_dir / f"old_{timestamp}.jsonl"
    new_file = output_dir / f"new_{timestamp}.jsonl"
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 限制内容长度，避免超长处理
    max_content_length = 50000  # 50k 字符
    
    # 旧方式
    with open(old_file, 'w', encoding='utf-8') as f:
        for doi, pmid, markdown in papers:
            # 限制长度
            content = markdown[:max_content_length] if len(markdown) > max_content_length else markdown
            
            user_content = BATCH_EXTRACTION_PROMPT_V1.replace("{markdown_content}", content)
            
            request = {
                "custom_id": f"old_{doi.replace('/', '_')}",
                "method": "POST",
                "url": "/v4/chat/completions",
                "body": {
                    "model": "glm-4-plus",
                    "messages": [
                        {"role": "system", "content": "你是一个专业的学术论文信息提取助手。严格按照规则提取，返回 JSON 格式。"},
                        {"role": "user", "content": user_content}
                    ],
                    "temperature": 0.1,
                    "max_tokens": 2048
                }
            }
            f.write(json.dumps(request, ensure_ascii=False) + '\n')
    
    # 新方式
    with open(new_file, 'w', encoding='utf-8') as f:
        for doi, pmid, markdown in papers:
            content = markdown[:max_content_length] if len(markdown) > max_content_length else markdown
            
            user_content = BATCH_EXTRACTION_PROMPT_V1.replace("{markdown_content}", content)
            
            request = {
                "custom_id": f"new_{doi.replace('/', '_')}",
                "method": "POST",
                "url": "/v4/chat/completions",
                "body": {
                    "model": "glm-4-plus",
                    "messages": [
                        {"role": "system", "content": "你是一个专业的学术论文信息提取助手。严格按照规则提取，返回 JSON 格式。"},
                        {"role": "user", "content": user_content}
                    ],
                    "temperature": 0.1,
                    "max_tokens": 2048,
                    "response_format": {"type": "json_object"}
                }
            }
            f.write(json.dumps(request, ensure_ascii=False) + '\n')
    
    return old_file, new_file

if __name__ == "__main__":
    print("=" * 60)
    print("快速对比测试（3篇文章）")
    print("=" * 60)
    
    papers = get_test_papers(limit=3)
    print(f"✅ 获取到 {len(papers)} 篇文章")
    
    output_dir = Path("tmp/quick_comparison")
    old_file, new_file = build_files(papers, output_dir)
    
    print(f"\n✅ 旧方式文件: {old_file}")
    print(f"✅ 新方式文件: {new_file}")
    
    # 检查文件大小
    old_size = old_file.stat().st_size / 1024
    new_size = new_file.stat().st_size / 1024
    print(f"\n文件大小:")
    print(f"  旧方式: {old_size:.1f} KB")
    print(f"  新方式: {new_size:.1f} KB")
    
    print("\n" + "=" * 60)
    print("文件已准备就绪，可以上传")
    print("=" * 60)
