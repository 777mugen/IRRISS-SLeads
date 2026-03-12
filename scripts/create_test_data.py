"""
测试批量处理 - 创建模拟数据
"""

import asyncio
from src.db.models import RawMarkdown
from src.db.utils import get_session
from src.logging_config import get_logger


async def create_test_data():
    """
    创建 3 篇模拟测试论文
    """
    logger = get_logger()
    
    print("\n" + "="*60)
    print("🧪 创建测试数据")
    print("="*60)
    
    # 模拟 3 篇论文的 Markdown 内容
    test_papers = [
        {
            'doi': '10.1016/j.test.2024.001',
            'pmid': '12345678',
            'markdown': """
# Multiplex Immunofluorescence for Tumor Analysis

**Published**: 2024-03-15

## Abstract

This paper presents a novel multiplex immunofluorescence (mIF) method for simultaneous detection of multiple biomarkers in tumor tissue samples.

## Authors

- **John Smith** - Department of Pathology, Harvard Medical School
- **Jane Doe** (Corresponding Author) - Department of Oncology, Stanford University
  - Email: jane.doe@stanford.edu
  - Phone: +1-650-123-4567
  - Address: 300 Pasteur Drive, Stanford, CA 94305

## Introduction

Multiplex immunofluorescence (mIF) is a powerful technique...

## Methods

We used a panel of 6 antibodies...

## Results

Our method achieved 95% sensitivity...

## Conclusion

This mIF approach provides comprehensive tumor profiling...

## References

1. Smith J, et al. (2023) Cancer Res.
2. Doe J, et al. (2022) Nat Med.
""",
            'url': 'https://doi.org/10.1016/j.test.2024.001'
        },
        {
            'doi': '10.1038/s41591-024-002',
            'pmid': '12345679',
            'markdown': """
# Spatial Proteomics Analysis of Tumor Microenvironment

**Published**: 2024-02-20

## Correspondence

**Corresponding Author**: Bob Johnson, PhD  
**Affiliation**: Department of Immunology, MIT  
**Email**: bob.johnson@mit.edu  
**Phone**: +1-617-987-6543  
**Address**: 77 Massachusetts Avenue, Cambridge, MA 02139

## Abstract

We developed a spatial proteomics approach to analyze the tumor microenvironment...

## Authors

1. Alice Brown - MIT
2. Bob Johnson (Corresponding) - MIT
3. Carol White - MIT

## Introduction

The tumor microenvironment (TME) plays a crucial role...

## Results

We identified 15 distinct cell populations...

## Discussion

Our findings reveal new insights into TME composition...

## References

[Multiple references listed here...]
""",
            'url': 'https://doi.org/10.1038/s41591-024-002'
        },
        {
            'doi': '10.1126/science.2024.003',
            'pmid': '12345680',
            'markdown': """
# Single-Cell Analysis of Immune Cells

**Published**: 2024-01-10

## Abstract

Single-cell RNA sequencing reveals heterogeneity in immune cell populations...

## Contact Information

**Corresponding Author**:  
**Name**: David Lee, MD, PhD  
**Institution**: Department of Medicine, Johns Hopkins University  
**Email**: david.lee@jhmi.edu  
**Phone**: +1-410-955-1234  
**Address**: 733 N Broadway, Baltimore, MD 21205

## Authors

David Lee¹*, Emily Chen¹, Michael Zhang¹

¹ Johns Hopkins University  
* Corresponding author

## Introduction

Immune cell heterogeneity is a key factor...

## Methods

We performed scRNA-seq on 10,000 cells...

## Results

We identified 8 major cell types...

## Discussion

Our results provide a comprehensive map...

## Acknowledgments

This work was supported by NIH grant...

## References

1. Lee D, et al. (2023) Cell
2. Chen E, et al. (2022) Nature
""",
            'url': 'https://doi.org/10.1126/science.2024.003'
        }
    ]
    
    print(f"\n📝 准备插入 {len(test_papers)} 篇测试论文...")
    
    async with get_session() as session:
        for i, paper in enumerate(test_papers, 1):
            # 检查是否已存在
            from sqlalchemy import select
            result = await session.execute(
                select(RawMarkdown).where(RawMarkdown.doi == paper['doi'])
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                print(f"  [{i}/3] DOI {paper['doi']} - 已存在，跳过")
                continue
            
            raw = RawMarkdown(
                doi=paper['doi'],
                pmid=paper['pmid'],
                markdown_content=paper['markdown'],
                source_url=paper['url'],
                processing_status='pending'
            )
            session.add(raw)
            print(f"  [{i}/3] DOI {paper['doi']} - ✅ 插入")
        
        await session.commit()
    
    print(f"\n✅ 测试数据创建完成！")
    
    # 检查数据库状态
    from sqlalchemy import func
    async with get_session() as session:
        result = await session.execute(
            select(
                RawMarkdown.processing_status,
                func.count(RawMarkdown.id)
            ).group_by(RawMarkdown.processing_status)
        )
        
        stats = dict(result.all())
        print(f"\n📊 数据库状态:")
        for status, count in stats.items():
            print(f"  - {status}: {count}")
        
        total = sum(stats.values())
        print(f"  - 总计: {total}")
    
    print("\n" + "="*60)
    print("✅ 准备就绪，可以开始测试批量提取！")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(create_test_data())
