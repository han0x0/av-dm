"""
API 数据模型 Schema
"""

from app.api.v1.schemas.task import (
    TaskResponse,
    TaskListResponse,
    TaskFilterParams,
    TaskActionResponse,
    TaskBatchActionRequest,
    TaskBatchActionResponse,
)
from app.api.v1.schemas.stats import (
    StatsResponse,
    RecentStatsResponse,
    DiskUsage,
    WorkflowStatus,
    RecentActivity,
    TaskStatusCount,
)
from app.api.v1.schemas.auth import (
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    UserInfo,
)
from app.api.v1.schemas.config import (
    ConfigResponse,
    WorkflowScheduleConfig,
    JavSPSubmitConfig,
    ConfigBackupInfo,
)
from app.api.v1.schemas.log import (
    LogResponse,
    LogEntry,
    LogFilterParams,
)

__all__ = [
    # Task
    "TaskResponse",
    "TaskListResponse",
    "TaskFilterParams",
    "TaskActionResponse",
    "TaskBatchActionRequest",
    "TaskBatchActionResponse",
    # Stats
    "StatsResponse",
    "RecentStatsResponse",
    "DiskUsage",
    "WorkflowStatus",
    "RecentActivity",
    "TaskStatusCount",
    # Auth
    "LoginRequest",
    "LoginResponse",
    "LogoutResponse",
    "UserInfo",
    # Config
    "ConfigResponse",
    "WorkflowScheduleConfig",
    "JavSPSubmitConfig",
    "ConfigBackupInfo",
    # Log
    "LogResponse",
    "LogEntry",
    "LogFilterParams",
]
