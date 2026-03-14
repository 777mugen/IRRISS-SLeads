"""
浏览器验证脚本：逐一打开论文并记录误差
"""

import json
from pathlib import Path
from datetime import datetime

# 读取 V1 结果
with open('tmp/batch/v1_results_summary.json') as f:
    v1_results = json.load(f)

# 验证记录模板
verification_template = {
    'doi': '',
    'v1_extraction': {
        'author': '',
        'email': '',
    },
    'browser_verification': {
        'author': '',
        'email': '',
        'source': '',  # 在哪里找到的（作者列表、脚注、文末等）
    },
    'errors': [],  # 误差列表
}

# 选择前 5 篇进行验证
test_dois = [
    '10.1158/0008-5472.CAN-25-3806',
    '10.21037/tcr-2025-aw-2287',
    '10.1007/s43630-026-00863-7',
    '10.21037/jgo-2025-750',
    '10.3389/fcimb.2026.1747682',
]

print(f"\n{'='*80}")
print(f"🔍 浏览器验证：前 5 篇论文")
print(f"{'='*80}\n")

verifications = []

for doi in test_dois:
    # 查找对应的 V1 结果
    v1_data = next((r for r in v1_results if r['doi'] == doi), None)

    if not v1_data:
        print(f"❌ {doi}: 无 V1 结果")
        continue

    print(f"📄 {doi}")
    print(f"   V1 提取:")
    print(f"     作者: {v1_data.get('author')}")
    print(f"     邮箱: {v1_data.get('email')}")
    print(f"   👉 请浏览器打开: https://doi.org/{doi}")
    print(f"   👉 查看实际通讯作者和邮箱")
    print()

print(f"\n{'='*80}")
print(f"📋 等待人工验证...")
print(f"{'='*80}\n")
