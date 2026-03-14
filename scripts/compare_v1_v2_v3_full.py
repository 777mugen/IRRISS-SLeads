"""
V1 vs V2 vs V3 完整对比
"""

import json
from pathlib import Path

# 结果文件
v1_file = Path("tmp/batch/v1_result_20260314_200227.jsonl")
v2_file = Path("tmp/batch/v2_result_20260314_203229.jsonl")
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
v2_results = load_results(v2_file)
v3_results = load_results(v3_file)

print(f"\n{'='*80}")
print(f"📊 V1 vs V2 vs V3 完整对比报告")
print(f"{'='*80}\n")

print(f"V1: {len(v1_results)} 篇论文")
print(f"V2: {len(v2_results)} 篇论文")
print(f"V3: {len(v3_results)} 篇论文\n")

# 对比每篇论文
comparison = []

for doi in v1_results.keys():
    v1 = v1_results[doi]
    v2 = v2_results.get(doi, {})
    v3 = v3_results.get(doi, {})
    
    # 检查是否都是 null
    v1_is_null = v1.get('title') is None
    v2_is_null = v2.get('title') is None
    v3_is_null = v3.get('title') is None
    
    # 提取关键信息
    v1_author = v1.get('corresponding_author', {}).get('name') if not v1_is_null else None
    v2_author = v2.get('corresponding_author', {}).get('name') if not v2_is_null else None
    v3_author = v3.get('corresponding_author', {}).get('name') if not v3_is_null else None
    
    v1_email = v1.get('corresponding_author', {}).get('email') if not v1_is_null else None
    v2_email = v2.get('corresponding_author', {}).get('email') if not v2_is_null else None
    v3_email = v3.get('corresponding_author', {}).get('email') if not v3_is_null else None
    
    comparison.append({
        'doi': doi,
        'v1_success': not v1_is_null,
        'v2_success': not v2_is_null,
        'v3_success': not v3_is_null,
        'v1_author': v1_author,
        'v2_author': v2_author,
        'v3_author': v3_author,
        'v1_email': v1_email,
        'v2_email': v2_email,
        'v3_email': v3_email,
    })

# 统计成功率
v1_success = sum(1 for c in comparison if c['v1_success'])
v2_success = sum(1 for c in comparison if c['v2_success'])
v3_success = sum(1 for c in comparison if c['v3_success'])

print(f"{'='*80}")
print(f"📊 成功率统计")
print(f"{'='*80}\n")

print(f"V1 (不截断+长): {v1_success}/{len(comparison)} 成功 ({100*v1_success/len(comparison):.1f}%)")
print(f"V2 (截断+短): {v2_success}/{len(comparison)} 成功 ({100*v2_success/len(comparison):.1f}%)")
print(f"V3 (截断+长): {v3_success}/{len(comparison)} 成功 ({100*v3_success/len(comparison):.1f}%)")

# 统计差异
differences = []

for c in comparison:
    issues = []
    
    # 检查通讯作者是否一致
    if c['v1_author'] != c['v2_author']:
        issues.append(f"V1/V2 作者不一致")
    if c['v1_author'] != c['v3_author']:
        issues.append(f"V1/V3 作者不一致")
    if c['v2_author'] != c['v3_author']:
        issues.append(f"V2/V3 作者不一致")
    
    # 检查邮箱是否一致
    if c['v1_email'] != c['v2_email']:
        issues.append(f"V1/V2 邮箱不一致")
    if c['v1_email'] != c['v3_email']:
        issues.append(f"V1/V3 邮箱不一致")
    if c['v2_email'] != c['v3_email']:
        issues.append(f"V2/V3 邮箱不一致")
    
    if issues:
        differences.append({
            'doi': c['doi'],
            'issues': issues,
            'v1': f"{c['v1_author']} <{c['v1_email']}>",
            'v2': f"{c['v2_author']} <{c['v2_email']}>",
            'v3': f"{c['v3_author']} <{c['v3_email']}>",
        })

print(f"\n{'='*80}")
print(f"⚠️  差异分析 ({len(differences)} 篇)")
print(f"{'='*80}\n")

for i, diff in enumerate(differences, 1):
    print(f"{i}. {diff['doi']}")
    print(f"   问题: {', '.join(diff['issues'])}")
    print(f"   V1: {diff['v1']}")
    print(f"   V2: {diff['v2']}")
    print(f"   V3: {diff['v3']}")
    print()

# 保存详细对比
output_file = Path("tmp/batch/v1_v2_v3_comparison.json")
with open(output_file, 'w') as f:
    json.dump(comparison, f, indent=2, ensure_ascii=False)

print(f"\n{'='*80}")
print(f"✅ 对比完成！")
print(f"{'='*80}\n")

print(f"📄 详细对比结果: {output_file}")
