"""
统计信息 API
"""

from datetime import datetime, timedelta
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.auth import get_current_active_user, User
from app.database import get_db, DownloadRecord
from app.api.v1.schemas import (
    StatsResponse,
    DiskUsage,
    WorkflowStatus,
    TaskStatusCount,
    RecentActivity,
    RecentStatsResponse,
)
from app.config import settings
from app.logger import logger
import shutil

router = APIRouter()


@router.get("", response_model=StatsResponse)
async def get_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    获取系统统计信息
    """
    # 任务总数统计
    total_tasks = db.query(DownloadRecord).count()
    running_tasks = db.query(DownloadRecord).filter(
        DownloadRecord.status == "running"
    ).count()
    pending_tasks = db.query(DownloadRecord).filter(
        DownloadRecord.status == "pending"
    ).count()
    completed_tasks = db.query(DownloadRecord).filter(
        DownloadRecord.status == "completed"
    ).count()
    failed_tasks = db.query(DownloadRecord).filter(
        DownloadRecord.status.in_(["error", "javsp_error"])
    ).count()
    timeout_tasks = db.query(DownloadRecord).filter(
        DownloadRecord.status == "timeout"
    ).count()
    
    # 今日统计
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    completed_today = db.query(DownloadRecord).filter(
        DownloadRecord.status == "completed",
        DownloadRecord.updated_at >= today_start
    ).count()
    created_today = db.query(DownloadRecord).filter(
        DownloadRecord.created_at >= today_start
    ).count()
    
    # 状态分布
    status_counts = db.query(
        DownloadRecord.status,
        func.count(DownloadRecord.id).label("count")
    ).group_by(DownloadRecord.status).all()
    
    status_distribution = [
        TaskStatusCount(status=s.status, count=s.count)
        for s in status_counts
    ]
    
    # 磁盘使用（如果有权限访问）
    disk_usage = None
    try:
        stat = shutil.disk_usage(settings.bitcomet_download_path)
        disk_usage = DiskUsage(
            total=stat.total,
            used=stat.used,
            free=stat.free,
            percent=round(stat.used / stat.total * 100, 2)
        )
    except Exception as e:
        logger.debug(f"无法获取磁盘使用信息: {e}")
    
    # 工作流状态（从调度器获取，这里返回配置信息）
    workflow_status = [
        WorkflowStatus(
            name="workflow1",
            display_name="处理 Starred Items",
            status="running",
            interval=f"{settings.workflow1_interval_minutes} 分钟"
        ),
        WorkflowStatus(
            name="workflow2",
            display_name="状态监控",
            status="running",
            interval=f"{settings.workflow2_interval_minutes} 分钟"
        ),
        WorkflowStatus(
            name="workflow3",
            display_name="空间管理与清理",
            status="running",
            interval=f"{settings.workflow3_interval_hours} 小时"
        ),
    ]
    
    return StatsResponse(
        total_tasks=total_tasks,
        running_tasks=running_tasks,
        pending_tasks=pending_tasks,
        completed_tasks=completed_tasks,
        failed_tasks=failed_tasks,
        timeout_tasks=timeout_tasks,
        completed_today=completed_today,
        created_today=created_today,
        status_distribution=status_distribution,
        disk_usage=disk_usage,
        workflow_status=workflow_status,
    )


@router.get("/recent", response_model=RecentStatsResponse)
async def get_recent_activities(
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    获取近期活动
    
    返回最近更新的任务记录
    """
    records = db.query(DownloadRecord).order_by(
        DownloadRecord.updated_at.desc()
    ).limit(limit).all()
    
    activities = []
    for r in records:
        # 根据状态确定动作
        action = "创建"
        if r.status == "completed":
            action = "完成"
        elif r.status in ["error", "javsp_error"]:
            action = "失败"
        elif r.status == "running":
            action = "开始下载"
        elif r.status == "timeout":
            action = "超时"
        
        activities.append(RecentActivity(
            id=r.id,
            content_id=r.content_id,
            action=action,
            status=r.status,
            message=r.error_message,
            created_at=r.updated_at
        ))
    
    return RecentStatsResponse(
        activities=activities,
        total=len(activities)
    )
