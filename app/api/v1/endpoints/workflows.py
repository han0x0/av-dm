"""
工作流控制 API
"""

from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks

from app.core.auth import get_current_active_user, User
from app.api.v1.schemas import WorkflowStatus
from app.config import settings
from app.logger import logger

router = APIRouter()

# 全局调度器引用（将在 main.py 中设置）
scheduler_ref = None


def set_scheduler(scheduler):
    """设置调度器引用"""
    global scheduler_ref
    scheduler_ref = scheduler


@router.get("", response_model=List[WorkflowStatus])
async def get_workflows(
    current_user: User = Depends(get_current_active_user),
):
    """
    获取工作流列表和状态
    """
    workflows = []
    
    if scheduler_ref:
        # 从调度器获取实际状态
        jobs = scheduler_ref.get_jobs()
        job_map = {job.id: job for job in jobs}
        
        workflow_configs = [
            ("workflow1", "处理 Starred Items", settings.workflow1_interval_minutes, "分钟"),
            ("workflow2", "状态监控", settings.workflow2_interval_minutes, "分钟"),
            ("workflow3", "空间管理与清理", settings.workflow3_interval_minutes, "分钟"),
        ]
        
        for wf_id, name, interval, unit in workflow_configs:
            job = job_map.get(wf_id)
            if job:
                next_run = job.next_run_time
                workflows.append(WorkflowStatus(
                    name=wf_id,
                    display_name=name,
                    status="running",
                    next_run=next_run,
                    interval=f"{interval} {unit}"
                ))
    else:
        # 调度器未启动，返回配置信息
        workflows = [
            WorkflowStatus(
                name="workflow1",
                display_name="处理 Starred Items",
                status="stopped",
                interval=f"{settings.workflow1_interval_minutes} 分钟"
            ),
            WorkflowStatus(
                name="workflow2",
                display_name="状态监控",
                status="stopped",
                interval=f"{settings.workflow2_interval_minutes} 分钟"
            ),
            WorkflowStatus(
                name="workflow3",
                display_name="空间管理与清理",
                status="stopped",
                interval=f"{settings.workflow3_interval_minutes} 分钟"
            ),
        ]
    
    return workflows


@router.post("/{workflow_name}/trigger")
async def trigger_workflow(
    workflow_name: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
):
    """
    手动触发工作流执行
    
    参数:
        - workflow_name: workflow1/workflow2/workflow3
    """
    valid_workflows = ["workflow1", "workflow2", "workflow3"]
    
    if workflow_name not in valid_workflows:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效的工作流名称: {workflow_name}"
        )
    
    # 从主应用获取工作流函数
    from app.main import Application
    
    # 创建临时应用实例执行工作流
    app = Application()
    
    workflow_map = {
        "workflow1": app.run_workflow1,
        "workflow2": app.run_workflow2,
        "workflow3": app.run_workflow3,
    }
    
    workflow_func = workflow_map.get(workflow_name)
    
    if not workflow_func:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="工作流函数未找到"
        )
    
    # 在后台执行工作流
    import asyncio
    
    async def run_in_background():
        try:
            logger.info(f"手动触发工作流: {workflow_name}")
            await workflow_func()
            logger.info(f"工作流 {workflow_name} 执行完成")
        except Exception as e:
            logger.exception(f"工作流 {workflow_name} 执行失败: {e}")
    
    # 启动后台任务
    asyncio.create_task(run_in_background())
    
    return {
        "success": True,
        "message": f"工作流 {workflow_name} 已触发，正在后台执行",
        "workflow": workflow_name,
        "triggered_at": datetime.utcnow().isoformat()
    }
