#!/usr/bin/env python3
"""
P2 修复验证脚本
验证所有修复是否正确应用
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from src.db.utils import get_session
from src.logging_config import get_logger


async def verify_p2_fixes():
    """验证 P2 修复"""
    logger = get_logger()
    
    print("\n" + "=" * 60)
    print("🔍 P2 修复验证")
    print("=" * 60)
    
    async with get_session() as session:
        # 1. 验证字段注释（通过查询表结构）
        print("\n1️⃣  验证字段是否存在")
        print("-" * 60)
        
        result = await session.execute(text("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'paper_leads'
              AND column_name = 'pipeline_source'
        """))
        
        row = result.fetchone()
        if row:
            print(f"✅ paper_leads.pipeline_source 存在（类型: {row[1]}）")
        else:
            print("❌ paper_leads.pipeline_source 不存在")
        
        result = await session.execute(text("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'raw_markdown'
              AND column_name = 'pipeline_source'
        """))
        
        row = result.fetchone()
        if row:
            print(f"✅ raw_markdown.pipeline_source 存在（类型: {row[1]}）")
        else:
            print("❌ raw_markdown.pipeline_source 不存在")
        
        # 2. 验证索引
        print("\n2️⃣  验证索引是否存在")
        print("-" * 60)
        
        result = await session.execute(text("""
            SELECT indexname
            FROM pg_indexes
            WHERE tablename IN ('paper_leads', 'raw_markdown')
              AND indexname LIKE '%pipeline_source%'
        """))
        
        rows = result.fetchall()
        if rows:
            for row in rows:
                print(f"✅ 索引: {row[0]}")
        else:
            print("❌ 没有找到 pipeline_source 相关索引")
        
        # 3. 验证历史数据回填
        print("\n3️⃣  验证历史数据回填")
        print("-" * 60)
        
        result = await session.execute(text("""
            SELECT 
                COUNT(*) as total,
                COUNT(pipeline_source) as tagged,
                COUNT(*) - COUNT(pipeline_source) as untagged
            FROM paper_leads
            WHERE created_at < '2026-03-15 00:00:00'
        """))
        
        row = result.fetchone()
        print(f"paper_leads 旧数据:")
        print(f"  总数: {row[0]}")
        print(f"  已标记: {row[1]}")
        print(f"  未标记: {row[2]}")
        
        if row[2] == 0:
            print("  ✅ 所有旧数据已标记")
        else:
            print(f"  ⚠️  仍有 {row[2]} 条旧数据未标记")
        
        # 4. 验证数据完整性
        print("\n4️⃣  验证数据完整性")
        print("-" * 60)
        
        result = await session.execute(text("""
            SELECT 
                pipeline_source,
                COUNT(*) as count
            FROM paper_leads
            WHERE pipeline_source IS NOT NULL
            GROUP BY pipeline_source
        """))
        
        rows = result.fetchall()
        if rows:
            print("Pipeline 分布:")
            for row in rows:
                print(f"  {row[0]}: {row[1]} 条")
        else:
            print("⚠️  没有找到已标记的数据")
        
        # 5. 检查是否有无效值
        print("\n5️⃣  检查无效值")
        print("-" * 60)
        
        result = await session.execute(text("""
            SELECT DISTINCT pipeline_source
            FROM paper_leads
            WHERE pipeline_source IS NOT NULL
              AND pipeline_source NOT IN ('pipeline_v1_jina', 'pipeline_v2_zhipu_reader')
        """))
        
        invalid = result.fetchall()
        if invalid:
            print(f"⚠️  发现无效值:")
            for row in invalid:
                print(f"  - {row[0]}")
        else:
            print("✅ 没有发现无效值")
    
    print("\n" + "=" * 60)
    print("✅ 验证完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(verify_p2_fixes())
