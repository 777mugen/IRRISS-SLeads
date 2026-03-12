"""
Database utilities for Sales Lead Discovery System.
数据库工具函数。
"""

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession, 
    create_async_engine, 
    async_sessionmaker
)

from .models import Base


# 从环境变量获取数据库 URL
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql+asyncpg://localhost/sleads_dev"
)

# 创建异步引擎
engine = create_async_engine(DATABASE_URL, echo=False)

# 创建异步会话工厂
async_session_maker = async_sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    获取数据库会话的上下文管理器
    
    Usage:
        async with get_session() as session:
            result = await session.execute(...)
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db():
    """
    初始化数据库（创建所有表）
    注意：生产环境应使用 Alembic 迁移
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """关闭数据库连接池"""
    await engine.dispose()
