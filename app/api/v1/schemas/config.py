"""
配置相关 Schema
"""

from typing import Optional
from pydantic import BaseModel, Field


class ConfigResponse(BaseModel):
    """配置响应（脱敏）"""
    app_name: str = Field(..., description="应用名称")
    debug: bool = Field(..., description="调试模式")
    log_level: str = Field(..., description="日志级别")
    web_password: str = Field("", description="Web UI 密码（脱敏）")
    
    # 工作流调度配置
    workflow1_interval_minutes: int = Field(..., description="Workflow 1 间隔(分钟)")
    workflow2_interval_minutes: int = Field(..., description="Workflow 2 间隔(分钟)")
    workflow3_interval_minutes: int = Field(..., description="Workflow 3 间隔(分钟)")
    
    # JavSP 提交条件
    javsp_submit_share_ratio: float = Field(..., description="分享率阈值")
    javsp_submit_hours: float = Field(..., description="创建时间阈值(小时)")
    
    # 业务配置
    max_completed_downloads: int = Field(..., description="最大保留完成下载数")
    max_retry_count: int = Field(..., description="最大重试次数")
    retry_delay_seconds: int = Field(..., description="重试延迟(秒)")
    download_timeout_hours: int = Field(..., description="下载超时时间(小时)")
    
    # 路径配置
    bitcomet_download_path: str = Field(..., description="BitComet 下载路径")
    javsp_input_path: str = Field(..., description="JavSP 输入路径")
    javsp_output_path: str = Field(..., description="JavSP 输出路径")
    
    # 服务 URL
    freshrss_url: str = Field("", description="FreshRSS URL")
    rsshub_base_url: str = Field("", description="RSSHub URL")
    bitcomet_url: str = Field("", description="BitComet URL")
    javsp_url: str = Field("", description="JavSP URL")
    jellyfin_url: str = Field("", description="Jellyfin URL")
    jellyfin_library_name: str = Field("", description="Jellyfin 媒体库名称")
    
    # 用户名
    freshrss_username: str = Field("", description="FreshRSS 用户名")
    bitcomet_username: str = Field("", description="BitComet 用户名")
    javsp_username: str = Field("", description="JavSP 用户名")
    
    # 服务地址（脱敏，只显示是否配置）
    freshrss_configured: bool = Field(..., description="FreshRSS 是否配置")
    bitcomet_configured: bool = Field(..., description="BitComet 是否配置")
    javsp_configured: bool = Field(..., description="JavSP 是否配置")
    jellyfin_configured: bool = Field(..., description="Jellyfin 是否配置")
    rsshub_configured: bool = Field(..., description="RSSHub 是否配置")


class WorkflowScheduleConfig(BaseModel):
    """工作流调度配置"""
    workflow1_interval_minutes: int = Field(..., ge=1, le=1440)
    workflow2_interval_minutes: int = Field(..., ge=1, le=1440)
    workflow3_interval_minutes: int = Field(..., ge=1, le=1440)


class JavSPSubmitConfig(BaseModel):
    """JavSP 提交条件配置"""
    javsp_submit_share_ratio: float = Field(..., ge=0, le=10)
    javsp_submit_hours: float = Field(..., ge=0, le=168)


class ConfigBackupInfo(BaseModel):
    """备份文件信息"""
    name: str
    path: str
    size: int
    created: str
