"""配置管理 API"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Any
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.database import get_db
from src.web.services.config_service import ConfigService
from src.logging_config import get_logger

router = APIRouter(prefix="/api/config", tags=["config-api"])
logger = get_logger()


class KeywordsUpdate(BaseModel):
    """关键词更新请求"""
    english: List[str]
    chinese: List[str]
    core: List[str]
    equipment: List[str]


class ScoringUpdate(BaseModel):
    """评分规则更新请求"""
    weights: Dict[str, float]
    thresholds: Dict[str, int]


@router.get("/keywords")
async def get_keywords(
    service: ConfigService = Depends()
) -> Dict[str, Any]:
    """获取关键词配置"""
    try:
        keywords = await service.get_keywords()
        logger.info("config_keywords_retrieved")
        return keywords
    except Exception as e:
        logger.error("config_keywords_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/keywords")
async def update_keywords(
    update: KeywordsUpdate,
    service: ConfigService = Depends()
) -> Dict[str, str]:
    """更新关键词配置"""
    try:
        await service.update_keywords(update.dict())
        logger.info("config_keywords_updated")
        return {"status": "success"}
    except Exception as e:
        logger.error("config_keywords_update_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scoring")
async def get_scoring_rules(
    service: ConfigService = Depends()
) -> Dict[str, Any]:
    """获取评分规则"""
    try:
        scoring = await service.get_scoring_rules()
        logger.info("config_scoring_retrieved")
        return scoring
    except Exception as e:
        logger.error("config_scoring_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/scoring")
async def update_scoring_rules(
    update: ScoringUpdate,
    service: ConfigService = Depends()
) -> Dict[str, str]:
    """更新评分规则"""
    try:
        await service.update_scoring_rules(update.dict())
        logger.info("config_scoring_updated")
        return {"status": "success"}
    except Exception as e:
        logger.error("config_scoring_update_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
