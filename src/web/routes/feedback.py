"""反馈路由（HTML 页面）"""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(prefix="/feedback", tags=["feedback"])
templates = Jinja2Templates(directory="src/web/templates")


@router.get("/create", response_class=HTMLResponse)
async def create_feedback_page(request: Request):
    """反馈录入页面"""
    return templates.TemplateResponse(
        "feedback/create.html",
        {"request": request}
    )
