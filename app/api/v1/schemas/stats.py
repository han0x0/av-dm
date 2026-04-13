"""
统计相关 Schema
"""

from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, Field


class DiskUsage(BaseModel):
    """磁盘使用情况"""
    total: int = Field(..., description="总空间(字节)")
    used: int = Field(..., description="已用空间(字节)")
    free: int = Field(..., description="剩余空间(字节)")
    percent: float = Field(..., description="使用百分比")


class WorkflowStatus(BaseModel):
    """工作流状态"""
    name: str = Field(..., description="工作流名称")
    display_name: str = Field(..., description="显示名称")
    status: str = Field(..., description="状态: running/stopped")
    last_run: Optional[datetime] = Field(None, description="上次执行时间")
    next_run: Optional[datetime] = Field(None, description="下次执行时间")
    interval: str = Field(..., description="执行间隔")


class RecentActivity(BaseModel):
    """近期活动"""
    id: int = Field(..., description="记录ID")
    content_id: str = Field(..., description="番号")
    action: str = Field(..., description="操作类型")
    status: str = Field(..., description="状态")
    message: Optional[str] = Field(None, description="消息")
    created_at: datetime = Field(..., description="时间")


class TaskStatusCount(BaseModel):
    """任务状态统计"""
    status: str = Field(..., description="状态")
    count: int = Field(..., description="数量")


class StatsResponse(BaseModel):
    """统计信息响应"""
    # 任务统计
    total_tasks: int = Field(..., description="总任务数")
    running_tasks: int = Field(..., description="进行中")
    pending_tasks: int = Field(..., description="等待中")
    completed_tasks: int = Field(..., description="已完成")
    failed_tasks: int = Field(..., description="失败")
    timeout_tasks: int = Field(..., description="超时")
    
    # 今日统计
    completed_today: int = Field(..., description="今日完成")
    created_today: int = Field(..., description="今日创建")
    
    # 状态分布
    status_distribution: List[TaskStatusCount] = Field(..., description="状态分布")
    
    # 磁盘使用
    disk_usage: Optional[DiskUsage] = Field(None, description="磁盘使用")
    
    # 工作流状态
    workflow_status: List[WorkflowStatus] = Field(..., description="工作流状态")


class RecentStatsResponse(BaseModel):
    """近期活动响应"""
    activities: List[RecentActivity] = Field(..., description="活动列表")
    total: int = Field(..., description="总数")
