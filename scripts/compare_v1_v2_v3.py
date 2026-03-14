"""
对比 V1, V2, V3 的提取准确性
"""

import json
from pathlib import Path
from collections import defaultdict

# 添加项目根目录
import sys
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def load_results(file_path):
    """加载结果文件"""
    results = {}
    with open(file_path) as f:
        for line in f:
            data = json.loads(line)
            custom_id = data['custom_id']
            response = data['response']
            
            if 'body' in response and 'choices' in response['body']:
                content = response['body']['choices'][0]['message']['content']
                
                # 尝试解析 JSON
                try:
                    # 提取 JSON 部分
                    if '```json' in content:
                        json_str = content.split('```json')[1].split('```')[0].strip()
                    elif '```' in content:
                        json_str = content.split('```')[1].split('```')[0].strip()
                    else:
                        json_str = content
                    
                    result = json.loads(json_str)
                    results[custom_id] = result
                except:
                    results[custom_id] = {'error': 'parse_failed', 'raw': content[:200]}
    
    return results


def compare_field(v1, v2, v3, field):
    """对比某个字段"""
    v1_val = v1.get(field)
    v2_val = v2.get(field)
    v3_val = v3.get(field)
    
    # 检查是否一致
    v1_v2_match = v1_val == v2_val
    v1_v3_match = v1_val == v3_val
    v2_v3_match = v2_val == v3_val
    
    return {
        'field': field,
        'v1': v1_val,
        'v2': v2_val,
        'v3': v3_val,
        'v1_v2_match': v1_v2_match,
        'v1_v3_match': v1_v3_match,
        'v2_v3_match': v2_v3_match,
    }


def main():
    print(f"\n{'='*80}")
    print(f"📊 V1 vs V2 vs V3 准确性对比")
    print(f"{'='*80}\n")
    
    # 加载结果
    v1_file = Path("tmp/batch/v1_result_20260314_200227.jsonl")
    v2_file = Path("tmp/batch/v2_result_20260314_200454.jsonl")
    v3_file = Path("tmp/batch/v3_result_20260314_200227.jsonl")
    
    v1_results = load_results(v1_file)
    v2_results = load_results(v2_file)
    v3_results = load_results(v3_file)
    
    print(f"✅ V1: {len(v1_results)} 条")
    print(f"✅ V2: {len(v2_results)} 条")
    print(f"✅ V3: {len(v3_results)} 条\n")
    
    # 对比每篇论文
    all_dois = set(v1_results.keys()) | set(v2_results.keys()) | set(v3_results.keys())
    
    comparison_results = []
    
    for doi in sorted(all_dois):
        v1 = v1_results.get(doi, {})
        v2 = v2_results.get(doi, {})
        v3 = v3_results.get(doi, {})
        
        # 检查是否有错误
        if 'error' in v1 or 'error' in v2 or 'error' in v3:
            print(f"❌ {doi}: 解析失败")
            continue
        
        # 对比关键字段
        fields_to_compare = [
            'title',
            'published_at',
            'doi',
        ]
        
        author_fields = []
        if 'corresponding_author' in v1:
            author_fields = ['name', 'email', 'address', 'address_cn']
        
        # 统计一致性
        matches = {
            'v1_v2': 0,
            'v1_v3': 0,
            'v2_v3': 0,
        }
        
        for field in fields_to_compare:
            comp = compare_field(v1, v2, v3, field)
            if comp['v1_v2_match']:
                matches['v1_v2'] += 1
            if comp['v1_v3_match']:
                matches['v1_v3'] += 1
            if comp['v2_v3_match']:
                matches['v2_v3'] += 1
        
        # 对应作者信息
        if 'corresponding_author' in v1:
            for field in author_fields:
                v1_val = v1.get('corresponding_author', {}).get(field)
                v2_val = v2.get('corresponding_author', {}).get(field)
                v3_val = v3.get('corresponding_author', {}).get(field)
                
                if v1_val == v2_val:
                    matches['v1_v2'] += 1
                if v1_val == v3_val:
                    matches['v1_v3'] += 1
                if v2_val == v3_val:
                    matches['v2_v3'] += 1
        
        total_fields = len(fields_to_compare) + len(author_fields)
        
        comparison_results.append({
            'doi': doi,
            'matches': matches,
            'total_fields': total_fields,
            'v1': v1,
            'v2': v2,
            'v3': v3,
        })
    
    # 汇总统计
    print(f"\n{'='*80}")
    print(f"📊 汇总统计")
    print(f"{'='*80}\n")
    
    total_fields = sum(r['total_fields'] for r in comparison_results)
    
    v1_v2_matches = sum(r['matches']['v1_v2'] for r in comparison_results)
    v1_v3_matches = sum(r['matches']['v1_v3'] for r in comparison_results)
    v2_v3_matches = sum(r['matches']['v2_v3'] for r in comparison_results)
    
    print(f"V1 vs V2 一致性: {v1_v2_matches}/{total_fields} ({100*v1_v2_matches/total_fields:.1f}%)")
    print(f"V1 vs V3 一致性: {v1_v3_matches}/{total_fields} ({100*v1_v3_matches/total_fields:.1f}%)")
    print(f"V2 vs V3 一致性: {v2_v3_matches}/{total_fields} ({100*v2_v3_matches/total_fields:.1f}%)")
    
    # 保存详细对比结果
    output_file = Path("tmp/batch/comparison_v1_v2_v3.json")
    with open(output_file, 'w') as f:
        json.dump(comparison_results, f, indent=2, ensure_ascii=False)
    
    print(f"\n📄 详细对比结果: {output_file}")


if __name__ == "__main__":
    main()
