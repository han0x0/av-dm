"""
JavSP-Web API 客户端
基于 FastAPI 的 AV 元数据刮削器
"""

import os
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime

from app.services.base import BaseHTTPClient
from app.config import settings
from app.logger import logger


import re


def _normalize_folder_name(name: str) -> str:
    """
    清理文件夹名中的干扰前缀，保留番号部分
    如: "madoubt.com 228563.xyz KNB-406" → "KNB-406"
        "[xxx.com] ABC-123" → "ABC-123"
        "www.abc.com DEF-456 torrent" → "DEF-456"
    """
    # 去掉常见前缀（域名 + 可选数字）
    name = re.sub(r'^[\w\-\.]+\.\w+\s+(?:\d+\s+)?', '', name)
    # 去掉方括号包裹的内容
    name = re.sub(r'^\[[^\]]+\]\s*', '', name)
    # 去掉 "torrent" 等后缀词
    name = re.sub(r'\s+torrent\s*$', '', name, flags=re.IGNORECASE)
    return name.strip()


def _match_content_id(folder_name: str, content_id: str) -> bool:
    """
    双重检测机制匹配番号
    
    方式1（去掉"-"匹配）：
    - KNB-406 匹配 "KNB-406" (完全匹配)
    - KNB-406 匹配 "KNB406" (忽略横线)
    - KNB-406 匹配 "KNB-406-CD2" (多碟片)
    - KNB-406 不匹配 "KNB-4067" (避免子串误匹配)
    
    方式2（"-"前后分开匹配）：
    - KNB-406 需要同时匹配 KNB 和 406
    - 适用于文件名格式不一致的情况
    - 更精确，避免部分匹配
    """
    if not content_id:
        return False
    
    content_id_upper = content_id.upper()
    folder_name_upper = _normalize_folder_name(folder_name).upper()
    
    # 方式1：去掉横线匹配
    content_id_no_dash = content_id_upper.replace('-', '')
    folder_name_no_dash = folder_name_upper.replace('-', '').replace('_', '').replace(' ', '')
    
    # 构建单词边界正则
    pattern = r'\b' + re.escape(content_id_no_dash) + r'\b'
    if re.search(pattern, folder_name_no_dash):
        return True
    
    # 备用：直接包含匹配（确保后面不是数字）
    if content_id_no_dash in folder_name_no_dash:
        idx = folder_name_no_dash.find(content_id_no_dash)
        after = folder_name_no_dash[idx + len(content_id_no_dash):]
        if not after or not after[0].isdigit():
            return True
    
    # 方式2：分割部分匹配（所有部分都必须在文件名中找到）
    if '-' in content_id_upper:
        content_id_parts = content_id_upper.split('-')
        all_parts_found = all(part in folder_name_upper for part in content_id_parts if part)
        if all_parts_found:
            return True
    
    return False


def find_actual_media_folder(base_path: str, content_id: str = "", task_name: str = "") -> str:
    """
    找到实际包含视频文件的目录。
    BitComet 可能在 base_path 下创建子文件夹（来自 torrent 的 name 字段）。
    此函数在 Workflow 2 和 Workflow 4 中复用。
    
    Args:
        base_path: 基础下载路径（如 /home/sandbox/Downloads）
        content_id: 番号（如 KNB-406），用于精确匹配子目录
        task_name: BitComet 任务名称（torrent name），辅助匹配
    """
    if not os.path.isdir(base_path):
        return base_path
    
    video_exts = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.ts', '.m2ts'}
    has_direct_video = False
    subdirs_with_video = []
    
    try:
        for name in os.listdir(base_path):
            full = os.path.join(base_path, name)
            if os.path.isfile(full) and os.path.splitext(name)[1].lower() in video_exts:
                has_direct_video = True
            elif os.path.isdir(full):
                for f in os.listdir(full):
                    if os.path.isfile(os.path.join(full, f)) and os.path.splitext(f)[1].lower() in video_exts:
                        subdirs_with_video.append((name, full))
                        break
    except Exception:
        pass
    
    # 优先用 task_name 匹配（如果有提供）
    if task_name:
        matched_dirs = []
        for name, full_path in subdirs_with_video:
            if _match_content_id(name, task_name):
                matched_dirs.append((name, full_path))
        
        if matched_dirs:
            if len(matched_dirs) > 1:
                shortest = min(matched_dirs, key=lambda x: len(x[0]))
                logger.debug(f"多个子目录匹配 task_name {task_name}，选择最短名称: {shortest[0]}")
                return shortest[1]
            else:
                logger.debug(f"找到匹配 task_name 的子目录: {matched_dirs[0][0]}")
                return matched_dirs[0][1]
    
    # 优先级1：如果提供了 content_id，严格匹配番号
    if content_id:
        matched_dirs = []
        for name, full_path in subdirs_with_video:
            if _match_content_id(name, content_id):
                matched_dirs.append((name, full_path))
        
        if matched_dirs:
            # 如果多个匹配，选择名称最短的（避免长标题）
            if len(matched_dirs) > 1:
                shortest = min(matched_dirs, key=lambda x: len(x[0]))
                logger.debug(f"多个子目录匹配番号 {content_id}，选择最短名称: {shortest[0]}")
                return shortest[1]
            else:
                logger.debug(f"找到匹配番号的子目录: {matched_dirs[0][0]}")
                return matched_dirs[0][1]
        else:
            # 没有匹配到，记录警告，直接返回 base_path
            # 不再 fallback 到选择其他子文件夹，避免多米诺骨牌式错位
            logger.warning(
                f"未找到匹配番号 {content_id} 或 task_name {task_name} 的子目录，"
                f"可用目录: {[n for n, _ in subdirs_with_video]}，返回 base_path: {base_path}"
            )
            return base_path
    
    # 没有提供 content_id 时的 fallback（理论上不应发生）
    if len(subdirs_with_video) == 1:
        return subdirs_with_video[0][1]
    
    if len(subdirs_with_video) > 1:
        reasonable_dirs = [(n, p) for n, p in subdirs_with_video if len(n) <= 100]
        if reasonable_dirs:
            shortest = min(reasonable_dirs, key=lambda x: len(x[0]))
            logger.warning(f"无番号匹配，多个子目录，选择最短名称: {shortest[0]}")
            return shortest[1]
    
    # 没有子文件夹，但直接有视频文件
    if has_direct_video:
        return base_path
    
    return base_path


