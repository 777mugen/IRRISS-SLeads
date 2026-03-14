"""FastAPI 应用入口"""
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

# 导入路由
from src.web.routes import dashboard, batch, query, analysis, config, export
from src.web.api import batch as batch_api
from src.web.api import query as query_api
from src.web.api import export as export_api
from src.web.api import import_csv as import_api

# 创建应用
app = FastAPI(
    title="IRRISS Dashboard",
    description="论文线索管理系统",
    version="1.0.0"
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件
app.mount("/static", StaticFiles(directory="src/web/static"), name="static")

# 模板配置
templates = Jinja2Templates(directory="src/web/templates")

# 注册路由（HTML 页面）
app.include_router(dashboard.router, prefix="", tags=["dashboard"])
app.include_router(batch.router, prefix="/batch", tags=["batch"])
app.include_router(query.router, prefix="/query", tags=["query"])
app.include_router(analysis.router, prefix="/analysis", tags=["analysis"])
app.include_router(config.router, prefix="/config", tags=["config"])
app.include_router(export.router, prefix="/export", tags=["export"])

# 注册 API 路由
app.include_router(batch_api.router, prefix="/api", tags=["batch-api"])
app.include_router(query_api.router, prefix="/api", tags=["query-api"])
app.include_router(export_api.router, prefix="/api", tags=["export-api"])
app.include_router(import_api.router, prefix="/api", tags=["import-api"])


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """根路径重定向到 dashboard"""
    return templates.TemplateResponse(
        "dashboard/index.html",
        {"request": request}
    )


@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
