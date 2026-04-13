"""
应用配置管理
兼容旧代码的 settings 接口，内部使用 ConfigManager 实现动态配置
"""

from pathlib import Path
from typing import Optional

from app.config_manager import config_manager, AppConfig


class SettingsWrapper:
    """
    配置包装类
    兼容旧代码访问方式，内部转发到 ConfigManager
    """
    
    # 固定的应用信息（不从配置文件中读取）
    app_name: str = "AV Download Manager"
    debug: bool = False
    
    # Web UI 配置（从环境变量或配置文件）
    web_port: int = 8080
    log_level: str = "INFO"
    log_file: Path = Path("logs/app.log")
    database_url: str = "sqlite:///./data/av_downloads.db"
    
    def __init__(self):
        # 从环境变量读取基础配置
        import os
        self.web_port = int(os.getenv("WEB_PORT", "8080"))
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.log_file = Path(os.getenv("LOG_FILE", "logs/app.log"))
        self.database_url = os.getenv("DATABASE_URL", "sqlite:///./data/av_downloads.db")
    
    def _convert_value(self, name: str, value):
        """根据字段名转换值类型"""
        if value is None:
            return value
        
        # 整数类型字段
        int_fields = [
            'workflow1_interval_minutes',
            'workflow2_interval_minutes', 
            'workflow3_interval_minutes',
            'max_completed_downloads',
            'max_retry_count',
            'retry_delay_seconds',
            'download_timeout_hours',
        ]
        
        # 浮点数类型字段
        float_fields = [
            'javsp_submit_share_ratio',
            'javsp_submit_hours',
        ]
        
        if name in int_fields:
            try:
                return int(value)
            except (ValueError, TypeError):
                return value
        
        if name in float_fields:
            try:
                return float(value)
            except (ValueError, TypeError):
                return value
        
        return value
    
    def __getattr__(self, name: str):
        """动态转发到 ConfigManager"""
        # 优先返回自身的属性
        if name in self.__dict__:
            return self.__dict__[name]
        
        # 特殊属性处理
        if name == "freshrss_base_url":
            url = config_manager.get("freshrss_url")
            return f"{url.rstrip('/')}/api/greader.php" if url else ""
        
        if name == "bitcomet_api_url":
            url = config_manager.get("bitcomet_url")
            return url.rstrip('/') if url else ""
        
        if name == "javsp_api_url":
            url = config_manager.get("javsp_url")
            return url.rstrip('/') if url else ""
        
        # 从 ConfigManager 获取
        value = config_manager.get(name)
        if value is not None:
            # 类型转换
            return self._convert_value(name, value)
        
        # 返回 AppConfig 的默认值
        return getattr(AppConfig(), name, None)
    
    def reload(self):
        """重新加载配置"""
        config_manager.load()
    
    def to_dict(self) -> dict:
        """获取所有配置为字典"""
        base = {
            "app_name": self.app_name,
            "debug": self.debug,
            "web_port": self.web_port,
            "log_level": str(self.log_level),
            "log_file": str(self.log_file),
            "database_url": self.database_url,
        }
        base.update(config_manager.get())
        return base


# 全局配置实例（兼容旧代码）
settings = SettingsWrapper()

# 导出 ConfigManager 供新代码使用
from app.config_manager import config_manager
