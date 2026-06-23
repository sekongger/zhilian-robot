"""
智链机器人 - 后端应用入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from config.settings import settings
import uvicorn
import logging

# 配置日志
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """创建FastAPI应用实例"""
    
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="大模型驱动的产业链图谱自动构建平台",
        debug=settings.DEBUG
    )
    
    # 配置CORS - 允许所有前端来源
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 根路由
    @app.get("/")
    async def root():
        return {
            "message": f"欢迎使用{settings.APP_NAME}",
            "version": settings.APP_VERSION,
            "status": "running"
        }
    
    # 健康检查
    @app.get("/health")
    async def health_check():
        return {"status": "healthy"}
    
    # 注册路由
    from app.api import build_api_router
    app.include_router(build_api_router())
    
    # 启动时初始化数据库连接
    @app.on_event("startup")
    async def startup_event():
        """应用启动事件"""
        from app.database import init_databases
        try:
            init_databases()
            logger.info("数据库连接初始化成功")
        except Exception as e:
            logger.error(f"数据库连接初始化失败: {str(e)}")
    
    # 关闭时清理资源
    @app.on_event("shutdown")
    async def shutdown_event():
        """应用关闭事件"""
        from app.database import close_databases
        close_databases()
        logger.info("数据库连接已关闭")
    
    return app


# 创建应用实例
app = create_app()


if __name__ == "__main__":
    # 使用多worker提高并发处理能力，避免慢请求阻塞
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        workers=1 if settings.DEBUG else 2,  # 生产环境使用2个worker
        timeout_keep_alive=30  # 增加keep-alive超时
    )
