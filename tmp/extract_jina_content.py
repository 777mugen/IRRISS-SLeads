"""
提取 Jina 原始 Markdown 内容
"""

import sys
import json
import re
from pathlib import Path

# 读取批处理输入文件
input_file = Path("tmp/batch/batch_20260313_201428.jsonl")

# 查找目标论文
target_doi = "10.21037/tcr-2025-1389"

with open(input_file, 'r') as f:
    for line in f:
        if target_doi in line:
            data = json.loads(line)
            user_content = data['body']['messages'][1]['content']
            
            # 输出到文件
            output_file = Path("tmp/jina_content.txt")
            with open(output_file, 'w') as f:
                f.write(user_content)
            
            print(f"✅ 已保存到 {output_file}")
            print(f"总长度: {len(user_content)} 字符")
            break
