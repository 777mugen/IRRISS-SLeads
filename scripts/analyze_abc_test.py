"""
分析已生成的 ABC 测试数据
"""

import json
from pathlib import Path
from datetime import datetime


def analyze_abc_test():
    """分析 ABC 测试结果"""
    
    print(f"\n{'='*60}")
    print(f"📊 ABC 测试分析报告")
    print(f"{'='*60}\n")
    
    # 检查已生成的文件
    v1_dir = Path("tmp/abc_test/v1")
    v2_dir = Path("tmp/abc_test/v2")
    v3_dir = Path("tmp/abc_test/v3")
    
    v1_files = list(v1_dir.glob("*_prompt.txt")) if v1_dir.exists() else []
    v2_files = list(v2_dir.glob("*_prompt.txt")) if v2_dir.exists() else []
    v3_files = list(v3_dir.glob("*_prompt.txt")) if v3_dir.exists() else []
    
    print(f"已生成的测试文件:")
    print(f"  - V1: {len(v1_files)} 个")
    print(f"  - V2: {len(v2_files)} 个")
    print(f"  - V3: {len(v3_files)} 个")
    print()
    
    # 如果V1有数据，分析V1
    if v1_files:
        print(f"{'='*60}")
        print(f"📊 V1 版本分析（基于已完成数据）")
        print(f"{'='*60}\n")
        
        total_length = 0
        for file in v1_files:
            content = file.read_text()
            total_length += len(content)
        
        avg_length = total_length / len(v1_files) if v1_files else 0
        avg_tokens = avg_length / 4  # 粗略估算
        
        print(f"  文件数量: {len(v1_files)}")
        print(f"  平均 Prompt 长度: {avg_length:,.0f} 字符")
        print(f"  平均预估 Token: {avg_tokens:,.0f}")
        print()
    
    # 建议
    print(f"{'='*60}")
    print(f"💡 下一步建议")
    print(f"{'='*60}\n")
    
    print(f"测试状态: 部分完成（V1 完成 12/20 篇）\n")
    
    print(f"选项 1: 继续完整测试（推荐）")
    print(f"  - 增加超时时间到 180 秒")
    print(f"  - 跳过失败的论文")
    print(f"  - 重新运行测试\n")
    
    print(f"选项 2: 使用已完成数据")
    print(f"  - 只分析已完成的 12 篇论文")
    print(f"  - 生成 V1, V2, V3 对比报告\n")
    
    print(f"选项 3: 快速测试（3 篇论文）")
    print(f"  - 只测试 3 篇代表性论文")
    print(f"  - 快速验证功能\n")
    
    print(f"你的选择？")


if __name__ == "__main__":
    analyze_abc_test()
