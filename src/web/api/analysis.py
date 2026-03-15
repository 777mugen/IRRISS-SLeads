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
        
        # 地区分布（从 address_cn 提取省份，Top 20）
        import re
        
        # 获取所有有地址的线索
        address_result = await db.execute(
            select(PaperLead.address_cn).where(PaperLead.address_cn != None)
        )
        addresses = [addr for (addr,) in address_result.fetchall() if addr]
        
        # 提取省份信息
        province_counter = Counter()
        province_pattern = re.compile(
            r'(北京|天津|上海|重庆|河北|山西|辽宁|吉林|黑龙江|江苏|浙江|安徽|福建|江西|山东|河南|湖北|湖南|广东|海南|四川|贵州|云南|陕西|甘肃|青海|台湾|内蒙古|广西|西藏|宁夏|新疆|香港|澳门)'
        )
        
        for address in addresses:
            match = province_pattern.search(address)
            if match:
                province = match.group(1)
                province_counter[province] += 1
        
        # 转换为 Top 20 格式
        province_distribution = [
            {"name": province, "count": count}
            for province, count in province_counter.most_common(20)
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
            "province_distribution": province_distribution,  # 改名
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
