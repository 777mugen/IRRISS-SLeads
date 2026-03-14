"""
修正版：快速测试截断效果
包含完整的 Token 预估（Prompt + 内容）
"""

import asyncio
import sys
import json
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
    "10.21037/tcr-2025-1389",  # AME（已验证）
    "10.1097/CM9.0000000000004035",  # Chinese Medical Journal
    "10.1136/jitc-2025-014040",  # JITC
]


def estimate_tokens(text: str) -> int:
    """
    预估 Token 数量
    
    规则：
    - 英文: 1 token ≈ 4 字符
    - 中文: 1 token ≈ 1.5 字符
    """
    # 粗略估算：平均 3 字符 = 1 token
    return len(text) // 3


async def quick_test():
    """快速测试"""
    logger = get_logger()
    
    print(f"\n{'='*60}")
    print(f"🚀 快速测试：截断效果对比（完整版）")
    print(f"{'='*60}\n")
    
    # 初始化
    jina_client = JinaClient()
    truncator = ContentTruncator()
    
    # 加载 Prompt
    prompt_file = project_root / "docs/Batch Prompt v2.md"
    prompt = prompt_file.read_text()
    prompt_tokens = estimate_tokens(prompt)
    
    print(f"Prompt 长度: {len(prompt):,} 字符 (~{prompt_tokens:,} tokens)\n")
    
    results = {
        'v1': [],
        'v3': []
    }
    
    # 测试每篇论文
    for doi in TEST_DOIS:
        print(f"{'='*60}")
        print(f"📝 处理 DOI: {doi}")
        print(f"{'='*60}\n")
        
        # 爬取原始内容
        print(f"  Step 1: 爬取原始内容...")
        doi_url = f"https://doi.org/{doi}"
        original_content = await jina_client.read_paper(doi_url)
        
        original_length = len(original_content)
        print(f"  ✅ 原始长度: {original_length:,} 字符\n")
        
        # V1: 不截断
        print(f"  V1 (不截断):")
        v1_content_tokens = estimate_tokens(original_content)
        v1_total_tokens = prompt_tokens + v1_content_tokens
        print(f"    内容 Token: {v1_content_tokens:,}")
        print(f"    Prompt Token: {prompt_tokens:,}")
        print(f"    总 Token: {v1_total_tokens:,}\n")
        results['v1'].append({
            'doi': doi,
            'original_length': original_length,
            'content_tokens': v1_content_tokens,
            'prompt_tokens': prompt_tokens,
            'total_tokens': v1_total_tokens
        })
        
        # V3: 截断
        print(f"  V3 (截断):")
        truncated_content = truncator.extract_metadata_section(original_content)
        truncated_length = len(truncated_content)
        reduction = 100 * (1 - truncated_length / original_length) if original_length > 0 else 0
        print(f"    截断后长度: {truncated_length:,} 字符 (减少 {reduction:.1f}%)")
        v3_content_tokens = estimate_tokens(truncated_content)
        v3_total_tokens = prompt_tokens + v3_content_tokens
        print(f"    内容 Token: {v3_content_tokens:,}")
        print(f"    Prompt Token: {prompt_tokens:,}")
        print(f"    总 Token: {v3_total_tokens:,}\n")
        results['v3'].append({
            'doi': doi,
            'original_length': original_length,
            'truncated_length': truncated_length,
            'reduction': reduction,
            'content_tokens': v3_content_tokens,
            'prompt_tokens': prompt_tokens,
            'total_tokens': v3_total_tokens
        })
    
    # 统计结果
    print(f"\n{'='*60}")
    print(f"📊 测试结果")
    print(f"{'='*60}\n")
    
    # 计算平均值
    v1_avg_tokens = sum(r['total_tokens'] for r in results['v1']) / len(results['v1'])
    v3_avg_tokens = sum(r['total_tokens'] for r in results['v3']) / len(results['v3'])
    v3_avg_reduction = sum(r['reduction'] for r in results['v3']) / len(results['v3'])
    
    # Token 减少
    token_reduction = 100 * (1 - v3_avg_tokens / v1_avg_tokens) if v1_avg_tokens > 0 else 0
    
    # 显示对比表格
    print(f"{'版本':<15} {'平均 Token':<15} {'Token 减少':<15} {'内容减少':<15}")
    print(f"{'-'*60}")
    print(f"{'V1 (基准)':<15} {v1_avg_tokens:>15,.0f} {'-':<15} {'-':<15}")
    print(f"{'V3 (截断)':<15} {v3_avg_tokens:>15,.0f} {token_reduction:>13.1f}% {v3_avg_reduction:>13.1f}%")
    
    print()
    
    # 详细结果
    print(f"\n详细结果:")
    for i, doi in enumerate(TEST_DOIS):
        print(f"\n  {i+1}. {doi}")
        v1 = results['v1'][i]
        v3 = results['v3'][i]
        print(f"     V1 Token: {v1['total_tokens']:,}")
        print(f"     V3 Token: {v3['total_tokens']:,}")
        print(f"     减少: {100 * (1 - v3['total_tokens'] / v1['total_tokens']):.1f}%")
        print(f"     内容减少: {v3['reduction']:.1f}%")
    
    # 保存结果
    comparison = {
        'timestamp': datetime.now().isoformat(),
        'test_dois': TEST_DOIS,
        'v1': {
            'avg_tokens': v1_avg_tokens,
            'results': results['v1']
        },
        'v3': {
            'avg_tokens': v3_avg_tokens,
            'avg_reduction': v3_avg_reduction,
            'token_reduction': token_reduction,
            'results': results['v3']
        }
    }
    
    output_file = Path("tmp/quick_test_result.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w') as f:
        json.dump(comparison, f, indent=2, ensure_ascii=False)
    
    print(f"\n📄 对比结果已保存到: {output_file}")
    
    # 分析
    print(f"\n{'='*60}")
    print(f"💡 分析")
    print(f"{'='*60}\n")
    
    print(f"Token 消耗:")
    print(f"  - V1: {v1_avg_tokens:,.0f}")
    print(f"  - V3: {v3_avg_tokens:,.0f}")
    print(f"  - 减少: {token_reduction:.1f}%")
    print()
    
    if token_reduction > 80:
        print(f"✅ Token 减少超过 80%，截断效果显著")
    elif token_reduction > 50:
        print(f"✅ Token 减少超过 50%，截断效果明显")
    elif token_reduction > 20:
        print(f"⚠️ Token 减少在 20-50% 之间，截断效果一般")
    else:
        print(f"❌ Token 减少不足 20%，截断效果不明显")
    
    print(f"\n下一步：")
    print(f"1. 检查论文2（{TEST_DOIS[1]}）为什么截断失败")
    print(f"2. 提交到智谱批处理 API，获取提取结果")
    print(f"3. 对比 V1 和 V3 的提取准确性")
    print(f"4. 根据结果决定是否使用截断")


if __name__ == "__main__":
    asyncio.run(quick_test())
