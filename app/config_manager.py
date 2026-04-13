"""
动态配置管理模块
支持运行时加载、保存、更新配置，以及备份/恢复功能
"""

import os
import yaml
import shutil
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict

from app.logger import logger


@dataclass
class AppConfig:
    """应用配置数据类"""
    
    # ============================================
    # Web UI 配置
    # ============================================
    web_password: str = "admin123"
    web_secret_key: str = "change-me-in-production-secret-key-2024"
    
    # ============================================
    # FreshRSS 配置
    # ============================================
    freshrss_url: str = ""
    freshrss_username: str = ""
    freshrss_password: str = ""
    
    # ============================================
    # RSSHub 配置
    # ============================================
    rsshub_base_url: str = ""
    
    # ============================================
    # BitComet 配置
    # ============================================
    bitcomet_url: str = "http://bitcomet:1235"
    bitcomet_username: str = "sandbox"
    bitcomet_password: str = ""
    bitcomet_client_id: str = ""
    bitcomet_authentication: str = ""
    bitcomet_download_path: str = "/home/sandbox/Downloads"
    
    # ============================================
    # JavSP 配置
    # ============================================
    javsp_url: str = "http://javsp-web:8090"
    javsp_username: str = "your_username"
    javsp_password: str = ""
    javsp_input_path: str = "/video/downloaded"
    javsp_output_path: str = "/video"
    
    # ============================================
    # Jellyfin 配置
    # ============================================
    jellyfin_url: str = ""
    jellyfin_api_key: str = ""
    jellyfin_library_name: str = "video"
    
    # ============================================
    # 工作流调度配置
    # ============================================
    workflow1_interval_minutes: int = 10
    workflow2_interval_minutes: int = 30
    workflow3_interval_minutes: int = 60
    
    # ============================================
    # JavSP 提交条件配置
    # ============================================
    javsp_submit_share_ratio: float = 5.0
    javsp_submit_hours: float = 8.0
    
    # ============================================
    # 业务逻辑配置
    # ============================================
    max_completed_downloads: int = 50
    max_retry_count: int = 3
    retry_delay_seconds: int = 60
    download_timeout_hours: int = 48
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AppConfig":
        """从字典创建"""
        # 过滤掉不存在的字段
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered_data)
    
    def update(self, updates: Dict[str, Any]) -> List[str]:
        """
        更新配置
        
        Returns:
            实际被更新的字段列表
        """
        updated = []
        valid_fields = set(self.__dataclass_fields__.keys())
        
        for key, value in updates.items():
            if key not in valid_fields:
                logger.warning(f"忽略未知配置项: {key}")
                continue
            
            # 类型转换
            expected_type = self.__dataclass_fields__[key].type
            try:
                if expected_type == int:
                    value = int(value)
                elif expected_type == float:
                    value = float(value)
                elif expected_type == str:
                    value = str(value)
            except (ValueError, TypeError):
                logger.warning(f"配置项 {key} 类型转换失败，使用原值")
                continue
            
            old_value = getattr(self, key)
            if old_value != value:
                setattr(self, key, value)
                updated.append(key)
                logger.info(f"配置更新: {key} = {value}")
        
        return updated


