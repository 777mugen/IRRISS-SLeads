"""销售反馈 API（Web 方式）"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from src.db.database import get_db
from src.db.models import PaperLead, Feedback
from src.logging_config import get_logger

router = APIRouter(prefix="/api/feedback", tags=["feedback-api"])
logger = get_logger()


class FeedbackCreate(BaseModel):
    """反馈创建模型"""
    paper_lead_id: int
    accuracy: Optional[str] = None  # 线索准确性（好/中/差）
    demand_match: Optional[str] = None  # 需求匹配度（好/中/差）
    contact_validity: Optional[str] = None  # 联系方式有效性（好/中/差）
    deal_speed: Optional[str] = None  # 成交速度（好/中/差）
    deal_price: Optional[str] = None  # 成交价格（好/中/差）
    notes: Optional[str] = None  # 备注


class FeedbackUpdate(BaseModel):
    """反馈更新模型"""
    accuracy: Optional[str] = None
    demand_match: Optional[str] = None
    contact_validity: Optional[str] = None
    deal_speed: Optional[str] = None
    deal_price: Optional[str] = None
    notes: Optional[str] = None


@router.post("/")
async def create_feedback(
    feedback_data: FeedbackCreate,
    db: AsyncSession = Depends(get_db)
):
    """创建销售反馈"""
    try:
        # 检查 paper_lead 是否存在
        result = await db.execute(
            select(PaperLead).where(PaperLead.id == feedback_data.paper_lead_id)
        )
        lead = result.scalar_one_or_none()
        
        if not lead:
            raise HTTPException(status_code=404, detail="线索不存在")
        
        # 检查是否已有反馈
        result = await db.execute(
            select(Feedback).where(Feedback.paper_lead_id == feedback_data.paper_lead_id)
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            # 更新现有反馈
            existing.accuracy = feedback_data.accuracy
            existing.demand_match = feedback_data.demand_match
            existing.contact_validity = feedback_data.contact_validity
            existing.deal_speed = feedback_data.deal_speed
            existing.deal_price = feedback_data.deal_price
            existing.notes = feedback_data.notes
            existing.updated_at = datetime.utcnow()
            
            await db.commit()
            
            logger.info("feedback_updated", paper_lead_id=feedback_data.paper_lead_id)
            
            return {
                "status": "success",
                "message": "反馈已更新",
                "feedback_id": existing.id
            }
        else:
            # 创建新反馈
            feedback = Feedback(
                paper_lead_id=feedback_data.paper_lead_id,
                accuracy=feedback_data.accuracy,
                demand_match=feedback_data.demand_match,
                contact_validity=feedback_data.contact_validity,
                deal_speed=feedback_data.deal_speed,
                deal_price=feedback_data.deal_price,
                notes=feedback_data.notes
            )
            
            db.add(feedback)
            
            # 更新 paper_lead 的 feedback_status
            lead.feedback_status = '已反馈'
            
            await db.commit()
            await db.refresh(feedback)
            
            logger.info("feedback_created", paper_lead_id=feedback_data.paper_lead_id)
            
            return {
                "status": "success",
                "message": "反馈已创建",
                "feedback_id": feedback.id
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("feedback_create_failed", error=str(e))
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{feedback_id}")
async def update_feedback(
    feedback_id: int,
    feedback_data: FeedbackUpdate,
    db: AsyncSession = Depends(get_db)
):
    """更新销售反馈"""
    try:
        result = await db.execute(
            select(Feedback).where(Feedback.id == feedback_id)
        )
        feedback = result.scalar_one_or_none()
        
        if not feedback:
            raise HTTPException(status_code=404, detail="反馈不存在")
        
        # 更新字段
        if feedback_data.accuracy is not None:
            feedback.accuracy = feedback_data.accuracy
        if feedback_data.demand_match is not None:
            feedback.demand_match = feedback_data.demand_match
        if feedback_data.contact_validity is not None:
            feedback.contact_validity = feedback_data.contact_validity
        if feedback_data.deal_speed is not None:
            feedback.deal_speed = feedback_data.deal_speed
        if feedback_data.deal_price is not None:
            feedback.deal_price = feedback_data.deal_price
        if feedback_data.notes is not None:
            feedback.notes = feedback_data.notes
        
        feedback.updated_at = datetime.utcnow()
        
        await db.commit()
        
        logger.info("feedback_updated", feedback_id=feedback_id)
        
        return {
            "status": "success",
            "message": "反馈已更新"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("feedback_update_failed", error=str(e))
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{paper_lead_id}")
async def get_feedback(
    paper_lead_id: int,
    db: AsyncSession = Depends(get_db)
):
    """获取线索的反馈"""
    try:
        result = await db.execute(
            select(Feedback).where(Feedback.paper_lead_id == paper_lead_id)
        )
        feedback = result.scalar_one_or_none()
        
        if not feedback:
            return {
                "status": "not_found",
                "message": "暂无反馈"
            }
        
        return {
            "status": "success",
            "feedback": {
                "id": feedback.id,
                "paper_lead_id": feedback.paper_lead_id,
                "accuracy": feedback.accuracy,
                "demand_match": feedback.demand_match,
                "contact_validity": feedback.contact_validity,
                "deal_speed": feedback.deal_speed,
                "deal_price": feedback.deal_price,
                "notes": feedback.notes,
                "created_at": feedback.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "updated_at": feedback.updated_at.strftime("%Y-%m-%d %H:%M:%S")
            }
        }
    
    except Exception as e:
        logger.error("feedback_get_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