def get_safe_folder_path(actual_folder: str, content_id: str) -> tuple:
    """
    获取安全的文件夹路径用于 JavSP 提交
    
    如果文件夹名过长（>80字符），创建以 content_id 命名的软链接
    
    Args:
        actual_folder: 实际文件夹路径
        content_id: 番号
        
    Returns:
        (路径, 是否为软链接)
    """
    # 获取文件夹名称
    folder_name = os.path.basename(actual_folder)
    
    # 如果名称合理，直接使用
    if len(folder_name) <= 80:
        return actual_folder, False
    
    # 名称过长，创建软链接
    try:
        # 在 /tmp 创建以 content_id 命名的软链接
        link_dir = "/tmp/javsp_links"
        os.makedirs(link_dir, exist_ok=True)
        
        link_path = os.path.join(link_dir, content_id)
        
        # 如果已存在，先删除
        if os.path.islink(link_path):
            os.unlink(link_path)
        elif os.path.exists(link_path):
            # 如果存在但不是软链接，使用带序号的名称
            link_path = os.path.join(link_dir, f"{content_id}_link")
            if os.path.islink(link_path):
                os.unlink(link_path)
        
        # 创建软链接
        os.symlink(actual_folder, link_path)
        
        logger.info(f"创建短路径软链接: {link_path} -> {actual_folder[:50]}...")
        return link_path, True
        
    except Exception as e:
        logger.warning(f"创建软链接失败: {e}，使用原路径")
        return actual_folder, False


@dataclass
class JavSPTask:
    """JavSP 刮削任务数据类"""
    task_id: str
    task_type: str
    status: str  # PENDING/RUNNING/COMPLETED/FAILED
    input_directory: str
    profile: str
    created_at: datetime
    
    @classmethod
    def from_api_response(cls, task: Dict[str, Any]) -> "JavSPTask":
        """从 API 响应创建对象"""
        created_at_str = task.get("created_at", "")
        try:
            created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
        except:
            created_at = datetime.utcnow()
            
        return cls(
            task_id=task.get("id", ""),
            task_type=task.get("type", ""),
            status=task.get("status", ""),
            input_directory=task.get("input_directory", ""),
            profile=task.get("profile", "default"),
            created_at=created_at,
        )


@dataclass
class JavSPHistory:
    """JavSP 刮削历史记录"""
    id: int
    task_id: str
    dvdid: str  # 番号
    display_name: str
    save_dir: str
    poster_file: Optional[str]
    cover_download_success: bool
    fanart_download_success: bool
    created_at: datetime
    
    @classmethod
    def from_api_response(cls, item: Dict[str, Any]) -> "JavSPHistory":
        """从 API 响应创建对象"""
        created_at_str = item.get("created_at", "")
        try:
            created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
        except:
            created_at = datetime.utcnow()
            
        return cls(
            id=item.get("id", 0),
            task_id=item.get("task_id", ""),
            dvdid=item.get("dvdid", ""),
            display_name=item.get("display_name", ""),
            save_dir=item.get("save_dir", ""),
            poster_file=item.get("poster_file"),
            cover_download_success=item.get("cover_download_success", False),
            fanart_download_success=item.get("fanart_download_success", False),
            created_at=created_at,
        )


