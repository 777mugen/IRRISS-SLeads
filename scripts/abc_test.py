"""
三版本对比测试
V1: 不截断 + 长 Prompt
V2: 截断 + 精简 Prompt
V3: 截断 + 长 Prompt

测试 20 篇论文，对比：
1. Token 消耗
2. 提取准确性
3. 处理速度
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Callable

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.crawlers.jina_client import JinaClient
from src.processors.content_truncator import ContentTruncator
from src.logging_config import get_logger


# 测试集（20 篇论文，不同期刊）
TEST_DOIS = [
    "10.1021/acs.jmedchem.5c03498",  # J. Med. Chem.
    "10.3389/fonc.2026.1728876",  # Frontiers in Oncology
    "10.1097/CM9.0000000000004035",  # Chinese Medical Journal
    "10.1021/jacsau.5c01509",  # JACS Au
    "10.3389/fcimb.2026.1747682",  # Frontiers in Cellular and Infection Microbiology
    "10.7150/thno.124789",  # Theranostics
    "10.1136/jitc-2025-014040",  # Journal for ImmunoTherapy of Cancer
    "10.3748/wjg.v32.i9.115259",  # World Journal of Gastroenterology
    "10.2196/86322",  # JMIR
    "10.1038/s41556-026-01907-x",  # Nature Cell Biology
    "10.4103/bc.bc_65_24",  # Blood Cancer
    "10.21037/jgo-2025-750",  # Journal of Gastrointestinal Oncology
    "10.1007/s43630-026-00863-7",  # Biochimica et Biophysica Acta
    "10.1158/0008-5472.CAN-25-3806",  # Cancer Research
    "10.1186/s13058-026-02251-6",  # Breast Cancer Research
    "10.21037/tcr-2025-1389",  # Translational Cancer Research
    "10.21037/tcr-2025-1-2580",  # Translational Cancer Research
    "10.21037/tcr-2025-aw-2287",  # Translational Cancer Research
    "10.32604/or.2026.071122",  # Oncology Reports
    "10.1158/2159-8290.CD-25-1907",  # Cancer Discovery
]

# 快速测试（只测试 1 篇论文）
QUICK_TEST_DOIS = ["10.21037/tcr-2025-1389"]

# Prompt 文件
PROMPT_V1_FILE = "docs/Batch Prompt v2.md"  # V1 使用长 Prompt
PROMPT_V2_FILE = "docs/Batch Prompt v3 (Simplified).md"  # V2 使用精简 Prompt
PROMPT_V3_FILE = "docs/Batch Prompt v2.md"  # V3 使用长 Prompt（同 V1）


class VersionTest:
    """版本测试类"""
    
    def __init__(
        self,
        version_name: str,
        truncate_func: Callable[[str], str],
        prompt_file: str
    ):
        self.version_name = version_name
        self.truncate_func = truncate_func
        self.prompt_file = prompt_file
        self.logger = get_logger()
        
        # 加载 Prompt
        self.prompt = Path(prompt_file).read_text()
    
    async def test_single_paper(self, doi: str) -> Dict:
        """
        测试单篇论文
        
        Returns:
            测试结果
        """
        print(f"  📝 处理 DOI: {doi}")
        
        # 1. 爬取原始内容
        print(f"    Step 1: 爬取原始内容...")
        async with JinaClient() as client:
            doi_url = f"https://doi.org/{doi}"
            original_content = await client.read_paper(doi_url)
        
        original_length = len(original_content)
        print(f"    ✅ 原始长度: {original_length:,} 字符")
        
        # 2. 截断内容
        print(f"    Step 2: 截断内容...")
        truncated_content = self.truncate_func(original_content)
        truncated_length = len(truncated_content)
        reduction = 100 * (1 - truncated_length / original_length) if original_length > 0 else 0
        print(f"    ✅ 截断后长度: {truncated_length:,} 字符 (减少 {reduction:.1f}%)")
        
        # 3. 准备 Prompt
        print(f"    Step 3: 准备 Prompt...")
        full_prompt = self.prompt.replace("{content}", truncated_content)
        prompt_length = len(full_prompt)
        print(f"    ✅ Prompt 长度: {prompt_length:,} 字符")
        
        # 4. 预估 Token
        estimated_tokens = prompt_length / 4  # 粗略估算
        print(f"    ✅ 预估 Token: {estimated_tokens:,.0f}")
        
        # 5. 保存结果
        output_dir = Path(f"tmp/abc_test/{self.version_name}")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 保存截断后的内容
        with open(output_dir / f"{doi.replace('/', '_')}_truncated.txt", 'w') as f:
            f.write(truncated_content)
        
        # 保存完整的 Prompt
        with open(output_dir / f"{doi.replace('/', '_')}_prompt.txt", 'w') as f:
            f.write(full_prompt)
        
        print(f"    ✅ 结果已保存到: {output_dir}\n")
        
        return {
            'doi': doi,
            'original_length': original_length,
            'truncated_length': truncated_length,
            'reduction': reduction,
            'prompt_length': prompt_length,
            'estimated_tokens': estimated_tokens,
        }
    
    async def test_batch(self, dois: List[str]) -> Dict:
        """
        测试批量论文
        
        Returns:
            统计结果
        """
        print(f"\n{'='*60}")
        print(f"🧪 测试版本: {self.version_name}")
        print(f"{'='*60}\n")
        
        results = []
        
        for doi in dois:
            result = await self.test_single_paper(doi)
            results.append(result)
        
        # 统计
        print(f"\n{'='*60}")
        print(f"📊 {self.version_name} 统计")
        print(f"{'='*60}\n")
        
        avg_original = sum(r['original_length'] for r in results) / len(results)
        avg_truncated = sum(r['truncated_length'] for r in results) / len(results)
        avg_reduction = sum(r['reduction'] for r in results) / len(results)
        avg_prompt = sum(r['prompt_length'] for r in results) / len(results)
        avg_tokens = sum(r['estimated_tokens'] for r in results) / len(results)
        
        print(f"  平均原始长度: {avg_original:,.0f} 字符")
        print(f"  平均截断后长度: {avg_truncated:,.0f} 字符")
        print(f"  平均减少: {avg_reduction:.1f}%")
        print(f"  平均 Prompt 长度: {avg_prompt:,.0f} 字符")
        print(f"  平均预估 Token: {avg_tokens:,.0f}")
        
        return {
            'version': self.version_name,
            'prompt_file': self.prompt_file,
            'avg_original': avg_original,
            'avg_truncated': avg_truncated,
            'avg_reduction': avg_reduction,
            'avg_prompt': avg_prompt,
            'avg_tokens': avg_tokens,
            'results': results
        }


# 截断函数
def truncate_v1(content: str) -> str:
    """V1: 不截断"""
    return content


def truncate_v2_v3(content: str) -> str:
    """V2/V3: 精准截断"""
    truncator = ContentTruncator()
    return truncator.extract_metadata_section(content)


async def run_abc_test(dois: List[str]):
    """
    运行 A/B/C 测试
    
    Args:
        dois: 测试 DOI 列表
    """
    logger = get_logger()
    
    print(f"\n{'='*60}")
    print(f"🚀 开始 A/B/C 测试")
    print(f"{'='*60}\n")
    
    print(f"测试集: {len(dois)} 篇论文")
    print(f"版本:")
    print(f"  - V1: 不截断 + 长 Prompt（当前版本）")
    print(f"  - V2: 截断 + 精简 Prompt")
    print(f"  - V3: 截断 + 长 Prompt（测试截断效果）")
    print()
    
    # 测试 V1
    v1_test = VersionTest(
        version_name="v1",
        truncate_func=truncate_v1,
        prompt_file=PROMPT_V1_FILE
    )
    v1_stats = await v1_test.test_batch(dois)
    
    # 测试 V2
    v2_test = VersionTest(
        version_name="v2",
        truncate_func=truncate_v2_v3,
        prompt_file=PROMPT_V2_FILE
    )
    v2_stats = await v2_test.test_batch(dois)
    
    # 测试 V3
    v3_test = VersionTest(
        version_name="v3",
        truncate_func=truncate_v2_v3,
        prompt_file=PROMPT_V3_FILE
    )
    v3_stats = await v3_test.test_batch(dois)
    
    # 对比结果
    print(f"\n{'='*60}")
    print(f"📊 A/B/C 测试对比")
    print(f"{'='*60}\n")
    
    print(f"{'指标':<25} {'V1':<20} {'V2':<20} {'V3':<20}")
    print(f"{'-'*85}")
    
    # 原始长度
    print(f"{'平均原始长度':<25} {v1_stats['avg_original']:>18,.0f} {v2_stats['avg_original']:>18,.0f} {v3_stats['avg_original']:>18,.0f}")
    
    # 截断后长度
    print(f"{'平均截断后长度':<25} {v1_stats['avg_truncated']:>18,.0f} {v2_stats['avg_truncated']:>18,.0f} {v3_stats['avg_truncated']:>18,.0f}")
    
    # 减少比例
    print(f"{'平均减少':<25} {v1_stats['avg_reduction']:>17.1f}% {v2_stats['avg_reduction']:>17.1f}% {v3_stats['avg_reduction']:>17.1f}%")
    
    # Prompt 长度
    print(f"{'平均 Prompt 长度':<25} {v1_stats['avg_prompt']:>18,.0f} {v2_stats['avg_prompt']:>18,.0f} {v3_stats['avg_prompt']:>18,.0f}")
    
    # Token 预估
    print(f"{'平均预估 Token':<25} {v1_stats['avg_tokens']:>18,.0f} {v2_stats['avg_tokens']:>18,.0f} {v3_stats['avg_tokens']:>18,.0f}")
    
    # Token 减少
    v2_token_reduction = 100 * (1 - v2_stats['avg_tokens'] / v1_stats['avg_tokens'])
    v3_token_reduction = 100 * (1 - v3_stats['avg_tokens'] / v1_stats['avg_tokens'])
    
    print(f"{'Token 减少 (vs V1)':<25} {'-':>18} {v2_token_reduction:>17.1f}% {v3_token_reduction:>17.1f}%")
    
    print()
    
    # 保存对比结果
    comparison = {
        'timestamp': datetime.now().isoformat(),
        'test_dois': dois,
        'v1': v1_stats,
        'v2': v2_stats,
        'v3': v3_stats,
        'comparison': {
            'v2_token_reduction': v2_token_reduction,
            'v3_token_reduction': v3_token_reduction,
        }
    }
    
    output_file = Path("tmp/abc_test/comparison.json")
    with open(output_file, 'w') as f:
        json.dump(comparison, f, indent=2, ensure_ascii=False)
    
    print(f"📄 对比结果已保存到: {output_file}")
    print()
    
    # 建议
    print(f"{'='*60}")
    print(f"💡 建议")
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
    print(f"3. 对比 V1, V2, V3 的提取结果")
    print(f"4. 检查准确性")
    print(f"5. 根据结果选择最优版本")


if __name__ == "__main__":
    # 使用测试集
    if len(TEST_DOIS) == 0:
        print(f"❌ 测试集为空，请先添加测试 DOI")
        print(f"\n建议：")
        print(f"1. 从数据库中选择 20 篇不同期刊的论文")
        print(f"2. 更新 TEST_DOIS 列表")
        print(f"3. 重新运行测试")
        sys.exit(1)
    
    asyncio.run(run_abc_test(TEST_DOIS))
