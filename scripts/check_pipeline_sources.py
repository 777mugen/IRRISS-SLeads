#!/usr/bin/env python3
"""
检查 pipeline_source 字段使用情况
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text, select
from src.db.utils import get_session
from src.db.models import PaperLead, RawMarkdown


async def check_pipeline_sources():
    """检查 pipeline 来源"""
    async with get_session() as session:
        print("=" * 60)
        print("📊 Pipeline 来源统计")
        print("=" * 60)
        
        # 1. paper_leads 表统计
        result = await session.execute(text('''
            SELECT 
                pipeline_source,
                COUNT(*) as count,
                MIN(created_at) as first_created,
                MAX(created_at) as last_created
            FROM paper_leads
            GROUP BY pipeline_source
            ORDER BY count DESC
        '''))
        
        print("\n1️⃣  paper_leads 表:")
        print("-" * 60)
        rows = result.fetchall()
        if rows:
            for row in rows:
                print(f"  {row[0] or '未标记'}: {row[1]} 条")
                print(f"    时间范围: {row[2]} 至 {row[3]}")
        else:
            print("  ⚠️  没有数据")
        
        # 2. raw_markdown 表统计
        result = await session.execute(text('''
            SELECT 
                pipeline_source,
                COUNT(*) as count,
                MIN(created_at) as first_created,
                MAX(created_at) as last_created
            FROM raw_markdown
            GROUP BY pipeline_source
            ORDER BY count DESC
        '''))
        
        print("\n2️⃣  raw_markdown 表:")
        print("-" * 60)
        rows = result.fetchall()
        if rows:
            for row in rows:
                print(f"  {row[0] or '未标记'}: {row[1]} 条")
                print(f"    时间范围: {row[2]} 至 {row[3]}")
        else:
            print("  ⚠️  没有数据")
        
        # 3. 检查重复 DOI
        result = await session.execute(text('''
            SELECT 
                doi,
                COUNT(*) as duplicate_count,
                STRING_AGG(DISTINCT pipeline_source, ', ') as sources
            FROM paper_leads
            WHERE doi IS NOT NULL
            GROUP BY doi
            HAVING COUNT(*) > 1
            ORDER BY duplicate_count DESC
            LIMIT 10
        '''))
        
        print("\n3️⃣  重复 DOI 检查:")
        print("-" * 60)
        rows = result.fetchall()
        if rows:
            print(f"  ⚠️  发现 {len(rows)} 个重复 DOI:")
            for row in rows:
                print(f"    {row[0]}: {row[1]} 次 ({row[2]})")
        else:
            print("  ✅ 没有重复 DOI")
        
        # 4. 对比两个 pipeline 的成功率
        result = await session.execute(text('''
            SELECT 
                rm.pipeline_source,
                COUNT(rm.doi) as total_raw,
                COUNT(pl.doi) as total_leads,
                ROUND(
                    COUNT(pl.doi)::numeric / NULLIF(COUNT(rm.doi), 0) * 100, 
                    2
                ) as success_rate
            FROM raw_markdown rm
            LEFT JOIN paper_leads pl ON rm.doi = pl.doi
            GROUP BY rm.pipeline_source
            ORDER BY total_raw DESC
        '''))
        
        print("\n4️⃣  Pipeline 成功率对比:")
        print("-" * 60)
        rows = result.fetchall()
        if rows:
            for row in rows:
                print(f"  {row[0]}:")
                print(f"    原始内容: {row[1]} 篇")
                print(f"    提取成功: {row[2]} 篇")
                print(f"    成功率: {row[3]}%")
        else:
            print("  ⚠️  没有数据")
        
        print("\n" + "=" * 60)
        print("✅ 检查完成")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(check_pipeline_sources())
