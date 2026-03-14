"""DOI 查询路由"""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["query"])
templates = Jinja2Templates(directory="src/web/templates")


@router.get("/query/search", response_class=HTMLResponse)
async def query_search_page(request: Request):
    """DOI 查询页面"""
    return templates.TemplateResponse(
        "query/search.html",
        {"request": request}
    )
