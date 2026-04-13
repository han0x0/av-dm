"""
BitComet WebUI API 客户端
标准 BitComet WebUI API 实现
"""

import uuid
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from app.services.base import BaseHTTPClient
from app.config import settings
from app.logger import logger


@dataclass
class BitCometTask:
    """BitComet 任务数据类"""
    # 核心标识
    task_id: int
    task_guid: str  # 不变的唯一标识
    task_name: str
    
    # 状态和进度
    status: str  # running/stopped
    permillage: int  # 千分比进度 (1000 = 100%)
    
    # 文件大小
    total_size: int  # 总大小 bytes
    selected_size: int  # 选择下载大小
    selected_downloaded_size: int  # 已下载 bytes
    
    # 速度信息
    download_rate: int  # 下载速度 B/s
    upload_rate: int  # 上传速度 B/s
    
    # 分享和上传
    share_ratio: Optional[float] = None  # 分享率
    up_size: int = 0  # 已上传大小
    
    # 任务信息
    task_type: str = "BT"  # 任务类型: BT/HTTP
    file_count: int = 0  # 文件数
    health: Optional[str] = None  # 健康度
    
    # 错误信息
    error_code: str = ""  # 错误码
    error_message: str = ""  # 错误信息
    
    @classmethod
    def from_api_response(cls, task: Dict[str, Any]) -> "BitCometTask":
        """从 API 响应创建对象"""
        # 解析分享率（可能是字符串或数字）
        share_ratio = task.get("share_ratio")
        if isinstance(share_ratio, str):
            try:
                share_ratio = float(share_ratio)
            except:
                share_ratio = None
        
        return cls(
            task_id=task.get("task_id", 0),
            task_guid=task.get("task_guid", ""),
            task_name=task.get("task_name", ""),
            status=task.get("status", ""),
            permillage=task.get("permillage", 0),
            total_size=task.get("total_size", 0),
            selected_size=task.get("selected_size", 0),
            selected_downloaded_size=task.get("selected_downloaded_size", 0),
            download_rate=task.get("download_rate", 0),
            upload_rate=task.get("upload_rate", 0),
            share_ratio=share_ratio,
            up_size=task.get("up_size", 0),
            task_type=task.get("type", "BT"),
            file_count=task.get("file_count", 0),
            health=task.get("health"),
            error_code=task.get("error_code", ""),
            error_message=task.get("error_message", ""),
        )
    
    @property
    def progress_percent(self) -> float:
        """获取进度百分比"""
        return self.permillage / 10.0
    
    @property
    def is_completed(self) -> bool:
        """是否已完成下载"""
        return self.permillage >= 1000


