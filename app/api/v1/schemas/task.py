"""
任务相关 Schema
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class TaskResponse(BaseModel):
    """任务详情响应模型"""
    id: int = Field(..., description="任务ID")
    content_id: str = Field(..., description="番号")
    content_title: Optional[str] = Field(None, description="标题")
    magnet_url: Optional[str] = Field(None, description="磁力链接")
    file_size: Optional[int] = Field(None, description="文件大小(字节)")
    
    # BitComet 相关
    bitcomet_task_id: Optional[str] = Field(None, description="BitComet 任务ID")
    bitcomet_task_guid: Optional[str] = Field(None, description="BitComet 任务GUID")
    task_type: Optional[str] = Field(None, description="任务类型")
    download_rate: Optional[int] = Field(None, description="下载速度(B/s)")
    upload_rate: Optional[int] = Field(None, description="上传速度(B/s)")
    error_code: Optional[str] = Field(None, description="错误码")
    error_message: Optional[str] = Field(None, description="错误信息")
    health: Optional[str] = Field(None, description="健康度")
    file_count: Optional[int] = Field(None, description="文件数")
    share_ratio: Optional[float] = Field(None, description="分享率")
    progress: Optional[int] = Field(None, description="进度(千分比)")
    
    # 状态
    status: str = Field(..., description="状态")
    file_path: Optional[str] = Field(None, description="文件路径")
    tags: Optional[str] = Field(None, description="标签")
    
    # JavSP 相关
    javsp_task_id: Optional[str] = Field(None, description="JavSP 任务ID")
    javsp_checked: bool = Field(False, description="是否已检测整理")
    folder_cleaned: bool = Field(False, description="文件夹是否已清理")
    javsp_retry_count: int = Field(0, description="JavSP 重试次数")
    
    # 时间
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    timeout_at: Optional[datetime] = Field(None, description="超时时间")
    
    class Config:
        from_attributes = True


class TaskListResponse(BaseModel):
    """任务列表响应"""
    items: List[TaskResponse] = Field(..., description="任务列表")
    total: int = Field(..., description="总数")
    page: int = Field(..., description="当前页")
    page_size: int = Field(..., description="每页数量")
    pages: int = Field(..., description="总页数")


class TaskFilterParams(BaseModel):
    """任务筛选参数"""
    status: Optional[str] = Field(None, description="状态筛选")
    content_id: Optional[str] = Field(None, description="番号搜索")
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页数量")
    sort_by: str = Field("created_at", description="排序字段")
    sort_order: str = Field("desc", description="排序方向: asc/desc")


class TaskActionResponse(BaseModel):
    """任务操作响应"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="提示信息")
    task_id: Optional[int] = Field(None, description="任务ID")


class TaskBatchActionRequest(BaseModel):
    """批量操作请求"""
    task_ids: List[int] = Field(..., description="任务ID列表")
    action: str = Field(..., description="操作类型: retry/cancel/delete")


class TaskBatchActionResponse(BaseModel):
    """批量操作响应"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="提示信息")
    processed: int = Field(..., description="处理数量")
    failed: int = Field(..., description="失败数量")
