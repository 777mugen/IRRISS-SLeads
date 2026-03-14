"""CSV 导入 API"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import pandas as pd
import io

from src.db.database import get_db
from src.db.models import PaperLead, Feedback
from src.logging_config import get_logger

router = APIRouter(prefix="/api/import", tags=["import-api"])
logger = get_logger()


class CSVPreviewRequest(BaseModel):
    """CSV 预览请求"""
    csv_content: str


class CSVImportRequest(BaseModel):
    """CSV 导入请求"""
    csv_content: str
    skip_unmatched: bool = True


@router.post("/csv/preview")
async def preview_csv(
    request: CSVPreviewRequest,
    db: AsyncSession = Depends(get_db)
):
    """预览 CSV 导入"""
    try:
        # 解析 CSV
        df = pd.read_csv(io.StringIO(request.csv_content))
        
        # 验证必需列
        required_columns = [
            "DOI", "线索准确性", "需求匹配度",
            "联系方式有效性", "成交速度", "成交价格"
        ]
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            raise HTTPException(
                status_code=400,
                detail=f"缺少必需列: {', '.join(missing_columns)}"
            )
        
        # 统计
        total_rows = len(df)
        matched_dois = []
        unmatched_dois = []
        
        # 批量检查 DOI 是否存在（1 次查询替代 N 次）
        dois = df["DOI"].tolist()
        result = await db.execute(
            select(PaperLead.doi, PaperLead.id)
            .where(PaperLead.doi.in_(dois))
        )
        existing_dois = {row.doi for row in result.fetchall()}
        
        # 分类匹配和未匹配的 DOI
        for doi in dois:
            if doi in existing_dois:
                matched_dois.append(doi)
            else:
                unmatched_dois.append(doi)
        
        logger.info("csv_preview_completed",
                   total=total_rows,
                   matched=len(matched_dois),
                   unmatched=len(unmatched_dois))
        
        return {
            "total_rows": total_rows,
            "matched_count": len(matched_dois),
            "unmatched_count": len(unmatched_dois),
            "matched_dois": matched_dois[:10],
            "unmatched_dois": unmatched_dois[:10],
            "preview_data": df.head(5).to_dict('records')
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("csv_preview_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/csv/confirm")
async def confirm_import(
    request: CSVImportRequest,
    db: AsyncSession = Depends(get_db)
):
    """确认导入反馈数据"""
    try:
        # 解析 CSV
        df = pd.read_csv(io.StringIO(request.csv_content))
        
        imported_count = 0
        skipped_count = 0
        
        # 批量查询所有 DOI（1 次查询替代 N 次）
        dois = df["DOI"].tolist()
        result = await db.execute(
            select(PaperLead.id, PaperLead.doi)
            .where(PaperLead.doi.in_(dois))
        )
        paper_ids = {row.doi: row.id for row in result.fetchall()}
        
        # 准备批量插入
        feedbacks = []
        
        for _, row in df.iterrows():
            doi = row["DOI"]
            paper_id = paper_ids.get(doi)
            
            if not paper_id:
                if request.skip_unmatched:
                    skipped_count += 1
                    continue
                else:
                    raise HTTPException(status_code=404, detail=f"DOI 不存在: {doi}")
            
            # 创建反馈记录
            feedback = Feedback(
                paper_lead_id=paper_id,
                accuracy=row["线索准确性"],
                demand_match=row["需求匹配度"],
                contact_validity=row["联系方式有效性"],
                deal_speed=row["成交速度"],
                deal_price=row["成交价格"],
                notes=row.get("备注", "")
            )
            
            feedbacks.append(feedback)
            imported_count += 1
        
        # 批量插入（1 次提交替代 N 次）
        if feedbacks:
            db.add_all(feedbacks)
            await db.commit()
        
        # 提交事务
        await db.commit()
        
        logger.info("feedback_imported",
                   imported=imported_count,
                   skipped=skipped_count)
        
        return {
            "imported": imported_count,
            "skipped": skipped_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("feedback_import_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