class BitCometClient(BaseHTTPClient):
    """
    BitComet WebUI API 客户端
    
    标准 BitComet WebUI API 流程:
    1. POST /api/webui/login -> 获取 invite_token
    2. POST /api/device_token/get -> 使用 invite_token 换取 device_token
    3. 使用 device_token 调用其他 API
    """
    
    def __init__(self):
        super().__init__(settings.bitcomet_api_url)
        self._client_id: Optional[str] = None
        self._invite_token: Optional[str] = None
        self._device_token: Optional[str] = None
        
    def _get_default_headers(self) -> Dict[str, str]:
        """获取默认请求头"""
        return {
            "client-type": "BitComet WebUI",
            "Content-Type": "application/json",
        }
    
    async def login(self) -> str:
        """
        登录获取 invite_token
        POST /api/webui/login
        
        注意: 如果返回 APP_ACCESS_DISABLED，需要在 BitComet 设置中启用远程访问
        """
        url = "/api/webui/login"
        
        # 使用配置的 client_id，或复用默认值
        if not self._client_id:
            self._client_id = settings.bitcomet_client_id or "3b667012-c53c-4d76-a261-661e8d4a3ed4"
        
        headers = self._get_default_headers()
        
        # 请求体 - authentication 为 BitComet WebUI 登录凭证
        # 标准 BitComet API 中该值由 client_id + password 派生，需通过浏览器抓包获取。
        # 支持通过环境变量 BITCOMET_AUTHENTICATION 配置，否则使用旧版兼容值。
        auth_value = settings.bitcomet_authentication or ""
        if not auth_value:
            raise ValueError(
                "BitComet authentication 未配置。"
                "请通过浏览器 DevTools 抓包获取 /api/webui/login 请求中的 authentication 字段，"
                "并配置到 BITCOMET_AUTHENTICATION 环境变量中。"
            )
        data = {
            "client_id": self._client_id,
            "authentication": auth_value,
        }
        
        try:
            response = await self.post(url, headers=headers, json=data)
            result = response.json()
            
            if result.get("error_code") == "APP_ACCESS_DISABLED":
                raise ValueError(
                    "BitComet 远程访问未启用。"
                    "请在 BitComet 设置中启用远程访问功能。"
                )
            
            if result.get("error_code") != "OK":
                raise ValueError(f"BitComet 登录失败: {result}")
            
            self._invite_token = result.get("invite_token")
            logger.info("BitComet 登录成功，获取 invite_token")
            
            # 获取 device_token
            await self._get_device_token()
            
            return self._invite_token
            
        except Exception as e:
            logger.error(f"BitComet 登录失败: {e}")
            raise
    
    async def _get_device_token(self) -> str:
        """
        获取 device_token
        POST /api/device_token/get
        """
        if not self._invite_token:
            raise ValueError("Must login first")
        
        url = "/api/device_token/get"
        headers = self._get_default_headers()
        headers["authorization"] = f"Bearer {self._invite_token}"
        
        data = {
            "invite_token": self._invite_token,
            "device_id": self._client_id,
            "device_name": "av-download-manager",
            "platform": "webui",
        }
        
        response = await self.post(url, headers=headers, json=data)
        result = response.json()
        
        if result.get("error_code") != "OK":
            raise ValueError(f"获取 device_token 失败: {result}")
        
        self._device_token = result.get("device_token")
        logger.info("获取 device_token 成功")
        
        return self._device_token
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """获取需要认证的请求头"""
        if not self._device_token:
            raise ValueError("Must login first")
        
        headers = self._get_default_headers()
        headers["authorization"] = f"Bearer {self._device_token}"
        return headers
    
    async def ensure_logged_in(self):
        """确保已登录"""
        if not self._device_token:
            await self.login()
    
    async def get_task_list(self) -> List[BitCometTask]:
        """
        获取任务列表
        POST /api_v2/task_list/get
        """
        await self.ensure_logged_in()
        
        url = "/api_v2/task_list/get"
        headers = self._get_auth_headers()
        
        response = await self.post(url, headers=headers, json={})
        result = response.json()
        
        tasks = result.get("tasks", [])
        logger.debug(f"获取到 {len(tasks)} 个任务")
        
        return [BitCometTask.from_api_response(task) for task in tasks]
    
    async def add_task(self, magnet_url: str, save_path: Optional[str] = None) -> Optional[int]:
        """
        添加 BT 任务（磁力链接）
        POST /api/task/bt/add
        """
        await self.ensure_logged_in()
        
        url = "/api/task/bt/add"
        headers = self._get_auth_headers()
        
        # 确定保存路径
        actual_save_path = save_path or settings.bitcomet_download_path
        
        # BitComet API 参数格式
        data = {
            "torrent_url": magnet_url,
            "save_folder": actual_save_path,
            "start_later": False,
            "torrent_file": "",
        }
        
        # 详细调试日志
        logger.debug(f"[BitComet add_task] 请求 URL: {url}")
        logger.debug(f"[BitComet add_task] 请求 Headers: {headers}")
        logger.debug(f"[BitComet add_task] save_path 参数: {save_path}")
        logger.debug(f"[BitComet add_task] settings.bitcomet_download_path: {settings.bitcomet_download_path}")
        logger.debug(f"[BitComet add_task] 实际使用的 save_folder: {actual_save_path}")
        logger.debug(f"[BitComet add_task] 完整请求数据: {data}")
        
        try:
            response = await self.post(url, headers=headers, json=data)
            logger.debug(f"[BitComet add_task] 响应状态码: {response.status_code}")
            logger.debug(f"[BitComet add_task] 响应内容: {response.text}")
            
            result = response.json()
            
            # 注意：error_code 是 "ok" (小写)，不是 "OK"
            if result.get("error_code") != "ok":
                logger.warning(f"添加任务失败: {result}")
                logger.warning(f"[BitComet add_task] 失败详情 - error_code: {result.get('error_code')}, error_message: {result.get('error_message')}")
                return None
            
            # task_id 在根级别，可能是字符串 "1014"
            task_id = result.get("task_id")
            
            if task_id:
                logger.info(f"成功添加任务: {task_id}")
                return int(task_id) if isinstance(task_id, str) else task_id
            else:
                logger.warning(f"添加任务响应缺少 task_id: {result}")
                return None
        except Exception as e:
            logger.error(f"[BitComet add_task] 请求异常: {e}")
            logger.error(f"[BitComet add_task] 请求数据: {data}")
            raise
    
    async def stop_task(self, task_id: int) -> bool:
        """
        停止任务
        POST /api_v2/tasks/action
        
        Args:
            task_id: 任务ID
        """
        await self.ensure_logged_in()
        
        url = "/api_v2/tasks/action"
        headers = self._get_auth_headers()
        
        data = {
            "task_ids": [str(task_id)],
            "action": "stop",
        }
        
        try:
            response = await self.post(url, headers=headers, json=data)
            result = response.json()
            
            # 注意：error_code 可能是 "ok" (小写) 或 "OK" (大写)
            error_code = result.get("error_code", "").lower()
            success = error_code == "ok"
            
            if success:
                logger.info(f"成功停止任务 {task_id}")
            else:
                logger.warning(f"停止任务失败: {result}")
            
            return success
        except Exception as e:
            logger.warning(f"停止任务异常: {e}")
            return False
    
    async def delete_task(self, task_id: int, action: str = "delete_all") -> bool:
        """
        删除任务
        POST /api_v2/tasks/delete
        """
        await self.ensure_logged_in()
        
        url = "/api_v2/tasks/delete"
        headers = self._get_auth_headers()
        
        data = {
            "task_ids": [str(task_id)],
            "action": action,
        }
        
        response = await self.post(url, headers=headers, json=data)
        result = response.json()
        
        # 注意：error_code 可能是 "ok" (小写) 或 "OK" (大写)
        error_code = result.get("error_code", "").lower()
        success = error_code == "ok"
        
        if success:
            logger.info(f"成功删除任务 {task_id}")
        else:
            logger.warning(f"删除任务失败: {result}")
        
        return success
    
    async def find_task(self, task_id: int) -> Optional[BitCometTask]:
        """根据 task_id 查找任务"""
        tasks = await self.get_task_list()
        for task in tasks:
            if task.task_id == task_id:
                return task
        return None
    
    async def get_task_summary(self, task_id: int) -> Optional[BitCometTask]:
        """
        获取单个任务详情
        POST /api/task/summary/get
        
        注意：task_list/get 可能不返回做种/上传中的任务，
        此方法用于单独查询任务状态
        """
        await self.ensure_logged_in()
        
        url = "/api/task/summary/get"
        headers = self._get_auth_headers()
        
        response = await self.post(url, headers=headers, json={"task_id": str(task_id)})
        result = response.json()
        
        if result.get("error_code") != "ok":
            return None
        
        task_data = result.get("task")
        if not task_data:
            return None
        
        return BitCometTask.from_api_response(task_data)
    
    async def get_server_status(self) -> Dict[str, Any]:
        """获取服务器状态（用于诊断）"""
        try:
            # 尝试直接访问 login 端点看返回什么
            url = "/api/webui/login"
            headers = self._get_default_headers()
            data = {
                "client_id": "test-client-id",
                "authentication": "",
            }
            
            response = await self.post(url, headers=headers, json=data)
            return {
                "status": "accessible",
                "http_code": response.status_code,
                "response": response.json(),
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }
