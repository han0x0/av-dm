"""
日志查看 API
"""

import os
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse

from app.core.auth import get_current_active_user, User
from app.api.v1.schemas import LogResponse, LogEntry
from app.config import settings

router = APIRouter()


def parse_log_line(line: str) -> Optional[LogEntry]:
    """
    解析日志行
    
    实际格式: 2024-01-15 10:30:45.123 | LEVEL | name:function:line | MESSAGE
    """
    try:
        parts = line.split("|", 3)
        if len(parts) >= 4:
            timestamp_str = parts[0].strip()
            level = parts[1].strip()
            module_info = parts[2].strip()
            message = parts[3].strip()
            
            from datetime import datetime
            timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S.%f")
            
            # 从 name:function:line 中提取模块和行号
            module = None
            line_no = None
            if ":" in module_info:
                module_parts = module_info.rsplit(":", 1)
                if module_parts[-1].isdigit():
                    line_no = int(module_parts[-1])
                    module = module_parts[0] or None
                else:
                    module = module_info or None
            else:
                module = module_info or None
            
            return LogEntry(
                timestamp=timestamp,
                level=level,
                message=message,
                module=module,
                line=line_no
            )
    except Exception:
        pass
    
    # 如果解析失败，返回原始内容
    from datetime import datetime
    return LogEntry(
        timestamp=datetime.now(),
        level="INFO",
        message=line.strip(),
        module=None,
        line=None
    )


@router.get("", response_model=LogResponse)
async def get_logs(
    level: Optional[str] = Query(None, description="日志级别筛选"),
    search: Optional[str] = Query(None, description="关键字搜索"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=500, description="每页数量"),
    current_user: User = Depends(get_current_active_user),
):
    """
    获取日志内容
    
    支持分页、级别筛选、关键字搜索
    """
    log_file = settings.log_file
    
    if not os.path.exists(log_file):
        return LogResponse(entries=[], total=0, page=page, page_size=page_size)
    
    # 读取日志文件
    try:
        with open(log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        return LogResponse(
            entries=[LogEntry(timestamp=__import__('datetime').datetime.now(), level="ERROR", message=f"无法读取日志文件: {e}")],
            total=1,
            page=page,
            page_size=page_size
        )
    
    # 解析日志行
    entries = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        entry = parse_log_line(line)
        if entry:
            # 应用级别筛选
            if level and entry.level != level.upper():
                continue
            
            # 应用关键字搜索
            if search and search.lower() not in entry.message.lower():
                continue
            
            entries.append(entry)
    
    # 倒序排列（最新的在前）
    entries.reverse()
    
    # 分页
    total = len(entries)
    start = (page - 1) * page_size
    end = start + page_size
    paged_entries = entries[start:end]
    
    return LogResponse(
        entries=paged_entries,
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/raw", response_class=PlainTextResponse)
async def get_raw_logs(
    lines: int = Query(100, ge=1, le=1000, description="返回行数"),
    current_user: User = Depends(get_current_active_user),
):
    """
    获取原始日志文本
    
    用于导出或调试
    """
    log_file = settings.log_file
    
    if not os.path.exists(log_file):
        return "日志文件不存在"
    
    try:
        with open(log_file, "r", encoding="utf-8") as f:
            all_lines = f.readlines()
        
        # 返回最后 N 行
        return "".join(all_lines[-lines:])
    except Exception as e:
        return f"读取日志失败: {e}"
