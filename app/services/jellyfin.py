"""
Jellyfin API 客户端
用于管理媒体库中的条目，配合空间管理策略
"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime

from app.services.base import BaseHTTPClient
from app.config import settings
from app.logger import logger


@dataclass
class JellyfinItem:
    """Jellyfin 媒体条目"""
    id: str
    name: str
    path: str
    type: str  # Movie, Episode, etc.
    date_created: Optional[datetime] = None
    production_year: Optional[int] = None
    
    @classmethod
    def from_api_response(cls, item: Dict[str, Any]) -> "JellyfinItem":
        """从 API 响应创建对象"""
        # 解析创建时间
        date_created = None
        date_created_str = item.get("DateCreated") or item.get("PremiereDate")
        if date_created_str:
            try:
                # Jellyfin 时间格式: 2024-01-15T10:30:00.0000000Z
                date_created = datetime.fromisoformat(date_created_str.replace('Z', '+00:00'))
            except:
                pass
        
        return cls(
            id=item.get("Id", ""),
            name=item.get("Name", ""),
            path=item.get("Path", ""),
            type=item.get("Type", ""),
            date_created=date_created,
            production_year=item.get("ProductionYear"),
        )


class JellyfinClient(BaseHTTPClient):
    """Jellyfin API 客户端"""
    
    def __init__(self):
        super().__init__(settings.jellyfin_url)
        self.api_key = settings.jellyfin_api_key
        self.user_id: Optional[str] = None
        self._connected = False
        
    def _get_headers(self) -> Dict[str, str]:
        """获取认证头"""
        return {
            "X-Emby-Token": self.api_key,
            "Content-Type": "application/json",
        }
    
    async def connect(self):
        """连接并获取必要信息"""
        if self._connected:
            return
            
        await super().connect()
        
        try:
            self.user_id = await self._get_admin_user()
            if self.user_id:
                logger.info(f"Jellyfin 连接成功，用户ID: {self.user_id}")
                self._connected = True
            else:
                logger.warning("Jellyfin 连接失败，无法获取用户ID")
        except Exception as e:
            logger.error(f"Jellyfin 连接异常: {e}")
    
    async def _get_users(self) -> List[Dict[str, Any]]:
        """
        获取用户列表
        GET /Users
        """
        url = "/Users"
        response = await self.get(url, headers=self._get_headers())
        return response.json()
    
    async def _get_admin_user(self) -> Optional[str]:
        """
        获取管理员用户 ID
        """
        try:
            users = await self._get_users()
            for user in users:
                if user.get("Policy", {}).get("IsAdministrator", False):
                    return user.get("Id")
            # 如果没有找到管理员，返回第一个用户
            if users:
                return users[0].get("Id")
        except Exception as e:
            logger.error(f"获取管理员用户失败: {e}")
        return None
    
    async def get_library_by_name(self, library_name: str) -> Optional[Dict[str, Any]]:
        """
        根据名称获取媒体库
        GET /Library/VirtualFolders
        """
        try:
            url = "/Library/VirtualFolders"
            response = await self.get(url, headers=self._get_headers())
            libraries = response.json()
            
            for lib in libraries:
                if lib.get("Name") == library_name:
                    return lib
            
            logger.warning(f"未找到媒体库: {library_name}")
            return None
        except Exception as e:
            logger.error(f"获取媒体库失败: {e}")
            return None
    
    async def get_library_items(
        self, 
        parent_id: Optional[str] = None,
        sort_by: str = "DateCreated",
        sort_order: str = "Ascending",
        limit: Optional[int] = None
    ) -> List[JellyfinItem]:
        """
        获取媒体库中的条目
        GET /Items?parentId={parent_id}&sortBy={sort_by}&sortOrder={sort_order}
        
        Args:
            parent_id: 父文件夹ID（媒体库ID）
            sort_by: 排序字段 (DateCreated, PremiereDate, ProductionYear, etc.)
            sort_order: 排序方向 (Ascending/Descending)
            limit: 限制数量
        """
        if not self._connected:
            await self.connect()
            
        if not self.user_id:
            logger.error("无法获取 Jellyfin 用户ID")
            return []
        
        url = "/Items"
        params = {
            "userId": self.user_id,
            "sortBy": sort_by,
            "sortOrder": sort_order,
            "includeItemTypes": "Movie,Video",
            "recursive": "true",
            "fields": "Path,DateCreated,PremiereDate,ProductionYear",
        }
        
        if parent_id:
            params["parentId"] = parent_id
        if limit:
            params["limit"] = limit
        
        try:
            response = await self.get(url, params=params, headers=self._get_headers())
            data = response.json()
            items = data.get("Items", [])
            return [JellyfinItem.from_api_response(item) for item in items]
        except Exception as e:
            logger.error(f"获取 Jellyfin 条目失败: {e}")
            return []
    
    async def get_all_movies(self, limit: Optional[int] = None) -> List[JellyfinItem]:
        """
        获取所有电影/视频条目（按创建时间排序，最早的在前）
        
        Args:
            limit: 限制返回数量
        """
        # 先尝试获取指定媒体库
        library = await self.get_library_by_name(settings.jellyfin_library_name)
        
        if library:
            library_id = library.get("ItemId")
            logger.debug(f"使用媒体库: {settings.jellyfin_library_name} ({library_id})")
            items = await self.get_library_items(
                parent_id=library_id,
                sort_by="DateCreated",
                sort_order="Ascending",
                limit=limit
            )
        else:
            # 如果找不到指定媒体库，获取所有电影
            logger.warning(f"媒体库 {settings.jellyfin_library_name} 不存在，获取所有电影")
            items = await self.get_library_items(
                sort_by="DateCreated",
                sort_order="Ascending",
                limit=limit
            )
        
        return items
    
    async def get_oldest_movies(self, count: int) -> List[JellyfinItem]:
        """
        获取最早的 N 个影片
        
        Args:
            count: 数量
        """
        return await self.get_all_movies(limit=count)
    
    async def get_movie_count(self) -> int:
        """
        获取媒体库中影片总数
        """
        if not self._connected:
            await self.connect()
            
        if not self.user_id:
            return 0
        
        url = "/Items"
        params = {
            "userId": self.user_id,
            "includeItemTypes": "Movie,Video",
            "recursive": "true",
            "limit": 0,
        }
        
        # 尝试限制到指定媒体库
        library = await self.get_library_by_name(settings.jellyfin_library_name)
        if library:
            params["parentId"] = library.get("ItemId")
        
        try:
            response = await self.get(url, params=params, headers=self._get_headers())
            data = response.json()
            return data.get("TotalRecordCount", 0)
        except Exception as e:
            logger.error(f"获取 Jellyfin 影片数量失败: {e}")
            return 0
    
    async def delete_item(self, item_id: str) -> bool:
        """
        删除 Jellyfin 条目及其文件
        DELETE /Items/{item_id}
        
        Args:
            item_id: 条目 ID
        """
        url = f"/Items/{item_id}"
        
        try:
            await self.delete(url, headers=self._get_headers())
            logger.info(f"成功删除 Jellyfin 条目: {item_id}")
            return True
        except Exception as e:
            logger.error(f"删除 Jellyfin 条目失败 {item_id}: {e}")
            return False