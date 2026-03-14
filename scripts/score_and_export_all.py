"""
对所有 paper_leads 进行评分并导出 CSV
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import asyncio
from datetime import datetime
from sqlalchemy import select

from src.db.models import PaperLead
from src.db.utils import get_session
from src.scoring.paper_scorer import PaperScorer
from src.exporters.csv_exporter import CSVExporter


async def score_and_export_all():
    """对所有 paper_leads 进行评分并导出 CSV"""
    
    print(f"\n{'='*60}")
    print(f"📊 对所有 paper_leads 进行评分并导出 CSV")
    print(f"{'='*60}\n")
    
    # Step 1: 读取所有 paper_leads
    print(f"📝 Step 1: 读取所有 paper_leads...")
    
    async with get_session() as session:
        stmt = select(PaperLead)
        result = await session.execute(stmt)
        leads = result.scalars().all()
        
        print(f"✅ 读取到 {len(leads)} 条记录\n")
        
        if not leads:
            print(f"❌ 数据库中没有记录")
            return
        
        # Step 2: 评分
        print(f"📊 Step 2: 对所有线索进行评分...")
        
        scorer = PaperScorer()
        scored_leads = []
        
        for i, lead in enumerate(leads, 1):
            # 转换为字典
            lead_dict = {
                'doi': lead.doi,
                'title': lead.title,
                'published_at': lead.published_at,
                'name': lead.name,
                'email': lead.email,
                'phone': lead.phone,
                'address': lead.address,
                'institution': lead.address,  # 使用 address 作为 institution
                'feedback_status': lead.feedback_status,
                'keywords_matched': [],  # 暂时为空
            }
            
            # 计算分数
            score = scorer.calculate_score(lead_dict)
            
            # 确定等级
            if score >= 80:
                grade = 'A'
            elif score >= 65:
                grade = 'B'
            elif score >= 50:
                grade = 'C'
            else:
                grade = 'D'
            
            # 更新数据库
            lead.score = score
            lead.grade = grade
            
            # 准备导出数据
            lead_dict['score'] = score
            lead_dict['grade'] = grade
            lead_dict['article_url'] = lead.article_url
            lead_dict['source'] = lead.source
            lead_dict['all_authors'] = None  # 暂时为空
            
            scored_leads.append(lead_dict)
            
            if i % 5 == 0 or i == len(leads):
                print(f"  进度: {i}/{len(leads)}")
        
        await session.commit()
        print(f"✅ 评分完成，已更新到数据库\n")
        
        # Step 3: 导出 CSV
        print(f"📤 Step 3: 导出 CSV...")
        
        exporter = CSVExporter(output_dir="output")
        
        # 导出论文线索
        csv_path = exporter.export_paper_leads(scored_leads, include_diff=True)
        
        print(f"✅ CSV 已导出: {csv_path}\n")
        
        # Step 4: 统计
        print(f"📊 Step 4: 统计评分结果...")
        
        grade_counts = {'A': 0, 'B': 0, 'C': 0, 'D': 0}
        for lead in scored_leads:
            grade_counts[lead['grade']] += 1
        
        print(f"  - A 级 (>=80): {grade_counts['A']} 条")
        print(f"  - B 级 (65-79): {grade_counts['B']} 条")
        print(f"  - C 级 (50-64): {grade_counts['C']} 条")
        print(f"  - D 级 (<50): {grade_counts['D']} 条")
        print()
        
        # Step 5: 验证 CSV 文件
        print(f"🔍 Step 5: 验证 CSV 文件...")
        
        import csv as csv_module
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv_module.reader(f)
            rows = list(reader)
            
            print(f"  - 总行数: {len(rows)} (包含标题行)")
            print(f"  - 标题行: {rows[0][:5]}...")
            print(f"  - 第一条数据: {rows[1][:5]}...")
        
        print(f"\n{'='*60}")
        print(f"✅ 所有任务完成")
        print(f"{'='*60}\n")
        
        print(f"📊 总结:")
        print(f"  - 评分记录数: {len(scored_leads)}")
        print(f"  - CSV 文件路径: {csv_path}")
        print(f"  - CSV 总行数: {len(rows)}")


if __name__ == "__main__":
    asyncio.run(score_and_export_all())
