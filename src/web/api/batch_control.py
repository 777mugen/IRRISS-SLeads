"""批处理重试和控制 API"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from src.db.database import get_db
from src.db.models import RawMarkdown
from src.logging_config import get_logger

router = APIRouter(prefix="/api/batch", tags=["batch-control-api"])
logger = get_logger()


class RetryRequest(BaseModel):
    """重试请求"""
    doi: Optional[str] = None
    batch_id: Optional[str] = None
    all_failed: bool = False


class ResetRequest(BaseModel):
    """重置请求"""
    hours: int = 24  # 重置多少小时前卡住的任务


@router.post("/retry")
async def retry_failed_tasks(
    request: RetryRequest,
    db: AsyncSession = Depends(get_db)
):
    """重试失败的任务"""
    try:
        count = 0
        
        if request.doi:
            # 重试单个 DOI
            result = await db.execute(
                update(RawMarkdown)
                .where(RawMarkdown.doi == request.doi)
                .where(RawMarkdown.processing_status == "failed")
                .values(
                    processing_status="pending",
                    retry_count=RawMarkdown.retry_count + 1,
                    last_retry_at=datetime.utcnow()
                )
            )
            count = result.rowcount
            
        elif request.all_failed:
            # 重试所有失败任务
            result = await db.execute(
                update(RawMarkdown)
                .where(RawMarkdown.processing_status == "failed")
                .where(RawMarkdown.retry_count < 3)  # 最多重试 3 次
                .values(
                    processing_status="pending",
                    retry_count=RawMarkdown.retry_count + 1,
                    last_retry_at=datetime.utcnow()
                )
            )
            count = result.rowcount
        
        await db.commit()
        
        logger.info("batch_retry_completed", 
                   doi=request.doi, 
                   all_failed=request.all_failed,
                   count=count)
        
        return {
            "status": "success",
            "retried_count": count
        }
        
    except Exception as e:
        await db.rollback()
        logger.error("batch_retry_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reset-stale")
async def reset_stale_tasks(
    request: ResetRequest,
    db: AsyncSession = Depends(get_db)
):
    """重置卡住的任务（processing 状态超过 N 小时）"""
    try:
        from datetime import datetime, timedelta
        
        threshold = datetime.utcnow() - timedelta(hours=request.hours)
        
        # 重置卡住的 processing 任务
        result = await db.execute(
            update(RawMarkdown)
            .where(RawMarkdown.processing_status == "processing")
            .where(RawMarkdown.updated_at < threshold)
            .values(processing_status="pending")
        )
        
        count = result.rowcount
        await db.commit()
        
        logger.info("batch_reset_completed", 
                   hours=request.hours, 
                   count=count)
        
        return {
            "status": "success",
            "reset_count": count
        }
        
    except Exception as e:
        await db.rollback()
        logger.error("batch_reset_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{batch_id}")
async def get_batch_status(
    batch_id: str,
    db: AsyncSession = Depends(get_db)
):
    """获取批处理状态"""
    try:
        result = await db.execute(
            select(RawMarkdown)
            .where(RawMarkdown.batch_id == batch_id)
        )
        papers = result.scalars().all()
        
        status = {
            "total": len(papers),
            "pending": sum(1 for p in papers if p.processing_status == "pending"),
            "processing": sum(1 for p in papers if p.processing_status == "processing"),
            "completed": sum(1 for p in papers if p.processing_status == "completed"),
            "failed": sum(1 for p in papers if p.processing_status == "failed")
        }
        
        logger.info("batch_status_retrieved", batch_id=batch_id)
        return status
        
    except Exception as e:
        logger.error("batch_status_failed", batch_id=batch_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
