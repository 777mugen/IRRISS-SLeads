"""数据分析路由"""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["analysis"])
templates = Jinja2Templates(directory="src/web/templates")


@router.get("/stats", response_class=HTMLResponse)
async def analysis_stats_page(request: Request):
    """数据分析页面"""
    return templates.TemplateResponse(
        "analysis/stats.html",
        {"request": request}
    )
