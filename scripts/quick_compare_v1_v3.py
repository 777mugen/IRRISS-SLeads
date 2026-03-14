"""
V1 vs V3 快速对比
"""

import json
from pathlib import Path

# V1 结果文件
v1_file = Path("tmp/batch/v1_result_20260314_200227.jsonl")
v3_file = Path("tmp/batch/v3_result_20260314_200227.jsonl")

# 加载结果
def load_results(file_path):
    results = {}
    with open(file_path) as f:
        for line in f:
            data = json.loads(line)
            doi = data['custom_id']
            response = data.get('response', {})
            body = response.get('body', {})
            
            # 提取内容
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
                    results[doi] = result
                except:
                    results[doi] = {'error': 'parse_failed'}
    
    return results

v1_results = load_results(v1_file)
v3_results = load_results(v3_file)

print(f"\n{'='*80}")
print(f"📊 V1 vs V3 对比报告")
print(f"{'='*80}\n")

print(f"V1: {len(v1_results)} 篇论文")
print(f"V3: {len(v3_results)} 篇论文\n")

# 对比每篇论文
differences = []

for doi in v1_results.keys():
    v1 = v1_results[doi]
    v3 = v3_results.get(doi, {})
    
    # 检查是否都是 null
    v1_is_null = v1.get('title') is None
    v3_is_null = v3.get('title') is None
    
    if v1_is_null and v3_is_null:
        # 两者都失败，跳过
        continue
    
    if v1_is_null and not v3_is_null:
        differences.append({
            'doi': doi,
            'issue': 'V1 失败, V3 成功',
            'v1_author': None,
            'v1_email': None,
            'v3_author': v3.get('corresponding_author', {}).get('name'),
            'v3_email': v3.get('corresponding_author', {}).get('email'),
        })
        continue
    
    if not v1_is_null and v3_is_null:
        differences.append({
            'doi': doi,
            'issue': 'V1 成功, V3 失败 ⚠️',
            'v1_author': v1.get('corresponding_author', {}).get('name'),
            'v1_email': v1.get('corresponding_author', {}).get('email'),
            'v3_author': None,
            'v3_email': None,
        })
        continue
    
    # 两者都成功，对比详细信息
    v1_author = v1.get('corresponding_author', {}).get('name')
    v3_author = v3.get('corresponding_author', {}).get('name')
    
    v1_email = v1.get('corresponding_author', {}).get('email')
    v3_email = v3.get('corresponding_author', {}).get('email')
    
    if v1_author != v3_author or v1_email != v3_email:
        differences.append({
            'doi': doi,
            'issue': '通讯作者或邮箱不一致 ⚠️',
            'v1_author': v1_author,
            'v1_email': v1_email,
            'v3_author': v3_author,
            'v3_email': v3_email,
        })

# 输出差异
if differences:
    print(f"\n{'='*80}")
    print(f"⚠️  发现 {len(differences)} 篇论文有差异")
    print(f"{'='*80}\n")
    
    for i, diff in enumerate(differences, 1):
        print(f"{i}. {diff['doi']}")
        print(f"   问题: {diff['issue']}")
        print(f"   V1: {diff['v1_author']} <{diff['v1_email']}>")
        print(f"   V3: {diff['v3_author']} <{diff['v3_email']}>")
        print()
else:
    print("✅ 所有论文提取结果一致！")

# 统计
v1_success = sum(1 for r in v1_results.values() if r.get('title') is not None)
v3_success = sum(1 for r in v3_results.values() if r.get('title') is not None)

print(f"\n{'='*80}")
print(f"📊 成功率统计")
print(f"{'='*80}\n")

print(f"V1: {v1_success}/{len(v1_results)} 成功 ({100*v1_success/len(v1_results):.1f}%)")
print(f"V3: {v3_success}/{len(v3_results)} 成功 ({100*v3_success/len(v3_results):.1f}%)")
