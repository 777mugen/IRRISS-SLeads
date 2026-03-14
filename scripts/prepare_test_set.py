"""
准备测试集
从数据库中选择 20 篇论文
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import select
from src.db.models import PaperLead
from src.db.utils import get_session


async def prepare_test_set():
    """准备测试集"""
    
    print(f"\n{'='*60}")
    print(f"📊 准备测试集")
    print(f"{'='*60}\n")
    
    async with get_session() as session:
        # 查询所有论文
        result = await session.execute(
            select(PaperLead)
            .order_by(PaperLead.created_at.desc())
            .limit(20)
        )
        papers = result.scalars().all()
        
        print(f"找到 {len(papers)} 篇论文\n")
        
        # 提取 DOI
        dois = []
        for paper in papers:
            if paper.doi:
                # 提取 DOI 编号
                doi = paper.doi.replace("https://doi.org/", "")
                dois.append(doi)
                print(f"  - {doi}")
            else:
                print(f"  - {paper.title[:50]}... (无 DOI)")
        
        print()
        
        # 保存到文件
        output_file = Path("tmp/test_dois.txt")
        with open(output_file, 'w') as f:
            for doi in dois:
                f.write(f"{doi}\n")
        
        print(f"✅ 测试集已保存到: {output_file}")
        print(f"   共 {len(dois)} 个 DOI")
        print()
        
        # 生成 Python 代码
        print(f"Python 代码:")
        print(f"TEST_DOIS = [")
        for doi in dois:
            print(f'    "{doi}",')
        print(f"]")


if __name__ == "__main__":
    asyncio.run(prepare_test_set())
