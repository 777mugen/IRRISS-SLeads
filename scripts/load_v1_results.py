"""
加载已有的 V1 结果
"""

import json
from pathlib import Path

# 读取 V1 结果
v1_file = Path('tmp/batch/v1_result_20260314_200227.jsonl')

results = []
with open(v1_file) as f:
    for line in f:
        data = json.loads(line)
        doi = data['custom_id'].replace('doi_', '').replace('_', '/', 1).replace('_', '.')

        # 提取内容
        response = data.get('response', {})
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

                results.append({
                    'doi': doi,
                    'title': result.get('title'),
                    'author': result.get('corresponding_author', {}).get('name'),
                    'email': result.get('corresponding_author', {}).get('email'),
                })
            except:
                results.append({
                    'doi': doi,
                    'error': 'parse_failed'
                })

print(f'已提取 {len(results)} 篇论文\n')

# 保存到文件
output_file = Path('tmp/batch/v1_results_summary.json')
with open(output_file, 'w') as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print(f'✅ 保存到: {output_file}\n')

print(f'前 5 篇:')
for r in results[:5]:
    print(f"  - {r['doi']}")
    print(f"    作者: {r.get('author')}")
    print(f"    邮箱: {r.get('email')}")
