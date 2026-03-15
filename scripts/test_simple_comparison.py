#!/usr/bin/env python3
"""
简化版对比测试脚本
使用同步SQLAlchemy避免greenlet问题
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from src.config import config
from src.prompts.batch_extraction import BATCH_EXTRACTION_PROMPT_V1

def get_test_papers(limit: int = 10):
    """获取测试文章（同步版本）"""
    # 将异步URL转换为同步URL（asyncpg -> psycopg2）
    db_url = config.database_url.replace("+asyncpg", "")
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

def build_comparison_files(papers, output_dir: Path):
    """构建对比文件"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    old_file = output_dir / f"old_style_{timestamp}.jsonl"
    new_file = output_dir / f"new_style_{timestamp}.jsonl"
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 旧方式（无 response_format）
    with open(old_file, 'w', encoding='utf-8') as f:
        for doi, pmid, markdown in papers:
            user_content = BATCH_EXTRACTION_PROMPT_V1.replace(
                "{markdown_content}",
                markdown
            )
            
            request = {
                "custom_id": f"old_doi_{doi.replace('/', '_')}",
                "method": "POST",
                "url": "/v4/chat/completions",
                "body": {
                    "model": "glm-4-plus",
                    "messages": [
                        {
                            "role": "system",
                            "content": "你是一个专业的学术论文信息提取助手。严格按照规则提取，返回 JSON 格式。"
                        },
                        {
                            "role": "user",
                            "content": user_content
                        }
                    ],
                    "temperature": 0.1,
                    "max_tokens": 4096
                }
            }
            f.write(json.dumps(request, ensure_ascii=False) + '\n')
    
    # 新方式（有 response_format）
    with open(new_file, 'w', encoding='utf-8') as f:
        for doi, pmid, markdown in papers:
            user_content = BATCH_EXTRACTION_PROMPT_V1.replace(
                "{markdown_content}",
                markdown
            )
            
            request = {
                "custom_id": f"new_doi_{doi.replace('/', '_')}",
                "method": "POST",
                "url": "/v4/chat/completions",
                "body": {
                    "model": "glm-4-plus",
                    "messages": [
                        {
                            "role": "system",
                            "content": "你是一个专业的学术论文信息提取助手。严格按照规则提取，返回 JSON 格式。"
                        },
                        {
                            "role": "user",
                            "content": user_content
                        }
                    ],
                    "temperature": 0.1,
                    "max_tokens": 4096,
                    "response_format": {"type": "json_object"}  # ✅ 官方结构化输出
                }
            }
            f.write(json.dumps(request, ensure_ascii=False) + '\n')
    
    return old_file, new_file

if __name__ == "__main__":
    print("=" * 60)
    print("Step 1: 从数据库获取 10 篇测试文章")
    print("=" * 60)
    
    papers = get_test_papers(limit=10)
    
    if not papers:
        print("❌ 没有找到待处理的文章！")
        sys.exit(1)
    
    print(f"✅ 获取到 {len(papers)} 篇文章")
    
    print("\n" + "=" * 60)
    print("Step 2: 构建批处理文件")
    print("=" * 60)
    
    output_dir = Path("tmp/comparison_test")
    old_file, new_file = build_comparison_files(papers, output_dir)
    
    print(f"✅ 旧方式批处理文件: {old_file}")
    print(f"✅ 新方式批处理文件: {new_file}")
    
    print("\n" + "=" * 60)
    print("Step 3: 上传并执行批处理任务")
    print("=" * 60)
    
    print("\n请运行以下命令上传并执行批处理：")
    print(f"""
# 旧方式
source .venv/bin/activate
python -m src.llm.batch_client --upload {old_file}

# 新方式
python -m src.llm.batch_client --upload {new_file}
""")
    
    print("\n" + "=" * 60)
    print("✅ 准备完成！")
    print("=" * 60)
