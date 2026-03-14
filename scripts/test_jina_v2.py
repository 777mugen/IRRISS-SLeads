"""
测试 Jina API 新参数配置
"""

import sys
import asyncio
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.crawlers.jina_client import JinaClient


async def test_jina_v2():
    """测试 Jina API v2 参数配置"""
    
    print(f"\n{'='*60}")
    print(f"🧪 测试 Jina API 新参数配置")
    print(f"{'='*60}\n")
    
    doi_url = "https://doi.org/10.21037/tcr-2025-1389"
    
    async with JinaClient() as client:
        # 使用新方法
        print(f"📝 测试 URL: {doi_url}")
        print(f"📥 开始提取...")
        
        content = await client.read_paper(doi_url)
        
        print(f"✅ 提取完成")
        print(f"总长度: {len(content)} 字符\n")
        
        # 查找关键信息
        print(f"{'='*60}")
        print(f"🔍 关键信息验证")
        print(f"{'='*60}\n")
        
        # 1. 查找作者全名
        if "Zhilan Huang" in content:
            print(f"✅ 找到作者全名: Zhilan Huang")
        else:
            print(f"❌ 未找到作者全名")
        
        # 2. 查找机构地址
        if "Fourth Clinical Medical College" in content or "Guangzhou University of Chinese Medicine" in content:
            print(f"✅ 找到机构地址")
        else:
            print(f"❌ 未找到机构地址")
        
        # 3. 查找通讯作者
        if "Wei Xie" in content and "Correspondence to" in content:
            print(f"✅ 找到通讯作者: Wei Xie")
        else:
            print(f"❌ 未找到通讯作者")
        
        # 4. 查找邮箱
        if "xiew0703@163.com" in content:
            print(f"✅ 找到邮箱: xiew0703@163.com")
        else:
            print(f"❌ 未找到邮箱")
        
        # 5. 查找共同第一作者标注
        if "#" in content and "contributed equally" in content:
            print(f"✅ 找到共同第一作者标注")
        else:
            print(f"❌ 未找到共同第一作者标注")
        
        print()
        
        # 保存到文件
        output_file = Path("tmp/jina_v2_content.txt")
        with open(output_file, 'w') as f:
            f.write(content)
        
        print(f"📄 完整内容已保存到: {output_file}")
        print(f"\n{'='*60}")


if __name__ == "__main__":
    asyncio.run(test_jina_v2())
