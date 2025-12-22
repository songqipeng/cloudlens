"""
FastAPI 主应用入口
"""

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import logging
import os
from pathlib import Path

# 加载环境变量（从 ~/.cloudlens/.env 文件）
env_file = Path.home() / ".cloudlens" / ".env"
if env_file.exists():
    with open(env_file, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建 FastAPI 应用
app = FastAPI(
    title="CloudLens API",
    description="云资源成本优化与分析平台 API",
    version="2.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 导入并注册路由
try:
    from web.backend.api import router as api_router
    app.include_router(api_router)
    logger.info("API router registered")
except Exception as e:
    logger.error(f"Failed to register API router: {e}")

try:
    from web.backend.api_alerts import router as alerts_router
    app.include_router(alerts_router)
    logger.info("Alerts router registered")
except Exception as e:
    logger.warning(f"Failed to register alerts router: {e}")

try:
    from web.backend.api_cost_allocation import router as cost_allocation_router
    app.include_router(cost_allocation_router)
    logger.info("Cost allocation router registered")
except Exception as e:
    logger.warning(f"Failed to register cost allocation router: {e}")

try:
    from web.backend.api_ai_optimizer import router as ai_optimizer_router
    app.include_router(ai_optimizer_router)
    logger.info("AI optimizer router registered")
except Exception as e:
    logger.warning(f"Failed to register AI optimizer router: {e}")

# OpenAPI 自定义配置
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="CloudLens API",
        version="2.0.0",
        description="云资源成本优化与分析平台 API 文档",
        routes=app.routes,
    )
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

@app.get("/")
async def root():
    """API 根路径"""
    return {
        "name": "CloudLens API",
        "version": "2.0.0",
        "docs": "/docs",
        "redoc": "/redoc"
    }

@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy"}

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """处理404错误，返回更友好的错误信息"""
    return JSONResponse(
        status_code=404,
        content={
            "detail": f"API端点不存在: {request.method} {request.url.path}",
            "error": "Not Found",
            "path": request.url.path,
            "method": request.method
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """处理请求验证错误"""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": exc.errors(),
            "error": "Validation Error",
            "path": request.url.path
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
