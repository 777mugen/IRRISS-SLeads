"""
A/B 测试脚本
对比 v1（当前版本）和 v2（新版本）的提取效果

使用相同的测试集，对比：
1. Token 消耗
2. 提取准确性
3. 处理速度
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.crawlers.jina_client import JinaClient
from src.processors.content_truncator import ContentTruncator
from src.llm.batch_client import ZhiPuBatchClient
from src.logging_config import get_logger


# 测试集（10 篇论文，不同期刊）
TEST_DOIS = [
    "10.21037/tcr-2025-1389",  # AME 出版社
    # 添加更多 DOI...
]

# Prompt v1（当前版本）
PROMPT_V1 = Path("docs/Batch Prompt v2.md").read_text()

# Prompt v2（新版本）
PROMPT_V2 = Path("docs/Batch Prompt v3 (Simplified).md").read_text()


async def fetch_paper_content(doi: str) -> str:
    """爬取论文内容"""
    async with JinaClient() as client:
        doi_url = f"https://doi.org/{doi}"
        content = await client.read_paper(doi_url)
        return content


def truncate_content_v1(content: str) -> str:
    """v1 版本：不截断"""
    return content


def truncate_content_v2(content: str) -> str:
    """v2 版本：精准截断"""
    truncator = ContentTruncator()
    return truncator.extract_metadata_section(content)


async def test_version(version: str, dois: list[str], prompt: str, truncate_func):
    """
    测试一个版本
    
    Args:
        version: 版本名称（v1 或 v2）
        dois: 测试 DOI 列表
        prompt: Prompt 内容
        truncate_func: 截断函数
    """
    logger = get_logger()
    
    print(f"\n{'='*60}")
    print(f"🧪 测试版本: {version}")
    print(f"{'='*60}\n")
    
    results = []
    
    for doi in dois:
        print(f"📝 处理 DOI: {doi}")
        
        # 1. 爬取原始内容
        print(f"  Step 1: 爬取原始内容...")
        original_content = await fetch_paper_content(doi)
        original_length = len(original_content)
        print(f"  ✅ 原始长度: {original_length:,} 字符")
        
        # 2. 截断内容
        print(f"  Step 2: 截断内容...")
        truncated_content = truncate_func(original_content)
        truncated_length = len(truncated_content)
        reduction = 100 * (1 - truncated_length / original_length)
        print(f"  ✅ 截断后长度: {truncated_length:,} 字符 (减少 {reduction:.1f}%)")
        
        # 3. 准备 Prompt
        print(f"  Step 3: 准备 Prompt...")
        full_prompt = prompt.replace("{content}", truncated_content)
        prompt_length = len(full_prompt)
        print(f"  ✅ Prompt 长度: {prompt_length:,} 字符")
        
        # 4. 保存结果
        result = {
            'doi': doi,
            'original_length': original_length,
            'truncated_length': truncated_length,
            'reduction': reduction,
            'prompt_length': prompt_length,
        }
        results.append(result)
        
        # 5. 保存到文件（用于后续检查）
        output_dir = Path(f"tmp/ab_test/{version}")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 保存截断后的内容
        with open(output_dir / f"{doi.replace('/', '_')}_truncated.txt", 'w') as f:
            f.write(truncated_content)
        
        # 保存完整的 Prompt
        with open(output_dir / f"{doi.replace('/', '_')}_prompt.txt", 'w') as f:
            f.write(full_prompt)
        
        print(f"  ✅ 结果已保存到: {output_dir}\n")
    
    # 统计
    print(f"\n{'='*60}")
    print(f"📊 {version} 统计")
    print(f"{'='*60}\n")
    
    avg_original = sum(r['original_length'] for r in results) / len(results)
    avg_truncated = sum(r['truncated_length'] for r in results) / len(results)
    avg_reduction = sum(r['reduction'] for r in results) / len(results)
    avg_prompt = sum(r['prompt_length'] for r in results) / len(results)
    
    print(f"  平均原始长度: {avg_original:,.0f} 字符")
    print(f"  平均截断后长度: {avg_truncated:,.0f} 字符")
    print(f"  平均减少: {avg_reduction:.1f}%")
    print(f"  平均 Prompt 长度: {avg_prompt:,.0f} 字符")
    print(f"  预估 Token: {avg_prompt / 4:.0f} (按 1 token ≈ 4 chars)")
    
    return {
        'version': version,
        'avg_original': avg_original,
        'avg_truncated': avg_truncated,
        'avg_reduction': avg_reduction,
        'avg_prompt': avg_prompt,
        'results': results
    }


async def run_ab_test():
    """运行 A/B 测试"""
    logger = get_logger()
    
    print(f"\n{'='*60}")
    print(f"🚀 开始 A/B 测试")
    print(f"{'='*60}\n")
    
    print(f"测试集: {len(TEST_DOIS)} 篇论文")
    print(f"版本:")
    print(f"  - v1: 当前版本（不截断 + 长 Prompt）")
    print(f"  - v2: 新版本（精准截断 + 精简 Prompt）")
    print()
    
    # 测试 v1
    v1_stats = await test_version(
        version="v1",
        dois=TEST_DOIS,
        prompt=PROMPT_V1,
        truncate_func=truncate_content_v1
    )
    
    # 测试 v2
    v2_stats = await test_version(
        version="v2",
        dois=TEST_DOIS,
        prompt=PROMPT_V2,
        truncate_func=truncate_content_v2
    )
    
    # 对比结果
    print(f"\n{'='*60}")
    print(f"📊 A/B 测试对比")
    print(f"{'='*60}\n")
    
    print(f"{'指标':<20} {'v1':<20} {'v2':<20} {'差异':<20}")
    print(f"{'-'*80}")
    
    # 原始长度
    print(f"{'平均原始长度':<20} {v1_stats['avg_original']:>18,.0f} {v2_stats['avg_original']:>18,.0f} {'相同':>18}")
    
    # 截断后长度
    diff_truncated = v2_stats['avg_truncated'] - v1_stats['avg_truncated']
    print(f"{'平均截断后长度':<20} {v1_stats['avg_truncated']:>18,.0f} {v2_stats['avg_truncated']:>18,.0f} {diff_truncated:>18,.0f}")
    
    # 减少比例
    print(f"{'平均减少':<20} {v1_stats['avg_reduction']:>17.1f}% {v2_stats['avg_reduction']:>17.1f}% {v2_stats['avg_reduction'] - v1_stats['avg_reduction']:>17.1f}%")
    
    # Prompt 长度
    diff_prompt = v2_stats['avg_prompt'] - v1_stats['avg_prompt']
    prompt_reduction = 100 * (1 - v2_stats['avg_prompt'] / v1_stats['avg_prompt'])
    print(f"{'平均 Prompt 长度':<20} {v1_stats['avg_prompt']:>18,.0f} {v2_stats['avg_prompt']:>18,.0f} {diff_prompt:>18,.0f}")
    
    # Token 预估
    v1_tokens = v1_stats['avg_prompt'] / 4
    v2_tokens = v2_stats['avg_prompt'] / 4
    diff_tokens = v2_tokens - v1_tokens
    token_reduction = 100 * (1 - v2_tokens / v1_tokens)
    print(f"{'预估 Token':<20} {v1_tokens:>18,.0f} {v2_tokens:>18,.0f} {diff_tokens:>18,.0f}")
    
    print()
    
    # 保存对比结果
    comparison = {
        'timestamp': datetime.now().isoformat(),
        'test_dois': TEST_DOIS,
        'v1': v1_stats,
        'v2': v2_stats,
        'comparison': {
            'truncated_reduction': v2_stats['avg_reduction'] - v1_stats['avg_reduction'],
            'prompt_reduction': prompt_reduction,
            'token_reduction': token_reduction,
        }
    }
    
    output_file = Path("tmp/ab_test/comparison.json")
    with open(output_file, 'w') as f:
        json.dump(comparison, f, indent=2, ensure_ascii=False)
    
    print(f"📄 对比结果已保存到: {output_file}")
    print()
    
    # 建议
    print(f"{'='*60}")
    print(f"💡 建议")
    print(f"{'='*60}\n")
    
    if token_reduction > 80:
        print(f"✅ Token 减少超过 80%，v2 版本显著优于 v1")
    elif token_reduction > 50:
        print(f"✅ Token 减少超过 50%，v2 版本明显优于 v1")
    else:
        print(f"⚠️ Token 减少不足 50%，需要进一步优化")
    
    print(f"\n下一步：")
    print(f"1. 使用浏览器打开原始论文")
    print(f"2. 对比 v1 和 v2 的提取结果")
    print(f"3. 检查准确性")
    print(f"4. 根据结果优化")


if __name__ == "__main__":
    asyncio.run(run_ab_test())
