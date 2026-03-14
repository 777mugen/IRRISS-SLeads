"""批处理监控路由"""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["batch"])
templates = Jinja2Templates(directory="src/web/templates")


@router.get("/monitor", response_class=HTMLResponse)
async def batch_monitor_page(request: Request):
    """批处理监控页面"""
    return templates.TemplateResponse(
        "batch/monitor.html",
        {"request": request}
    )
