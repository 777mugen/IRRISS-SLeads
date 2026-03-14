"""
验证真正存在的论文（使用正确的 DOI 格式）
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
import json

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.crawlers.jina_client import JinaClient


# 真实存在的论文 DOI（从原始19篇中筛选）
REAL_DOIS = [
    "10.1136/jitc-2025-014040",
    "10.21037/tcr-2025-aw-2287",
    "10.1097/CM9.0000000000004035",
    "10.3389/fcimb.2026.1747682",
    "10.7150/thno.124789",
    "10.3389/fonc.2026.1728876",
    "10.1038/s41556-026-01907-x",
    "10.21037/jgo-2025-750",
    "10.1158/0008-5472.CAN-25-3806",
    "10.32604/or.2026.071122",
    "10.2196/86322",
    "10.4103/bc.bc_65_24",
    "10.21037/tcr-2025-1389",
    "10.21037/tcr-2025-1-2580",
]


async def verify_real_papers():
    """验证真实存在的论文"""

    client = JinaClient()

    # 读取提取结果
    with open(project_root / 'tmp/batch/v1_50papers_summary.json') as f:
        data = json.load(f)

    # 创建 DOI -> 提取结果映射
    doi_map = {}
    for r in data['results']:
        # 修正 DOI 格式
        doi_raw = r['doi']
        # 将 "10/1136.jitc-2025-014040" 转换回 "10.1136/jitc-2025-014040"
        if '/' in doi_raw:
            parts = doi_raw.split('/', 1)
            if len(parts) == 2:
                # parts[0] = "10"
                # parts[1] = "1136.jitc-2025-014040"
                prefix = parts[0]  # "10"
                suffix_with_dot = parts[1]  # "1136.jitc-2025-014040"
                
                # 找到第一个点的位置
                dot_pos = suffix_with_dot.find('.')
                if dot_pos > 0:
                    # "1136.jitc-2025-014040" -> "1136" + "jitc-2025-014040"
                    registrant = suffix_with_dot[:dot_pos]
                    rest = suffix_with_dot[dot_pos+1:]
                    fixed_doi = f"{prefix}.{registrant}/{rest}"
                    doi_map[fixed_doi] = r

    print(f"\n{'='*80}")
    print(f"🔍 验证真实论文")
    print(f"{'='*80}\n")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    verifications = []

    # 验证前5篇真实论文
    test_dois = REAL_DOIS[:5]

    for i, doi in enumerate(test_dois, 1):
        print(f"[{i}/5] {doi}")

        # 查找对应的提取结果
        v1_data = doi_map.get(doi)
        if not v1_data:
            print(f"  ⚠️  未在提取结果中找到")
            continue

        v1_author = v1_data.get('author')
        v1_email = v1_data.get('email')

        print(f"  V1 提取: {v1_author} <{v1_email}>")

        try:
            # 使用 Jina Reader 获取原始内容
            content = await client.read_paper(f"https://doi.org/{doi}")

            if not content or len(content) < 100:
                print(f"  ❌ 内容过短或为空\n")
                continue

            # 保存原始内容
            safe_doi = doi.replace('/', '_').replace('.', '_')
            content_file = project_root / f"tmp/verification/{timestamp}_{safe_doi}.txt"
            content_file.parent.mkdir(parents=True, exist_ok=True)
            with open(content_file, 'w') as f:
                f.write(content)

            print(f"  ✅ 获取成功: {len(content)} 字符")

            # 简单检查
            has_author = v1_author in content if v1_author else False
            has_email = v1_email in content if v1_email else False

            verification = {
                'doi': doi,
                'v1_author': v1_author,
                'v1_email': v1_email,
                'content_length': len(content),
                'author_in_content': has_author,
                'email_in_content': has_email,
                'content_file': str(content_file),
            }

            if has_author:
                print(f"  ✅ 作者在内容中")
            else:
                print(f"  ⚠️  作者不在内容中")

            if has_email:
                print(f"  ✅ 邮箱在内容中")
            else:
                print(f"  ⚠️  邮箱不在内容中")

            verifications.append(verification)

        except Exception as e:
            print(f"  ❌ 错误: {e}\n")
            verifications.append({
                'doi': doi,
                'error': str(e),
            })

        print()

    # 保存验证结果
    report = {
        'timestamp': timestamp,
        'total_papers': 5,
        'verifications': verifications,
    }

    report_file = project_root / f"tmp/batch/real_papers_verification_{timestamp}.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*80}")
    print(f"✅ 验证完成")
    print(f"{'='*80}\n")
    print(f"报告: {report_file}\n")

    await client.close()


if __name__ == "__main__":
    asyncio.run(verify_real_papers())
