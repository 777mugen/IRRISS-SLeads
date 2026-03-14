"""
测试截断功能
验证截断函数是否能正确提取元数据部分
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.processors.content_truncator import ContentTruncator


def test_truncation():
    """测试截断功能"""
    
    # 读取之前保存的原始内容
    content_file = Path("tmp/jina_raw_data.txt")
    if not content_file.exists():
        print(f"❌ 文件不存在: {content_file}")
        print(f"请先运行 scripts/test_jina_raw_data.py 生成测试数据")
        return
    
    original_content = content_file.read_text()
    
    print(f"\n{'='*60}")
    print(f"🧪 测试截断功能")
    print(f"{'='*60}\n")
    
    # 1. 显示原始内容长度
    original_length = len(original_content)
    print(f"📝 原始内容长度: {original_length:,} 字符")
    
    # 2. 执行截断
    truncator = ContentTruncator()
    truncated_content = truncator.extract_metadata_section(original_content)
    truncated_length = len(truncated_content)
    reduction = 100 * (1 - truncated_length / original_length)
    
    print(f"✂️  截断后长度: {truncated_length:,} 字符")
    print(f"📊 减少: {reduction:.1f}%")
    print()
    
    # 3. 检查关键信息是否保留
    print(f"{'='*60}")
    print(f"🔍 检查关键信息")
    print(f"{'='*60}\n")
    
    checks = [
        ("作者全名", "Zhilan Huang"),
        ("机构地址", "Fourth Clinical Medical College"),
        ("通讯作者", "Wei Xie"),
        ("邮箱", "xiew0703@163.com"),
        ("共同第一作者标注", "#"),
        ("发表日期", "2026"),
    ]
    
    for name, keyword in checks:
        if keyword in truncated_content:
            print(f"✅ {name}: 保留")
        else:
            print(f"❌ {name}: 丢失")
    
    print()
    
    # 4. 检查是否去除了学术内容
    print(f"{'='*60}")
    print(f"🔍 检查学术内容是否去除")
    print(f"{'='*60}\n")
    
    academic_keywords = [
        "Introduction",
        "Methods",
        "Methodology",
        "Results",
        "Discussion",
    ]
    
    for keyword in academic_keywords:
        # 检查是否有独立的标题（## Introduction）
        if f"## {keyword}" in truncated_content or f"# {keyword}" in truncated_content:
            print(f"❌ {keyword}: 未去除（找到标题）")
        elif keyword in truncated_content:
            # 可能在其他地方出现（如作者介绍中提到）
            print(f"⚠️  {keyword}: 部分保留（可能在其他上下文）")
        else:
            print(f"✅ {keyword}: 已去除")
    
    print()
    
    # 5. 保存截断后的内容
    output_file = Path("tmp/truncated_content.txt")
    with open(output_file, 'w') as f:
        f.write(truncated_content)
    
    print(f"📄 截断后的内容已保存到: {output_file}")
    print()
    
    # 6. 显示前 500 字符
    print(f"{'='*60}")
    print(f"📖 截断后内容（前 500 字符）")
    print(f"{'='*60}\n")
    print(truncated_content[:500])
    print(f"\n... (总共 {truncated_length:,} 字符)")
    print()


if __name__ == "__main__":
    test_truncation()
