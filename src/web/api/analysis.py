"""数据分析 API"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Dict, List
from collections import Counter

from src.db.database import get_db
from src.db.models import PaperLead, Feedback
from src.logging_config import get_logger

router = APIRouter(prefix="/api/analysis", tags=["analysis-api"])
logger = get_logger()


@router.get("/stats")
async def get_analysis_stats(db: AsyncSession = Depends(get_db)):
    """获取分析统计数据"""
    try:
        # 总论文数
        total_result = await db.execute(
            select(func.count(PaperLead.id))
        )
        total_papers = total_result.scalar() or 0
        
        # 有效线索数（有邮箱的）
        leads_result = await db.execute(
            select(func.count(PaperLead.id)).where(PaperLead.email != None)
        )
        total_leads = leads_result.scalar() or 0
        
        # 评分分布
        score_result = await db.execute(
            select(PaperLead.score).where(PaperLead.score != None)
        )
        scores = [s for (s,) in score_result.fetchall() if s]
        
        score_distribution = {}
        for score in scores:
            if score >= 80:
                bucket = "80-100"
            elif score >= 60:
                bucket = "60-79"
            elif score >= 40:
                bucket = "40-59"
            else:
                bucket = "0-39"
            score_distribution[bucket] = score_distribution.get(bucket, 0) + 1
        
        # 机构分布（Top 20）
        institution_result = await db.execute(
            select(PaperLead.institution_cn, func.count(PaperLead.id))
            .where(PaperLead.institution_cn != None)
            .group_by(PaperLead.institution_cn)
            .order_by(func.count(PaperLead.id).desc())
            .limit(20)
        )
        institution_distribution = [
            {"name": inst, "count": count}
            for inst, count in institution_result.fetchall()
        ]
        
        # 反馈统计
        feedback_result = await db.execute(
            select(Feedback).where(Feedback.id != None)
        )
        feedbacks = feedback_result.scalars().all()
        
        feedback_stats = {
            "accuracy": analyze_feedback(feedbacks, "accuracy"),
            "demand": analyze_feedback(feedbacks, "demand_match"),
            "contact": analyze_feedback(feedbacks, "contact_validity"),
            "speed": analyze_feedback(feedbacks, "deal_speed"),
            "price": analyze_feedback(feedbacks, "deal_price")
        }
        
        logger.info("analysis_stats_retrieved",
                   total_papers=total_papers,
                   total_leads=total_leads)
        
        return {
            "total_papers": total_papers,
            "total_leads": total_leads,
            "score_distribution": score_distribution,
            "institution_distribution": institution_distribution,
            "feedback_stats": feedback_stats
        }
        
    except Exception as e:
        logger.error("analysis_stats_failed", error=str(e))
        raise


def analyze_feedback(feedbacks: List[Feedback], field: str) -> Dict[str, int]:
    """分析反馈数据"""
    values = []
    for fb in feedbacks:
        value = getattr(fb, field, None)
        if value:
            values.append(value)
    
    counter = Counter(values)
    
    return {
        "good": counter.get("好", 0),
        "medium": counter.get("中", 0),
        "poor": counter.get("差", 0)
    }
