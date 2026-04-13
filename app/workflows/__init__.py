"""
工作流层 - 实现业务逻辑

包含三个核心工作流:
- download: Workflow 1 - 处理 Starred Items
- monitor: Workflow 2 - 状态监控 & JavSP 整理
- cleanup: Workflow 3 & 4 - 空间管理 & 清理
"""

from app.workflows.download import DownloadWorkflow
from app.workflows.monitor import MonitorWorkflow
from app.workflows.cleanup import CleanupWorkflow

__all__ = ["DownloadWorkflow", "MonitorWorkflow", "CleanupWorkflow"]
