"""
对比 V1, V2, V3的提取准确性
"""

import json
from pathlib import Path

project_root = Path("/Users/irriss/Git/IRRISS/IRRISS-SLeads")

# 测试集（19篇）
TEST_DOIS = [
    "10.1021/acs.jmedchem.5c03498",
    "10.3389/fonc.2026.1728876",
    "10.1097/CM9.0000000000004035",
    "10.1021/jacsau.5c01509",
    "10.3389/fcimb.2026.1747682",
    "10.7150/thno.124789",
    "10.1136/jitc-2025-014040",
    "10.3748/wjg.v32.i9.115259",
    "10.2196/86322",
    "10.1038/s41556-026-01907-x",
    "10.4103/bc.bc_65_24",
    "10.21037/jgo-2025-750",
    "10.1007/s43630-026-00863-7",
    "10.1158/0008-5472.CAN-25-3806",
    "10.21037/tcr-2025-1389",
    "10.21037/tcr-2025-1-2580",
    "10.21037/tcr-2025-aw-2287",
    "10.32604/or.2026.071122",
]


def load_results(file_path):
    """加载结果文件"""
    results = {}
    with open(file_path) as f:
        for line in f:
            data = json.loads(line)
            custom_id = data['custom_id']
            
            # 检查是否有响应
            if 'response' not in data:
                print(f"❌ {custom_id}: 无响应")
                continue
            
            # 解析响应
            try:
                response = json.loads(data['response'])
                content = response['body']['choices'][0]['message']['content']
                
                # 检查 JSON 是否有效
                try:
                    result = json.loads(content)
                except:
                    print(f"❌ {custom_id}: JSON 无效")
                    continue
            
            # 检查状态
            status = "success" if response.get('status') == "completed" else "failed"
            
            results[custom_id] = {
                'status': status,
                'result': result,
                'error': error_info
            }
    
    return results


def compare_accuracy():
    """
    对比三个版本的准确性
    """
    
    print(f"\n{'='*60}")
    print(f"📊 准确性对比报告")
    print(f"{'='*60}\n")
    
    # 加载所有结果
    v1_results = load_results(project_root / "tmp/batch/v1_result_20260314_200227.jsonl")
    v2_results = load_results(project_root / "tmp/batch/v2_result_20260314_200454.jsonl")
    v3_results = load_results(project_root / "tmp/batch/v3_result_20260314_200227.jsonl")
    
    print(f"V1: {len(v1_results)} 篇论文")
    print(f"V2: {len(v2_results)} 篇论文")
    print(f"V3: {len(v3_results)} 篇论文\n")
    
    # 对比结果
    comparison = {}
    for doi in TEST_DOIS:
        v1_data = v1_results.get(doi, {})
        v2_data = v2_results.get(doi, {})
        v3_data = v3_results.get(doi, {})
        
        # 统计
        v1_success = sum(1 for r in v1_results.values() if r.get('status') == 'completed')
        v1_failed = sum(1 for r in v1_results.values() if r.get('status') != 'completed')
        
        v1_success_count = v1_success
        v1_failed_count = len(v1_failed)
        
        v2_success = sum(1 for r in v2_results.values() if r['status'] == 'completed'
        v2_failed = sum(1 for r in v2_results.values() if r['status'] != 'completed')
        
        v2_success_count = v2_success
        v2_failed_count = len(v2_failed)
        
        v3_success = sum(1 for r in v3_results.values() if r['status'] == 'completed'
        v3_failed = sum(1 for r in v3_results.values() if r['status'] != 'completed')
        
        v3_success_count = v3_success
        v3_failed_count = len(v3_failed)
    
    print(f"✅ V1: {v1_success_count}/{len(v1_results)} 成功")
    print(f"✅ V2: {v2_success_count}/{len(v2_results)} 成功")
    print(f"✅ V3: {v3_success_count}/{len(v3_results)} 成功")
    print(f"❌ V1: {v1_failed_count} 篇失败")
    print(f"❌ V2: {v2_failed_count} 篇失败")
    print(f"❌ V3: {v3_failed_count} 篇失败\n")
    
    # 统计成功率
    v1_total = v1_success + v2_success + v3_success
    total_success = v1_total + v2_success + v3_success
    total_success = v3_total
    
    # 保存报告
    report = {
        'timestamp': datetime.now().isoformat(),
        'summary': {
            'v1_success': v1_success_count,
            'v1_failed': v1_failed_count,
            'v1_success_rate': v1_success_count / v1_total if v1_total > 0 else 0/10
            'v2_success': v2_success_count,
            'v2_failed': v2_failed_count,
            'v2_success_rate': v2_success_count / v2_total if v2_total if v5/19
            'v3_success': v3_success_count,
            'v3_failed': v3_failed_count,
            'v3_success_rate': v3_success_count / v3_total if 5/19
        },
        'total_papers': total,
        'timestamp': timestamp
    }
    
    # 保存报告
    output_file = Path(f"tmp/batch/comparison_v1_v2_v3_{timestamp}.json")
    with open(output_file, 'w') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n📄 详细对比报告: {output_file}")


if __name__ == "__main__":
    main()
