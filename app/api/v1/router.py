"""
API v1 路由聚合
"""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, tasks, stats, workflows, config, logs, services

api_router = APIRouter(prefix="/api/v1")

# 认证相关
api_router.include_router(auth.router, prefix="/auth", tags=["认证"])

# 任务管理
api_router.include_router(tasks.router, prefix="/tasks", tags=["任务管理"])

# 统计信息
api_router.include_router(stats.router, prefix="/stats", tags=["统计"])

# 工作流控制
api_router.include_router(workflows.router, prefix="/workflows", tags=["工作流"])

# 配置管理
api_router.include_router(config.router, prefix="/config", tags=["配置"])

# 服务测试
api_router.include_router(services.router, prefix="/services", tags=["服务测试"])

# 日志查看
api_router.include_router(logs.router, prefix="/logs", tags=["日志"])
