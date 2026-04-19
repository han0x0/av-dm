"""
AV Download Manager - 主入口

集成调度器和 FastAPI Web API
"""

import asyncio
import signal
import sys
from typing import List

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from pytz import timezone
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from app.config import settings
from app.database import init_db
from app.logger import logger
from app.workflows import DownloadWorkflow, MonitorWorkflow, CleanupWorkflow
from app.api.v1 import api_router
from app.api.v1.endpoints.workflows import set_scheduler


# 创建 FastAPI 应用
fastapi_app = FastAPI(
    title=settings.app_name,
    description="AV Download Manager Web API",
    version="0.1.3",
)


# 公开的健康检查端点（不需要认证）
@fastapi_app.get("/health", tags=["健康检查"])
async def health_check():
    """
    健康检查端点
    
    用于 Docker 健康检查和负载均衡检测
    """
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": "0.1.3"
    }

# 配置 CORS
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源，生产环境应限制
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册 API 路由
fastapi_app.include_router(api_router)

# 调试：打印所有注册的路由
for route in fastapi_app.routes:
    if hasattr(route, 'methods'):
        logger.info(f"API 路由: {route.methods} {route.path}")


class Application:
    """应用主类"""
    
    def __init__(self):
        self.scheduler: AsyncIOScheduler = AsyncIOScheduler(timezone=timezone('Asia/Shanghai'))
        self.running = False
        self.web_server = None
        
    def setup_signal_handlers(self):
        """设置信号处理器"""
        for sig in (signal.SIGINT, signal.SIGTERM):
            asyncio.get_event_loop().add_signal_handler(sig, self.shutdown)
    
    def shutdown(self):
        """优雅关闭"""
        logger.info("收到关闭信号，正在停止...")
        self.running = False
        if self.scheduler.running:
            self.scheduler.shutdown()
    
    async def run_workflow1(self):
        """执行 Workflow 1: 处理 Starred Items"""
        try:
            async with DownloadWorkflow() as workflow:
                stats = await workflow.run()
                logger.info(f"Workflow 1 统计: {stats}")
        except Exception as e:
            logger.exception(f"Workflow 1 执行异常: {e}")
    
    async def run_workflow2(self):
        """执行 Workflow 2: 状态监控"""
        try:
            async with MonitorWorkflow() as workflow:
                stats = await workflow.run()
                logger.info(f"Workflow 2 统计: {stats}")
        except Exception as e:
            logger.exception(f"Workflow 2 执行异常: {e}")
    
    async def run_workflow3(self):
        """执行 Workflow 3 & 4: 空间管理和清理"""
        try:
            async with CleanupWorkflow() as workflow:
                stats = await workflow.run()
                logger.info(f"Workflow 3/4 统计: {stats}")
        except Exception as e:
            logger.exception(f"Workflow 3/4 执行异常: {e}")
    
    def setup_scheduler(self):
        """配置调度器"""
        # Workflow 1: 每 10 分钟执行一次
        self.scheduler.add_job(
            self.run_workflow1,
            trigger=IntervalTrigger(minutes=settings.workflow1_interval_minutes),
            id="workflow1",
            name="处理 Starred Items",
            replace_existing=True,
            max_instances=1,
        )
        logger.info(f"Workflow 1 已调度，间隔: {settings.workflow1_interval_minutes} 分钟")
        
        # Workflow 2: 每 30 分钟执行一次
        self.scheduler.add_job(
            self.run_workflow2,
            trigger=IntervalTrigger(minutes=settings.workflow2_interval_minutes),
            id="workflow2",
            name="状态监控",
            replace_existing=True,
            max_instances=1,
        )
        logger.info(f"Workflow 2 已调度，间隔: {settings.workflow2_interval_minutes} 分钟")
        
        # Workflow 3/4: 每60分钟执行一次
        self.scheduler.add_job(
            self.run_workflow3,
            trigger=IntervalTrigger(minutes=settings.workflow3_interval_minutes),
            id="workflow3",
            name="空间管理与清理",
            replace_existing=True,
            max_instances=1,
        )
        logger.info(f"Workflow 3/4 已调度，间隔: {settings.workflow3_interval_minutes} 分钟")
        
        # 向 API 模块传递调度器引用
        set_scheduler(self.scheduler)
    
    async def start_web_server(self):
        """启动 Web API 服务器"""
        # FastAPI 固定监听 8080（Nginx 代理到此端口）
        config = uvicorn.Config(
            app=fastapi_app,
            host="0.0.0.0",
            port=8080,
            log_level="warning",  # 使用 warning 级别避免重复日志
            access_log=False,
        )
        server = uvicorn.Server(config)
        await server.serve()
    
    async def run_once(self, workflow_names: List[str] = None):
        """
        立即执行一次指定工作流（用于测试或手动触发）
        
        Args:
            workflow_names: 要执行的工作流名称列表 ['w1', 'w2', 'w3']，None 表示全部
        """
        all_workflows = {
            'w1': self.run_workflow1,
            'w2': self.run_workflow2,
            'w3': self.run_workflow3,
        }
        
        if workflow_names is None:
            workflow_names = ['w1', 'w2', 'w3']
        
        for name in workflow_names:
            if name in all_workflows:
                logger.info(f"手动触发 {name}...")
                await all_workflows[name]()
            else:
                logger.warning(f"未知工作流: {name}")
    
    async def start(self):
        """启动应用"""
        logger.info("=" * 60)
        logger.info(f"启动 {settings.app_name}")
        logger.info("=" * 60)
        
        # 初始化数据库
        init_db()
        
        # 设置调度器
        self.setup_scheduler()
        self.scheduler.start()
        
        # 设置信号处理器
        self.setup_signal_handlers()
        
        self.running = True
        logger.info("调度器已启动")
        logger.info(f"Web API 服务即将启动于端口 {getattr(settings, 'web_port', 8080)}")
        
        # 同时运行调度器和 Web 服务器
        try:
            await asyncio.gather(
                self._keep_alive(),
                self.start_web_server(),
            )
        except asyncio.CancelledError:
            pass
        finally:
            logger.info("应用已停止")
    
    async def _keep_alive(self):
        """保持调度器运行"""
        while self.running:
            await asyncio.sleep(1)


async def main():
    """主函数"""
    app = Application()
    await app.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("用户中断")
        sys.exit(0)
