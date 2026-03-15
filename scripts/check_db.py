#!/usr/bin/env python3
"""检查数据库连接和数据"""
import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from src.db.utils import async_session_maker


async def check_database():
    """检查数据库连接和数据"""
    async with async_session_maker() as session:
        try:
            # 测试连接
            result = await session.execute(text("SELECT 1"))
            print("✅ 数据库连接成功")
            
            # 检查表是否存在
            tables = await session.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """))
            print(f"\n📋 数据库表:")
            for (table_name,) in tables:
                print(f"  - {table_name}")
            
            # 检查 raw_markdown 数据
            result = await session.execute(text("SELECT COUNT(*) FROM raw_markdown"))
            count = result.scalar()
            print(f"\n📊 raw_markdown 记录数: {count}")
            
            # 检查 paper_leads 数据
            result = await session.execute(text("SELECT COUNT(*) FROM paper_leads"))
            count = result.scalar()
            print(f"📊 paper_leads 记录数: {count}")
            
            # 检查状态分布
            if count > 0:
                result = await session.execute(text("""
                    SELECT processing_status, COUNT(*) 
                    FROM raw_markdown 
                    GROUP BY processing_status
                """))
                print(f"\n📈 状态分布:")
                for status, cnt in result:
                    print(f"  - {status}: {cnt}")
            
        except Exception as e:
            print(f"❌ 错误: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(check_database())
