"""
任务管理 API
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc, or_

from app.core.auth import get_current_active_user, User
from app.database import get_db, DownloadRecord
from app.api.v1.schemas import (
    TaskResponse,
    TaskListResponse,
    TaskFilterParams,
    TaskActionResponse,
)
from app.logger import logger

router = APIRouter()


def get_sort_column(sort_by: str):
    """获取排序列"""
    sort_map = {
        "id": DownloadRecord.id,
        "content_id": DownloadRecord.content_id,
        "status": DownloadRecord.status,
        "created_at": DownloadRecord.created_at,
        "updated_at": DownloadRecord.updated_at,
        "progress": DownloadRecord.progress,
    }
    return sort_map.get(sort_by, DownloadRecord.created_at)


@router.get("", response_model=TaskListResponse)
async def get_tasks(
    status: Optional[str] = Query(None, description="状态筛选"),
    content_id: Optional[str] = Query(None, description="番号搜索"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    sort_by: str = Query("created_at", description="排序字段"),
    sort_order: str = Query("desc", description="排序方向"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    获取任务列表
    
    支持分页、筛选、排序
    """
    # 构建查询
    query = db.query(DownloadRecord)
    
    # 应用筛选
    if status:
        query = query.filter(DownloadRecord.status == status)
    
    if content_id:
        query = query.filter(
            or_(
                DownloadRecord.content_id.ilike(f"%{content_id}%"),
                DownloadRecord.content_title.ilike(f"%{content_id}%")
            )
        )
    
    # 获取总数
    total = query.count()
    
    # 应用排序
    sort_column = get_sort_column(sort_by)
    if sort_order.lower() == "asc":
        query = query.order_by(asc(sort_column))
    else:
        query = query.order_by(desc(sort_column))
    
    # 应用分页
    offset = (page - 1) * page_size
    records = query.offset(offset).limit(page_size).all()
    
    # 计算总页数
    pages = (total + page_size - 1) // page_size
    
    return TaskListResponse(
        items=[TaskResponse.model_validate(r) for r in records],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    获取任务详情
    """
    record = db.query(DownloadRecord).filter(DownloadRecord.id == task_id).first()
    
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"任务 {task_id} 不存在"
        )
    
    return TaskResponse.model_validate(record)


@router.post("/{task_id}/retry", response_model=TaskActionResponse)
async def retry_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    重试失败任务
    
    将任务状态重置为 pending，等待下次工作流执行
    """
    record = db.query(DownloadRecord).filter(DownloadRecord.id == task_id).first()
    
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"任务 {task_id} 不存在"
        )
    
    # 只允许重试特定状态的任务
    allowed_statuses = ["error", "javsp_error", "timeout"]
    if record.status not in allowed_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"任务状态为 {record.status}，无法重试"
        )
    
    # 重置状态
    old_status = record.status
    record.status = "pending"
    record.error_message = None
    record.error_code = None
    
    db.commit()
    
    logger.info(f"任务 {task_id} ({record.content_id}) 已重置为 pending，原状态: {old_status}")
    
    return TaskActionResponse(
        success=True,
        message=f"任务已重置，将在下次工作流执行时重试",
        task_id=task_id
    )


@router.post("/{task_id}/cancel", response_model=TaskActionResponse)
async def cancel_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    取消任务
    
    将 pending 状态的任务标记为已取消
    """
    record = db.query(DownloadRecord).filter(DownloadRecord.id == task_id).first()
    
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"任务 {task_id} 不存在"
        )
    
    if record.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"只能取消 pending 状态的任务"
        )
    
    record.status = "cancelled"
    db.commit()
    
    logger.info(f"任务 {task_id} ({record.content_id}) 已取消")
    
    return TaskActionResponse(
        success=True,
        message="任务已取消",
        task_id=task_id
    )


@router.delete("/{task_id}", response_model=TaskActionResponse)
async def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    删除任务
    
    从数据库中删除任务记录
    """
    record = db.query(DownloadRecord).filter(DownloadRecord.id == task_id).first()
    
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"任务 {task_id} 不存在"
        )
    
    content_id = record.content_id
    db.delete(record)
    db.commit()
    
    logger.info(f"任务 {task_id} ({content_id}) 已删除")
    
    return TaskActionResponse(
        success=True,
        message="任务已删除",
        task_id=task_id
    )
