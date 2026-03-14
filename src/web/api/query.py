"""DOI 查询 API"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.db.database import get_db
from src.db.models import RawMarkdown, PaperLead
from src.logging_config import get_logger

router = APIRouter(prefix="/api/query", tags=["query-api"])
logger = get_logger()


class DOIQuery(BaseModel):
    """DOI 查询请求"""
    dois: List[str]


@router.post("/doi")
async def query_by_dois(
    request: DOIQuery,
    db: AsyncSession = Depends(get_db)
):
    """批量查询 DOI"""
    try:
        results = []
        
        for doi in request.dois:
            doi = doi.strip()
            if not doi:
                continue
            
            # 查询 raw_markdown
            raw_result = await db.execute(
                select(RawMarkdown).where(RawMarkdown.doi == doi)
            )
            raw = raw_result.scalar_one_or_none()
            
            # 查询 paper_leads
            lead_result = await db.execute(
                select(PaperLead).where(PaperLead.doi == doi)
            )
            lead = lead_result.scalar_one_or_none()
            
            result = {
                "doi": doi,
                "raw_markdown": None,
                "paper_lead": None
            }
            
            if raw:
                result["raw_markdown"] = {
                    "status": raw.processing_status,
                    "created_at": raw.created_at.strftime("%Y-%m-%d %H:%M:%S") if raw.created_at else None,
                    "updated_at": raw.updated_at.strftime("%Y-%m-%d %H:%M:%S") if raw.updated_at else None
                }
            
            if lead:
                result["paper_lead"] = {
                    "name": lead.name,
                    "email": lead.email,
                    "phone": lead.phone,
                    "institution_cn": lead.institution_cn,
                    "score": lead.score,
                    "grade": lead.grade,
                    "feedback_status": lead.feedback_status
                }
            
            results.append(result)
        
        logger.info("doi_query_completed", query_count=len(request.dois), result_count=len(results))
        return {"results": results}
        
    except Exception as e:
        logger.error("doi_query_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/paper/{doi}")
async def get_paper_detail(
    doi: str,
    db: AsyncSession = Depends(get_db)
):
    """获取单篇论文详情"""
    try:
        # 查询 paper_lead
        result = await db.execute(
            select(PaperLead).where(PaperLead.doi == doi)
        )
        paper = result.scalar_one_or_none()
        
        if not paper:
            raise HTTPException(status_code=404, detail="论文不存在")
        
        detail = {
            "doi": paper.doi,
            "pmid": paper.pmid,
            "title": paper.title,
            "name": paper.name,
            "email": paper.email,
            "phone": paper.phone,
            "address": paper.address,
            "address_cn": paper.address_cn,
            "institution_cn": paper.institution_cn,
            "score": paper.score,
            "grade": paper.grade,
            "feedback_status": paper.feedback_status,
            "created_at": paper.created_at.strftime("%Y-%m-%d %H:%M:%S") if paper.created_at else None
        }
        
        logger.info("paper_detail_retrieved", doi=doi)
        return detail
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("paper_detail_failed", doi=doi, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