class ConfigManager:
    """
    配置管理器
    单例模式，支持线程安全的配置读写
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._config_lock = threading.RLock()
        self._config = AppConfig()
        self._config_file = self._get_config_file_path()
        self._observers = []
        
        # 初始加载
        self.load()
    
    def _get_config_file_path(self) -> Path:
        """获取配置文件路径"""
        # 优先从环境变量获取
        env_path = os.getenv("CONFIG_FILE")
        if env_path:
            return Path(env_path)
        
        # 按优先级尝试多个位置
        # 1. data/config.yaml (YAML格式，推荐)
        # 2. app.env (环境变量格式，便于编辑)
        
        candidates = [
            Path("data/config.yaml"),
            Path("app.env"),
        ]
        
        for path in candidates:
            if path.exists():
                return path
        
        # 默认使用 YAML 格式
        return Path("data/config.yaml")
    
    def _parse_env_file(self, file_path: Path) -> Dict[str, Any]:
        """解析 .env 格式的配置文件"""
        result = {}
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # 跳过空行和注释
                if not line or line.startswith('#'):
                    continue
                # 解析 KEY=VALUE
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    # 移除引号
                    if (value.startswith('"') and value.endswith('"')) or \
                       (value.startswith("'") and value.endswith("'")):
                        value = value[1:-1]
                    result[key] = value
        return result
    
    def _convert_value(self, key: str, value: str) -> Any:
        """将字符串值转换为合适的类型"""
        # 根据字段名推断类型
        if key.endswith('_MINUTES') or key.endswith('_HOURS') or key.endswith('_SECONDS') or key.endswith('_COUNT'):
            try:
                return int(value)
            except ValueError:
                pass
        if key.endswith('_RATIO') or key.endswith('_HOURS') and 'SUBMIT' in key:
            try:
                return float(value)
            except ValueError:
                pass
        return value
    
    def load(self) -> bool:
        """
        从文件加载配置
        
        Returns:
            是否成功加载
        """
        with self._config_lock:
            try:
                if not self._config_file.exists():
                    logger.info(f"配置文件不存在，使用默认配置: {self._config_file}")
                    self.save()  # 创建默认配置文件
                    return True
                
                # 根据文件扩展名决定解析方式
                if self._config_file.suffix == '.env' or self._config_file.name == 'app.env':
                    # .env 格式
                    raw_data = self._parse_env_file(self._config_file)
                    # 转换键名：FRESHRSS_URL -> freshrss_url
                    data = {}
                    for key, value in raw_data.items():
                        # 转换为小写
                        config_key = key.lower()
                        # 转换值类型
                        data[config_key] = self._convert_value(config_key, value)
                else:
                    # YAML 格式
                    with open(self._config_file, 'r', encoding='utf-8') as f:
                        data = yaml.safe_load(f)
                
                if data:
                    self._config = AppConfig.from_dict(data)
                    logger.info(f"配置加载成功: {self._config_file}")
                
                return True
                
            except Exception as e:
                logger.error(f"配置加载失败: {e}")
                return False
    
    def _save_as_env(self, file_path: Path) -> bool:
        """保存为 .env 格式"""
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("# AV Download Manager - 应用业务配置\n")
            f.write("# 此文件由 Web UI 自动生成，也可手动编辑\n\n")
            
            for key, value in self._config.to_dict().items():
                # 转换为大写键名
                env_key = key.upper()
                # 处理字符串值中的特殊字符
                if isinstance(value, str) and ('#' in value or '=' in value or ' ' in value):
                    value = f'"{value}"'
                f.write(f"{env_key}={value}\n")
        return True
    
    def save(self) -> bool:
        """
        保存配置到文件
        
        Returns:
            是否成功保存
        """
        with self._config_lock:
            try:
                # 确保目录存在
                self._config_file.parent.mkdir(parents=True, exist_ok=True)
                
                # 根据文件扩展名决定保存格式
                if self._config_file.suffix == '.env' or self._config_file.name == 'app.env':
                    # .env 格式
                    self._save_as_env(self._config_file)
                else:
                    # YAML 格式
                    with open(self._config_file, 'w', encoding='utf-8') as f:
                        yaml.dump(
                            self._config.to_dict(),
                            f,
                            default_flow_style=False,
                            allow_unicode=True,
                            sort_keys=False
                        )
                
                logger.info(f"配置保存成功: {self._config_file}")
                return True
                
            except Exception as e:
                logger.error(f"配置保存失败: {e}")
                return False
    
    def update(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        更新配置并保存
        
        Args:
            updates: 要更新的配置项
            
        Returns:
            {"success": bool, "updated": List[str], "message": str}
        """
        with self._config_lock:
            updated_fields = self._config.update(updates)
            
            if not updated_fields:
                return {
                    "success": True,
                    "updated": [],
                    "message": "没有配置项需要更新"
                }
            
            # 保存到文件
            if self.save():
                # 通知观察者
                self._notify_observers(updated_fields)
                
                return {
                    "success": True,
                    "updated": updated_fields,
                    "message": f"已更新 {len(updated_fields)} 个配置项"
                }
            else:
                return {
                    "success": False,
                    "updated": [],
                    "message": "配置保存失败"
                }
    
    def get(self, key: Optional[str] = None) -> Any:
        """
        获取配置
        
        Args:
            key: 配置项名称，None 返回全部
            
        Returns:
            配置值或全部配置字典
        """
        with self._config_lock:
            if key is None:
                return self._config.to_dict()
            return getattr(self._config, key, None)
    
    @property
    def config(self) -> AppConfig:
        """获取配置对象（只读建议，直接修改不会触发保存）"""
        with self._config_lock:
            return self._config
    
    def backup(self, backup_name: Optional[str] = None) -> Dict[str, Any]:
        """
        备份配置
        
        Args:
            backup_name: 备份文件名，None 使用时间戳
            
        Returns:
            {"success": bool, "backup_path": str, "message": str}
        """
        try:
            backup_dir = self._config_file.parent / "backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            if backup_name is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_name = f"config_backup_{timestamp}.yaml"
            
            backup_path = backup_dir / backup_name
            
            # 复制当前配置文件
            shutil.copy2(self._config_file, backup_path)
            
            logger.info(f"配置备份成功: {backup_path}")
            return {
                "success": True,
                "backup_path": str(backup_path),
                "message": f"备份成功: {backup_name}"
            }
            
        except Exception as e:
            logger.error(f"配置备份失败: {e}")
            return {
                "success": False,
                "backup_path": "",
                "message": f"备份失败: {str(e)}"
            }
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """
        列出所有备份
        
        Returns:
            备份文件列表
        """
        backup_dir = self._config_file.parent / "backups"
        
        if not backup_dir.exists():
            return []
        
        backups = []
        for f in sorted(backup_dir.glob("config_backup_*.yaml"), reverse=True):
            stat = f.stat()
            backups.append({
                "name": f.name,
                "path": str(f),
                "size": stat.st_size,
                "created": datetime.fromtimestamp(stat.st_mtime).isoformat()
            })
        
        return backups
    
    def restore(self, backup_name: str) -> Dict[str, Any]:
        """
        从备份恢复配置
        
        Args:
            backup_name: 备份文件名
            
        Returns:
            {"success": bool, "message": str}
        """
        try:
            backup_dir = self._config_file.parent / "backups"
            backup_path = backup_dir / backup_name
            
            if not backup_path.exists():
                return {
                    "success": False,
                    "message": f"备份文件不存在: {backup_name}"
                }
            
            # 先备份当前配置
            self.backup("config_auto_before_restore.yaml")
            
            # 恢复备份
            shutil.copy2(backup_path, self._config_file)
            
            # 重新加载
            self.load()
            
            logger.info(f"配置恢复成功: {backup_name}")
            return {
                "success": True,
                "message": f"已从 {backup_name} 恢复配置"
            }
            
        except Exception as e:
            logger.error(f"配置恢复失败: {e}")
            return {
                "success": False,
                "message": f"恢复失败: {str(e)}"
            }
    
    def delete_backup(self, backup_name: str) -> Dict[str, Any]:
        """
        删除备份
        
        Args:
            backup_name: 备份文件名
            
        Returns:
            {"success": bool, "message": str}
        """
        try:
            backup_dir = self._config_file.parent / "backups"
            backup_path = backup_dir / backup_name
            
            if not backup_path.exists():
                return {
                    "success": False,
                    "message": f"备份文件不存在: {backup_name}"
                }
            
            backup_path.unlink()
            
            logger.info(f"备份删除成功: {backup_name}")
            return {
                "success": True,
                "message": f"已删除备份: {backup_name}"
            }
            
        except Exception as e:
            logger.error(f"备份删除失败: {e}")
            return {
                "success": False,
                "message": f"删除失败: {str(e)}"
            }
    
    def add_observer(self, callback):
        """添加配置变更观察者"""
        self._observers.append(callback)
    
    def remove_observer(self, callback):
        """移除配置变更观察者"""
        if callback in self._observers:
            self._observers.remove(callback)
    
    def _notify_observers(self, changed_fields: List[str]):
        """通知观察者配置已变更"""
        for callback in self._observers:
            try:
                callback(changed_fields)
            except Exception as e:
                logger.warning(f"配置观察者通知失败: {e}")


# 全局配置管理器实例
config_manager = ConfigManager()


# 兼容旧代码的便捷访问方式
def get_config() -> AppConfig:
    """获取配置对象"""
    return config_manager.config
