"""配置管理路由"""
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from src.web.services.config_service import ConfigService

router = APIRouter(prefix="/config", tags=["config"])
templates = Jinja2Templates(directory="src/web/templates")


def get_config_service() -> ConfigService:
    """获取配置服务实例"""
    return ConfigService()


@router.get("/", response_class=HTMLResponse)
async def config_page(
    request: Request,
    service: ConfigService = Depends(get_config_service)
):
    """配置管理页面"""
    # 获取配置数据
    keywords = await service.get_keywords()
    scoring = await service.get_scoring_rules()
    
    return templates.TemplateResponse(
        "config/keywords.html",
        {
            "request": request,
            "keywords": keywords,
            "scoring": scoring
        }
    )
