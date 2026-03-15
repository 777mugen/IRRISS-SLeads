"""批处理统计 API"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from src.db.database import get_db
from src.db.models import RawMarkdown
from src.logging_config import get_logger

router = APIRouter(prefix="/api/batch", tags=["batch-api"])
logger = get_logger()


@router.get("/stats")
async def get_batch_stats(db: AsyncSession = Depends(get_db)):
    """获取批处理统计数据"""
    try:
        # 统计各状态的论文数量
        result = await db.execute(
            select(
                RawMarkdown.processing_status,
                func.count(RawMarkdown.id).label('count')
            )
            .group_by(RawMarkdown.processing_status)
        )
        
        stats = {
            "pending": 0,
            "processing": 0,
            "completed": 0,
            "failed": 0
        }
        
        for row in result:
            status = row.processing_status or "pending"
            if status in stats:
                stats[status] = row.count
        
        logger.info("batch_stats_retrieved", stats=stats)
        return stats
        
    except Exception as e:
        logger.error("batch_stats_failed", error=str(e))
        return {
            "pending": 0,
            "processing": 0,
            "completed": 0,
            "failed": 0
        }


@router.get("/failed-list")
async def get_failed_papers(db: AsyncSession = Depends(get_db)):
    """获取失败的论文列表"""
    try:
        result = await db.execute(
            select(RawMarkdown)
            .where(RawMarkdown.processing_status == "failed")
            .order_by(RawMarkdown.updated_at.desc())
            .limit(20)
        )
        
        papers = result.scalars().all()
        
        failed_list = []
        for paper in papers:
            failed_list.append({
                "doi": paper.doi,
                "error": paper.error_message or "未知错误",
                "processed_at": paper.processed_at.strftime("%Y-%m-%d %H:%M:%S") if paper.processed_at else None
            })
        
        logger.info("failed_papers_retrieved", count=len(failed_list))
        return {"papers": failed_list}
        
    except Exception as e:
        logger.error("failed_papers_retrieval_failed", error=str(e))
        return {"papers": []
