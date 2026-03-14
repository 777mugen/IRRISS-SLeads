"""导入导出路由"""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from datetime import date

router = APIRouter(tags=["export"])
templates = Jinja2Templates(directory="src/web/templates")


@router.get("/export", response_class=HTMLResponse)
async def export_page(request: Request):
    """导入导出页面"""
    return templates.TemplateResponse(
        "export/index.html",
        {
            "request": request,
            "today_date": date.today().strftime("%Y-%m-%d")
        }
    )
