"""CSV 导出 API"""
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import date, datetime
import io
import csv

from src.db.database import get_db
from src.db.models import PaperLead
from src.logging_config import get_logger

router = APIRouter(prefix="/api/export", tags=["export-api"])
logger = get_logger()


@router.get("/csv/full")
async def export_full_csv(db: AsyncSession = Depends(get_db)):
    """导出全量 CSV"""
    try:
        # 查询所有论文
        result = await db.execute(
            select(PaperLead).order_by(PaperLead.created_at.desc())
        )
        papers = result.scalars().all()
        
        # 创建 CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # 写入表头
        writer.writerow([
            "DOI", "PMID", "标题", "通讯作者", "邮箱", "电话",
            "地址(英文)", "地址(中文)", "机构(中文)",
            "评分", "等级", "反馈状态", "创建时间"
        ])
        
        # 写入数据
        for paper in papers:
            writer.writerow([
                paper.doi or "",
                paper.pmid or "",
                paper.title or "",
                paper.name or "",
                paper.email or "",
                paper.phone or "",
                paper.address or "",
                paper.address_cn or "",
                paper.institution_cn or "",
                paper.score or 0,
                paper.grade or "",
                paper.feedback_status or "",
                paper.created_at.strftime("%Y-%m-%d %H:%M:%S") if paper.created_at else ""
            ])
        
        # 准备响应
        output.seek(0)
        filename = f"irriss_leads_full_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        logger.info("full_csv_exported", count=len(papers), filename=filename)
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
        
    except Exception as e:
        logger.error("full_csv_export_failed", error=str(e))
        raise


@router.get("/csv/today")
async def export_today_csv(db: AsyncSession = Depends(get_db)):
    """导出今日新增 CSV"""
    try:
        # 查询今日新增
        today = date.today()
        tomorrow = date.today()
        
        result = await db.execute(
            select(PaperLead)
            .where(PaperLead.created_at >= today)
            .where(PaperLead.created_at < tomorrow)
            .order_by(PaperLead.created_at.desc())
        )
        papers = result.scalars().all()
        
        # 创建 CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # 写入表头
        writer.writerow([
            "DOI", "标题", "通讯作者", "邮箱", "评分", "等级", "创建时间"
        ])
        
        # 写入数据
        for paper in papers:
            writer.writerow([
                paper.doi or "",
                paper.title or "",
                paper.name or "",
                paper.email or "",
                paper.grade or "",
                paper.feedback_status or "",
                paper.created_at.strftime("%Y-%m-%d %H:%M:%S") if paper.created_at else ""
            ])
        
        # 准备响应
        output.seek(0)
        filename = f"irriss_leads_today_{today.strftime('%Y%m%d')}.csv"
        
        logger.info("today_csv_exported", count=len(papers), filename=filename)
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
        
    except Exception as e:
        logger.error("today_csv_export_failed", error=str(e))
        raise
