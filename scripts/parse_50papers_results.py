"""
解析 50 篇论文提取结果
"""

import json
from pathlib import Path

result_file = Path('tmp/batch/v1_50papers_result_20260314_220104.jsonl')

results = []
success = 0
failed = 0
errors = []

with open(result_file) as f:
    for line in f:
        data = json.loads(line)
        doi = data['custom_id'].replace('doi_', '').replace('_', '/', 1).replace('_', '.')

        # 检查响应
        response = data.get('response', {})
        status_code = response.get('status_code', 0)

        if status_code == 200:
            body = response.get('body', {})
            if 'choices' in body:
                content = body['choices'][0]['message']['content']

                # 解析 JSON
                try:
                    if '```json' in content:
                        json_str = content.split('```json')[1].split('```')[0].strip()
                    elif '```' in content:
                        json_str = content.split('```')[1].split('```')[0].strip()
                    else:
                        json_str = content

                    result = json.loads(json_str)

                    author_info = result.get('corresponding_author', {})

                    results.append({
                        'doi': doi,
                        'title': result.get('title'),
                        'author': author_info.get('name'),
                        'email': author_info.get('email'),
                        'address': author_info.get('address'),
                    })
                    success += 1

                except Exception as e:
                    failed += 1
                    errors.append({
                        'doi': doi,
                        'error': str(e),
                        'content_preview': content[:100]
                    })
        else:
            failed += 1
            errors.append({
                'doi': doi,
                'error': f'status_code: {status_code}'
            })

print(f'\n{'='*80}')
print(f'📊 50 篇论文提取结果统计')
print(f'{'='*80}\n')

print(f'总论文数: {len(results) + failed}')
print(f'成功提取: {success}')
print(f'失败: {failed}')
print(f'成功率: {100 * success / (success + failed):.1f}%\n')

# 显示前 10 篇
print(f'前 10 篇提取结果:\n')
for i, r in enumerate(results[:10], 1):
    print(f'{i}. {r["doi"]}')
    print(f'   作者: {r.get("author")}')
    print(f'   邮箱: {r.get("email")}')
    print()

# 保存结果
output = {
    'total': len(results) + failed,
    'success': success,
    'failed': failed,
    'success_rate': f'{100 * success / (success + failed):.1f}%',
    'results': results,
    'errors': errors,
}

with open('tmp/batch/v1_50papers_summary.json', 'w') as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print(f'✅ 汇总保存到: tmp/batch/v1_50papers_summary.json\n')

# 保存 DOI 列表（用于浏览器验证）
with open('tmp/batch/v1_50papers_dois.txt', 'w') as f:
    for r in results:
        f.write(f"{r['doi']}\n")

print(f'✅ DOI 列表保存到: tmp/batch/v1_50papers_dois.txt\n')