class JavSPClient(BaseHTTPClient):
    """JavSP-Web API 客户端"""
    
    def __init__(self):
        super().__init__(settings.javsp_api_url)
        self.session_cookie: Optional[str] = None
        
    async def login(self) -> bool:
        """
        登录获取 Session Cookie
        POST /api/auth/login
        
        JavSP-Web 使用 Cookie-based Session
        """
        url = "/api/auth/login"
        data = {
            "username": settings.javsp_username,
            "password": settings.javsp_password,
        }
        
        response = await self.post(url, json=data)
        
        # 从响应头中获取 Cookie
        set_cookie = response.headers.get("set-cookie", "")
        if "javsp_session" in set_cookie:
            # 提取 session 值
            import re
            match = re.search(r'javsp_session=([^;]+)', set_cookie)
            if match:
                self.session_cookie = match.group(1)
                logger.info("JavSP-Web 登录成功")
                return True
                
        # 检查响应体
        result = response.json()
        if result.get("username") == settings.javsp_username:
            logger.info("JavSP-Web 登录成功")
            return True
            
        logger.warning(f"JavSP-Web 登录失败: {response.text}")
        return False
    
    def _get_cookies(self) -> Dict[str, str]:
        """获取请求 cookies"""
        if self.session_cookie:
            return {"javsp_session": self.session_cookie}
        return {}
    
    async def scan_folder(self, path: str) -> Dict[str, Any]:
        """
        扫描文件夹
        GET /api/tasks/fs/scan?path={path}
        
        用于检测文件夹内容，判断整理是否完成
        
        Returns:
            {
                "path": "/video/downloaded/XXX",
                "files": [...],
                "count": 0
            }
            count == 0 表示文件夹为空，已整理完成
        """
        if not self.session_cookie:
            await self.login()
            
        url = f"/api/tasks/fs/scan"
        params = {"path": path}
        
        response = await self.get(url, params=params, cookies=self._get_cookies())
        return response.json()
    
    async def is_folder_empty(self, path: str) -> bool:
        """
        检查文件夹是否为空（用于判断整理是否完成）
        
        Returns:
            True - 文件夹为空，表示已整理完成
            False - 文件夹仍有文件
        """
        result = await self.scan_folder(path)
        count = result.get("count", 0)
        return count == 0
    
    async def create_task(
        self, 
        input_directory: str, 
        profile: str = "default"
    ) -> Optional[JavSPTask]:
        """
        创建刮削任务
        POST /api/tasks/manual
        
        Args:
            input_directory: 输入目录路径，如 /video/downloaded/300MIUM-1334
            profile: 配置文件名，默认 default
            
        Returns:
            创建的任务信息
        """
        if not self.session_cookie:
            await self.login()
            
        url = "/api/tasks/manual"
        data = {
            "input_directory": input_directory,
            "profile": profile,
        }
        
        response = await self.post(url, json=data, cookies=self._get_cookies())
        result = response.json()
        
        task = JavSPTask.from_api_response(result)
        logger.info(f"成功创建刮削任务: {task.task_id}")
        
        return task
    
    async def get_history(
        self, 
        limit: int = 50, 
        offset: int = 0
    ) -> List[JavSPHistory]:
        """
        获取刮削历史
        GET /api/tasks/history?limit={limit}&offset={offset}
        """
        if not self.session_cookie:
            await self.login()
            
        url = f"/api/tasks/history"
        params = {"limit": limit, "offset": offset}
        
        response = await self.get(url, params=params, cookies=self._get_cookies())
        items = response.json()
        
        return [JavSPHistory.from_api_response(item) for item in items]
    
    async def find_in_history(self, dvdid: str) -> Optional[JavSPHistory]:
        """
        在历史记录中查找指定番号
        
        Args:
            dvdid: 番号，如 300MIUM-1334
        """
        history = await self.get_history(limit=100)
        for item in history:
            if item.dvdid and item.dvdid.upper() == dvdid.upper():
                return item
        return None
    
    async def get_task_list(self) -> List[JavSPTask]:
        """
        获取任务列表
        GET /api/tasks
        """
        if not self.session_cookie:
            await self.login()
            
        url = "/api/tasks"
        
        response = await self.get(url, cookies=self._get_cookies())
        tasks = response.json()
        
        return [JavSPTask.from_api_response(task) for task in tasks]
    
    async def get_task_log(self, task_id: str):
        """
        获取任务日志 (SSE 流)
        GET /api/tasks/{task_id}/log
        
        注意: SSE 流需要特殊处理，这里暂不实现
        """
        pass
    
    async def cancel_task(self, task_id: str) -> bool:
        """
        取消任务
        POST /api/tasks/{task_id}/cancel
        """
        if not self.session_cookie:
            await self.login()
            
        url = f"/api/tasks/{task_id}/cancel"
        
        try:
            await self.post(url, cookies=self._get_cookies())
            logger.info(f"成功取消任务: {task_id}")
            return True
        except Exception as e:
            logger.error(f"取消任务失败: {e}")
            return False
