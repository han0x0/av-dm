"""
配置管理 API
支持查看、更新、备份、恢复配置
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, Body, HTTPException
from pydantic import BaseModel, Field

from app.core.auth import get_current_active_user, User
from app.config_manager import config_manager
from app.config import settings

router = APIRouter()


# 敏感字段列表（不会在 API 中返回明文）
SENSITIVE_FIELDS = {
    "freshrss_password",
    "bitcomet_password",
    "bitcomet_authentication",
    "javsp_password",
    "jellyfin_api_key",
    "web_secret_key",
}


class ConfigUpdateRequest(BaseModel):
    """配置更新请求"""
    config: Dict[str, Any] = Field(..., description="要更新的配置项")


class ConfigUpdateResponse(BaseModel):
    """配置更新响应"""
    success: bool
    updated: List[str]
    message: str


class ConfigBackupResponse(BaseModel):
    """配置备份响应"""
    success: bool
    backup_path: Optional[str] = None
    message: str


class ConfigBackupInfo(BaseModel):
    """备份文件信息"""
    name: str
    path: str
    size: int
    created: str


class ConfigListBackupsResponse(BaseModel):
    """备份列表响应"""
    backups: List[ConfigBackupInfo]


class ConfigRestoreRequest(BaseModel):
    """配置恢复请求"""
    backup_name: str = Field(..., description="备份文件名")


class ConfigRestoreResponse(BaseModel):
    """配置恢复响应"""
    success: bool
    message: str


class ConfigDeleteBackupRequest(BaseModel):
    """删除备份请求"""
    backup_name: str = Field(..., description="备份文件名")


class ConfigResponse(BaseModel):
    """完整配置响应（脱敏）"""
    # 基础配置
    app_name: str
    debug: bool
    log_level: str
    
    # Web UI 配置
    web_password: str = Field("", description="Web UI 密码（脱敏显示）")
    web_password_configured: bool = Field(False, description="Web UI 密码是否已配置")
    
    # 工作流调度配置
    workflow1_interval_minutes: int
    workflow2_interval_minutes: int
    workflow3_interval_minutes: int
    
    # JavSP 提交条件
    javsp_submit_share_ratio: float
    javsp_submit_hours: float
    
    # 业务配置
    max_completed_downloads: int
    max_retry_count: int
    retry_delay_seconds: int
    download_timeout_hours: int
    
    # 路径配置
    bitcomet_download_path: str
    javsp_input_path: str
    javsp_output_path: str
    
    # 服务 URL（不包含敏感信息）
    freshrss_url: str
    rsshub_base_url: str
    bitcomet_url: str
    javsp_url: str
    jellyfin_url: str
    jellyfin_library_name: str
    
    # 用户名（不包含密码）
    freshrss_username: str
    bitcomet_username: str
    javsp_username: str
    
    # 密码配置状态（用于前端显示"已配置"而非脱敏值）
    freshrss_password_configured: bool = Field(False, description="FreshRSS 密码是否已配置")
    bitcomet_password_configured: bool = Field(False, description="BitComet 密码是否已配置")
    bitcomet_authentication_configured: bool = Field(False, description="BitComet Authentication 是否已配置")
    javsp_password_configured: bool = Field(False, description="JavSP 密码是否已配置")
    jellyfin_api_key_configured: bool = Field(False, description="Jellyfin API Key 是否已配置")
    
    # 配置状态
    freshrss_configured: bool
    bitcomet_configured: bool
    javsp_configured: bool
    jellyfin_configured: bool
    rsshub_configured: bool


def mask_sensitive_value(key: str, value: Any) -> Any:
    """敏感字段脱敏"""
    if key in SENSITIVE_FIELDS and value:
        if isinstance(value, str):
            if len(value) <= 4:
                return "****"
            return value[:2] + "****" + value[-2:]
    return value


def get_config_dict() -> Dict[str, Any]:
    """获取配置字典（脱敏）"""
    config = config_manager.get()
    return {k: mask_sensitive_value(k, v) for k, v in config.items()}


@router.get("", response_model=ConfigResponse)
async def get_config(
    current_user: User = Depends(get_current_active_user),
):
    """
    获取系统配置（脱敏）
    
    敏感信息（密码、API Key）会被脱敏处理
    """
    config = config_manager.get()
    
    return ConfigResponse(
        app_name=settings.app_name,
        debug=settings.debug,
        log_level=settings.log_level,
        
        # Web UI 配置（脱敏）
        web_password=mask_sensitive_value("web_password", config.get("web_password")),
        web_password_configured=bool(config.get("web_password")),
        
        # 工作流调度配置
        workflow1_interval_minutes=config.get("workflow1_interval_minutes", 10),
        workflow2_interval_minutes=config.get("workflow2_interval_minutes", 30),
        workflow3_interval_minutes=config.get("workflow3_interval_minutes", 60),
        
        # JavSP 提交条件
        javsp_submit_share_ratio=config.get("javsp_submit_share_ratio", 2.0),
        javsp_submit_hours=config.get("javsp_submit_hours", 6.0),
        
        # 业务配置
        max_completed_downloads=config.get("max_completed_downloads", 50),
        max_retry_count=config.get("max_retry_count", 3),
        retry_delay_seconds=config.get("retry_delay_seconds", 60),
        download_timeout_hours=config.get("download_timeout_hours", 48),
        
        # 路径配置
        bitcomet_download_path=config.get("bitcomet_download_path", "/home/sandbox/Downloads"),
        javsp_input_path=config.get("javsp_input_path", "/video/downloaded"),
        javsp_output_path=config.get("javsp_output_path", "/video"),
        
        # 服务 URL
        freshrss_url=config.get("freshrss_url", ""),
        rsshub_base_url=config.get("rsshub_base_url", ""),
        bitcomet_url=config.get("bitcomet_url", ""),
        javsp_url=config.get("javsp_url", ""),
        jellyfin_url=config.get("jellyfin_url", ""),
        jellyfin_library_name=config.get("jellyfin_library_name", "video"),
        
        # 用户名
        freshrss_username=config.get("freshrss_username", ""),
        bitcomet_username=config.get("bitcomet_username", ""),
        javsp_username=config.get("javsp_username", ""),
        
        # 密码配置状态
        freshrss_password_configured=bool(config.get("freshrss_password")),
        bitcomet_password_configured=bool(config.get("bitcomet_password")),
        bitcomet_authentication_configured=bool(config.get("bitcomet_authentication")),
        javsp_password_configured=bool(config.get("javsp_password")),
        jellyfin_api_key_configured=bool(config.get("jellyfin_api_key")),
        
        # 配置状态
        freshrss_configured=bool(
            config.get("freshrss_url") and config.get("freshrss_username")
        ),
        bitcomet_configured=bool(
            config.get("bitcomet_url") and config.get("bitcomet_username")
        ),
        javsp_configured=bool(
            config.get("javsp_url") and config.get("javsp_username")
        ),
        jellyfin_configured=bool(
            config.get("jellyfin_url") and config.get("jellyfin_api_key")
        ),
        rsshub_configured=bool(config.get("rsshub_base_url")),
    )


@router.put("", response_model=ConfigUpdateResponse)
async def update_config(
    request: ConfigUpdateRequest,
    current_user: User = Depends(get_current_active_user),
):
    """
    更新系统配置
    
    只更新提供的字段，未提供的字段保持不变
    保存后立即生效（无需重启）
    """
    if not request.config:
        raise HTTPException(status_code=400, detail="配置项不能为空")
    
    result = config_manager.update(request.config)
    
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["message"])
    
    return ConfigUpdateResponse(**result)


@router.post("/backup", response_model=ConfigBackupResponse)
async def backup_config(
    backup_name: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
):
    """
    备份当前配置
    
    Args:
        backup_name: 自定义备份文件名，默认使用时间戳
    """
    result = config_manager.backup(backup_name)
    
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["message"])
    
    return ConfigBackupResponse(**result)


@router.get("/backups", response_model=ConfigListBackupsResponse)
async def list_backups(
    current_user: User = Depends(get_current_active_user),
):
    """列出所有配置备份"""
    backups = config_manager.list_backups()
    return ConfigListBackupsResponse(backups=[ConfigBackupInfo(**b) for b in backups])


@router.post("/restore", response_model=ConfigRestoreResponse)
async def restore_config(
    request: ConfigRestoreRequest,
    current_user: User = Depends(get_current_active_user),
):
    """
    从备份恢复配置
    
    恢复前会自动备份当前配置
    """
    result = config_manager.restore(request.backup_name)
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    
    return ConfigRestoreResponse(**result)


@router.delete("/backups/{backup_name}", response_model=ConfigRestoreResponse)
async def delete_backup(
    backup_name: str,
    current_user: User = Depends(get_current_active_user),
):
    """删除指定备份文件"""
    result = config_manager.delete_backup(backup_name)
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    
    return ConfigRestoreResponse(**result)


@router.get("/raw")
async def get_raw_config(
    current_user: User = Depends(get_current_active_user),
):
    """
    获取完整配置（原始格式，用于导出）
    
    警告：包含敏感信息，请妥善保管
    """
    return config_manager.get()
