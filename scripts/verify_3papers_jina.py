"""
自动验证 18 篇论文
使用 Jina Reader API + 人工检查关键信息
"""

import asyncio
import sys
import re
from pathlib import Path
from datetime import datetime
import json

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.crawlers.jina_client import JinaClient


async def verify_papers():
    """验证论文"""

    client = JinaClient()

    # 读取提取结果
    with open(project_root / 'tmp/batch/v1_50papers_summary.json') as f:
        data = json.load(f)

    # 筛选有完整信息的论文
    papers = [r for r in data['results'] if r.get('author') and r.get('email')]

    print(f"\n{'='*80}")
    print(f"🔍 验证 {len(papers)} 篇论文")
    print(f"{'='*80}\n")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    verifications = []

    for i, paper in enumerate(papers[:3], 1):  # 先验证前3篇
        doi = paper['doi'].replace('/', '.')
        v1_author = paper['author']
        v1_email = paper['email']

        print(f"[{i}/3] 验证: {doi}")
        print(f"  V1 提取: {v1_author} <{v1_email}>")

        try:
            # 使用 Jina Reader 获取原始内容
            content = await client.read_paper(f"https://doi.org/{paper['doi']}")

            if not content or len(content) < 100:
                print(f"  ❌ 内容过短或为空\n")
                continue

            # 保存原始内容
            content_file = project_root / f"tmp/verification/{timestamp}_{doi}.txt"
            content_file.parent.mkdir(parents=True, exist_ok=True)
            with open(content_file, 'w') as f:
                f.write(content)

            print(f"  ✅ 获取成功: {len(content)} 字符")
            print(f"  📄 保存到: {content_file.name}")

            # 尝试提取通讯作者信息（简单匹配）
            # 查找 * 符号附近的名字
            patterns = [
                r'\*\s*([A-Z][a-z]+\s+[A-Z][a-z]+)',  # * Name
                r'Corresponding [Aa]uthor[:\s]+([A-Z][a-z]+\s+[A-Z][a-z]+)',
                r'([A-Z][a-z]+\s+[A-Z][a-z]+)\s*[\*\†]',
            ]

            found_authors = []
            for pattern in patterns:
                matches = re.findall(pattern, content)
                found_authors.extend(matches)

            # 查找邮箱
            email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
            found_emails = re.findall(email_pattern, content)

            verification = {
                'doi': paper['doi'],
                'v1_author': v1_author,
                'v1_email': v1_email,
                'content_length': len(content),
                'content_file': str(content_file),
                'found_authors': list(set(found_authors))[:5],  # 前5个
                'found_emails': list(set(found_emails))[:10],  # 前10个
                'match': False,
                'errors': [],
            }

            # 检查是否匹配
            if v1_author in ' '.join(found_authors):
                verification['match'] = True
                print(f"  ✅ 作者匹配: {v1_author}")

            if v1_email in found_emails:
                print(f"  ✅ 邮箱匹配: {v1_email}")
            else:
                verification['errors'].append('email_not_found_in_content')
                print(f"  ⚠️  邮箱未在内容中找到")

            verifications.append(verification)

        except Exception as e:
            print(f"  ❌ 错误: {e}\n")
            verifications.append({
                'doi': paper['doi'],
                'error': str(e),
            })

        print()

    # 保存验证结果
    report = {
        'timestamp': timestamp,
        'total_papers': 3,
        'verifications': verifications,
    }

    report_file = project_root / f"tmp/batch/verification_report_{timestamp}.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*80}")
    print(f"✅ 验证完成")
    print(f"{'='*80}\n")
    print(f"报告: {report_file}\n")

    await client.close()


if __name__ == "__main__":
    asyncio.run(verify_papers())
