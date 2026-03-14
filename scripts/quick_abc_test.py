"""
快速 ABC 测试（3 篇论文）
对比 V1, V2, V3 三个版本的 Token 消耗
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.crawlers.jina_client import JinaClient
from src.processors.content_truncator import ContentTruncator
from src.logging_config import get_logger


# 快速测试集（3 篇论文）
TEST_DOIS = [
    "10.21037/tcr-2025-1389",
    "10.1097/CM9.0000000000004035",
    "10.1136/jitc-2025-014040",
]


async def quick_test():
    """快速测试"""
    logger = get_logger()
    
    print(f"\n{'='*60}")
    print(f"🚀 快速 ABC 测试（3 篇论文）")
    print(f"{'='*60}\n")
    
    # 初始化
    jina_client = JinaClient()
    truncator = ContentTruncator()
    
    # 加载 Prompt（使用绝对路径）
    base_dir = Path("/Users/irriss/Git/IRRISS/IRRISS-SLeads")
    prompt_v1 = (base_dir / "docs/Batch Prompt v2.md").read_text()
    prompt_v2 = (base_dir / "docs/Batch Prompt v3 (Simplified).md").read_text()
    prompt_v3 = prompt_v1  # V3 使用相同的长 Prompt
    
    print(f"Prompt 长度:")
    print(f"  - V1 (长): {len(prompt_v1):,} 字符")
    print(f"  - V2 (短): {len(prompt_v2):,} 字符")
    print(f"  - V3 (长): {len(prompt_v3):,} 字符")
    print()
    
    results = {
        'v1': [],
        'v2': [],
        'v3': []
    }
    
    # 测试每篇论文
    for doi in TEST_DOIS:
        print(f"\n{'='*60}")
        print(f"📝 处理 DOI: {doi}")
        print(f"{'='*60}\n")
        
        # 爬取原始内容
        print(f"  Step 1: 爬取原始内容...")
        doi_url = f"https://doi.org/{doi}"
        original_content = await jina_client.read_paper(doi_url)
        
        original_length = len(original_content)
        print(f"  ✅ 原始长度: {original_length:,} 字符")
        
        # V1: 不截断 + 长 Prompt
        print(f"\n  V1 (不截断 + 长 Prompt):")
        full_prompt_v1 = prompt_v1.replace("{content}", original_content)
        v1_tokens = len(full_prompt_v1) / 4
        print(f"    Prompt 长度: {len(full_prompt_v1):,} 字符")
        print(f"    预估 Token: {v1_tokens:,.0f}")
        results['v1'].append({
            'doi': doi,
            'original_length': original_length,
            'prompt_length': len(full_prompt_v1),
            'tokens': v1_tokens
        })
        
        # V2: 截断 + 精简 Prompt
        print(f"\n  V2 (截断 + 精简 Prompt):")
        truncated_content = truncator.extract_metadata_section(original_content)
        truncated_length = len(truncated_content)
        reduction = 100 * (1 - truncated_length / original_length) if original_length > 0 else 0
        print(f"    截断后长度: {truncated_length:,} 字符 (减少 {reduction:.1f}%)")
        full_prompt_v2 = prompt_v2.replace("{content}", truncated_content)
        v2_tokens = len(full_prompt_v2) / 4
        print(f"    Prompt 长度: {len(full_prompt_v2):,} 字符")
        print(f"    预估 Token: {v2_tokens:,.0f}")
        results['v2'].append({
            'doi': doi,
            'original_length': original_length,
            'truncated_length': truncated_length,
            'reduction': reduction,
            'prompt_length': len(full_prompt_v2),
            'tokens': v2_tokens
        })
        
        # V3: 截断 + 长 Prompt
        print(f"\n  V3 (截断 + 长 Prompt):")
        full_prompt_v3 = prompt_v3.replace("{content}", truncated_content)
        v3_tokens = len(full_prompt_v3) / 4
        print(f"    Prompt 长度: {len(full_prompt_v3):,} 字符")
        print(f"    预估 Token: {v3_tokens:,.0f}")
        results['v3'].append({
            'doi': doi,
            'original_length': original_length,
            'truncated_length': truncated_length,
            'reduction': reduction,
            'prompt_length': len(full_prompt_v3),
            'tokens': v3_tokens
        })
    
    # 统计结果
    print(f"\n\n{'='*60}")
    print(f"📊 ABC 测试对比")
    print(f"{'='*60}\n")
    
    # 计算平均值
    v1_avg_tokens = sum(r['tokens'] for r in results['v1']) / len(results['v1'])
    v2_avg_tokens = sum(r['tokens'] for r in results['v2']) / len(results['v2'])
    v3_avg_tokens = sum(r['tokens'] for r in results['v3']) / len(results['v3'])
    
    v2_avg_reduction = sum(r['reduction'] for r in results['v2']) / len(results['v2'])
    v3_avg_reduction = sum(r['reduction'] for r in results['v3']) / len(results['v3'])
    
    # Token 减少
    v2_token_reduction = 100 * (1 - v2_avg_tokens / v1_avg_tokens)
    v3_token_reduction = 100 * (1 - v3_avg_tokens / v1_avg_tokens)
    
    # 显示对比表格
    print(f"{'版本':<15} {'平均 Token':<15} {'Token 减少':<15} {'内容减少':<15}")
    print(f"{'-'*60}")
    print(f"{'V1 (基准)':<15} {v1_avg_tokens:>15,.0f} {'-':<15} {'-':<15}")
    print(f"{'V2 (截断+短)':<15} {v2_avg_tokens:>15,.0f} {v2_token_reduction:>13.1f}% {v2_avg_reduction:>13.1f}%")
    print(f"{'V3 (截断+长)':<15} {v3_avg_tokens:>15,.0f} {v3_token_reduction:>13.1f}% {v3_avg_reduction:>13.1f}%")
    
    print()
    
    # 保存结果
    comparison = {
        'timestamp': datetime.now().isoformat(),
        'test_dois': TEST_DOIS,
        'v1': {
            'avg_tokens': v1_avg_tokens,
            'results': results['v1']
        },
        'v2': {
            'avg_tokens': v2_avg_tokens,
            'avg_reduction': v2_avg_reduction,
            'token_reduction': v2_token_reduction,
            'results': results['v2']
        },
        'v3': {
            'avg_tokens': v3_avg_tokens,
            'avg_reduction': v3_avg_reduction,
            'token_reduction': v3_token_reduction,
            'results': results['v3']
        }
    }
    
    output_file = Path("tmp/abc_test/quick_comparison.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w') as f:
        json.dump(comparison, f, indent=2, ensure_ascii=False)
    
    print(f"📄 对比结果已保存到: {output_file}")
    
    # 建议
    print(f"\n{'='*60}")
    print(f"💡 分析")
    print(f"{'='*60}\n")
    
    print(f"Token 消耗对比:")
    print(f"  - V2 vs V1: 减少 {v2_token_reduction:.1f}%")
    print(f"  - V3 vs V1: 减少 {v3_token_reduction:.1f}%")
    print()
    
    if v3_token_reduction > 80:
        print(f"✅ V3 Token 减少超过 80%，截断效果显著")
    elif v3_token_reduction > 50:
        print(f"✅ V3 Token 减少超过 50%，截断效果明显")
    else:
        print(f"⚠️ V3 Token 减少不足 50%，截断效果不明显")
    
    print(f"\n下一步：")
    print(f"1. 提交到智谱批处理 API，获取提取结果")
    print(f"2. 使用浏览器打开原始论文")
    print(f"3. 对比 V1, V2, V3 的提取准确性")
    print(f"4. 根据结果选择最优版本")
    
    await jina_client.close()


if __name__ == "__main__":
    asyncio.run(quick_test())
