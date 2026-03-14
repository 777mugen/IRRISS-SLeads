"""
快速 ABC 测试（3 篇论文）
验证 V1, V2, V3 三个版本
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.abc_test import run_abc_test


# 快速测试集（3 篇论文）
QUICK_TEST_DOIS = [
    "10.21037/tcr-2025-1389",  # AME 出版社（已验证）
    "10.3389/fonc.2026.1728876",  # Frontiers
    "10.1038/s41556-026-01907-x",  # Nature
]


async def main():
    """运行快速测试"""
    print(f"\n{'='*60}")
    print(f"🚀 快速 ABC 测试（3 篇论文）")
    print(f"{'='*60}\n")
    
    print(f"测试集:")
    for doi in QUICK_TEST_DOIS:
        print(f"  - {doi}")
    print()
    
    await run_abc_test(QUICK_TEST_DOIS)


if __name__ == "__main__":
    asyncio.run(main())
