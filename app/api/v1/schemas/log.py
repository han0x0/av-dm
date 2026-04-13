"""
日志相关 Schema
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class LogEntry(BaseModel):
    """日志条目"""
    timestamp: datetime = Field(..., description="时间戳")
    level: str = Field(..., description="日志级别")
    message: str = Field(..., description="日志内容")
    module: Optional[str] = Field(None, description="模块名")
    line: Optional[int] = Field(None, description="行号")


class LogResponse(BaseModel):
    """日志响应"""
    entries: List[LogEntry] = Field(..., description="日志条目列表")
    total: int = Field(..., description="总数")
    page: int = Field(..., description="当前页")
    page_size: int = Field(..., description="每页数量")


class LogFilterParams(BaseModel):
    """日志筛选参数"""
    level: Optional[str] = Field(None, description="日志级别: INFO/WARNING/ERROR/DEBUG")
    search: Optional[str] = Field(None, description="关键字搜索")
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(50, ge=1, le=500, description="每页数量")
