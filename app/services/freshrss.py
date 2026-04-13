"""
FreshRSS API 客户端
基于 Google Reader API
"""

import re
import html
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field

import httpx
from app.services.base import BaseHTTPClient
from app.config import settings
from app.logger import logger


@dataclass
class FreshRSSItem:
    """FreshRSS 条目数据类"""
    item_id: str  # 完整条目 ID
    id_entry: int  # 内部 ID
    title: str
    content: str
    source_url: Optional[str] = None  # 原始来源链接
    magnet_url: Optional[str] = None
    uid: Optional[str] = None  # 提取的番号
    _fetched_from_source: bool = field(default=False, repr=False)  # 是否已尝试从源站抓取
    
    @classmethod
    def from_api_response(cls, item: Dict[str, Any]) -> "FreshRSSItem":
        """从 API 响应创建对象"""
        content = item.get("summary", {}).get("content", "")
        # 解码 HTML 实体
        content = html.unescape(content)
        
        # 提取原始来源链接 (alternate/href)
        source_url = None
        alternates = item.get("alternate", [])
        if alternates and isinstance(alternates, list):
            source_url = alternates[0].get("href", "")
        
        freshrss_item = cls(
            item_id=item.get("id", ""),
            id_entry=item.get("id_entry", 0),
            title=item.get("title", ""),
            content=content,
            source_url=source_url,
        )
        
        # 提取磁力链接
        freshrss_item.magnet_url = freshrss_item._extract_magnet(content)
        # 提取番号
        freshrss_item.uid = freshrss_item._extract_uid(freshrss_item.title, content)
        
        return freshrss_item
    
    async def fetch_magnet_from_source(
        self, 
        rsshub_base_url: Optional[str] = None,
        timeout: int = 30
    ) -> Optional[str]:
        """
        从 RSSHub 源站抓取磁力链接
        
        当 FreshRSS 内容中没有磁力链接时，尝试从 RSSHub 重新获取该条目的 RSS 数据，
        因为 RSSHub 的完整内容中通常包含磁力链接。
        
        Args:
            rsshub_base_url: RSSHub 服务器地址，如 "https://rsshub.your-domain.com"
                            如果为 None，则尝试从 source_url 推断
            timeout: 请求超时时间（秒）
            
        Returns:
            抓取到的磁力链接，如果没有则返回 None
        """
        if self._fetched_from_source:
            logger.debug(f"条目 {self.id_entry} 已尝试过抓取，跳过")
            return self.magnet_url
        
        self._fetched_from_source = True
        
        # 构造 RSSHub 抓取 URL
        rsshub_url = self._build_rsshub_url(rsshub_base_url)
        if not rsshub_url:
            logger.debug(f"条目 {self.id_entry} 无法构造 RSSHub URL，跳过")
            return None
        
        logger.info(f"尝试从 RSSHub 抓取磁力链接: {rsshub_url}")
        
        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                response = await client.get(rsshub_url)
                response.raise_for_status()
                
                # 获取 RSS 内容
                rss_content = response.text
                
                # 从 RSS 内容中提取磁力链接
                magnet = self._extract_magnet(rss_content)
                
                if magnet:
                    logger.info(f"✅ 从 RSSHub 成功抓取磁力链接: {magnet[:50]}...")
                    self.magnet_url = magnet
                    return magnet
                else:
                    logger.warning(f"⚠️ RSSHub 内容中未找到磁力链接")
                    
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ 抓取 RSSHub 失败 (HTTP {e.response.status_code}): {rsshub_url}")
        except httpx.RequestError as e:
            logger.error(f"❌ 抓取 RSSHub 请求失败: {e}")
        except Exception as e:
            logger.error(f"❌ 抓取 RSSHub 异常: {e}")
        
        return None
    
    def _build_rsshub_url(self, rsshub_base_url: Optional[str] = None) -> Optional[str]:
        """
        构造 RSSHub 抓取 URL
        
        策略：
        1. 如果提供了 rsshub_base_url，则构造 URL: {rsshub_base_url}/javbus/home/ja/{番号}
        2. 否则尝试从 item_id 推断（如果 item_id 包含 rsshub 地址）
        3. 如果都失败，返回 None
        """
        if not self.uid:
            return None
        
        # 方案 1: 使用配置的 RSSHub 基础地址
        if rsshub_base_url:
            base = rsshub_base_url.rstrip('/')
            # 根据番号构造 JavBus RSS URL
            # 格式: https://rsshub.your-domain.com/javbus/home/ja/{番号}
            return f"{base}/javbus/home/ja/{self.uid}"
        
        # 方案 2: 从 item_id 中推断（如果 item_id 包含 rsshub 信息）
        # item_id 格式: tag:google.com,2005:reader/item/xxx 或包含 URL
        if self.item_id and 'rsshub' in self.item_id.lower():
            # 尝试从 item_id 提取 RSSHub URL
            match = re.search(r'(https?://[^/]+/javbus/[^/]+/[^/]+/[^/]+)', self.item_id)
            if match:
                return match.group(1)
        
        # 方案 3: 从 source_url 推断（如果 source_url 是 rsshub 地址）
        if self.source_url and 'rsshub' in self.source_url.lower():
            return self.source_url
        
        logger.warning(f"无法构造 RSSHub URL，请配置 rsshub_base_url 参数")
        return None
    
    def _extract_magnet(self, content: str) -> Optional[str]:
        """从内容中提取磁力链接"""
        import html
        # 先解码 HTML 实体
        content = html.unescape(content)
        
        # 磁力链接正则
        magnet_pattern = r'magnet:\?xt=urn:btih:[a-zA-Z0-9]+[^"\s<>]*'
        match = re.search(magnet_pattern, content)
        if match:
            magnet = match.group(0)
            # 清理可能的 HTML 转义
            magnet = html.unescape(magnet)
            return magnet
        
        # 调试：如果没找到，打印部分内容
        if 'magnet' in content.lower():
            logger.debug(f"检测到'magnet'关键字但未匹配成功，内容片段: {content[:500]}")
        
        return None
    
    def _extract_uid(self, title: str, content: str) -> Optional[str]:
        """
        从标题和内容中提取番号
        
        策略：优先从标题提取，因为标题通常包含正确的番号，
        而内容 HTML 中可能包含其他类似番号的字符串（如推荐内容）
        """
        # 常见番号格式: XXX-123, XXX-1234, XXX-12345, XXX123, XXX-123A 等
        # 数字部分支持 2-5 位（如 01701 是 5 位）
        patterns = [
            r'([A-Z]{2,6}-?\d{2,5}[A-Z]?)',  # 标准格式，支持2-5位数字
        ]
        
        # 第一步：优先从标题提取（更准确）
        for pattern in patterns:
            match = re.search(pattern, title, re.IGNORECASE)
            if match:
                uid = match.group(1).upper()
                # 清理格式：如果没有横线，在数字前添加横线
                uid = re.sub(r'(\d{2,5}[A-Z]?)$', lambda m: '-' + m.group(1), uid) if '-' not in uid else uid
                # 验证：番号前缀应该在常见范围内（避免匹配到其他字符串）
                prefix = uid.split('-')[0] if '-' in uid else uid[:3]
                if len(prefix) >= 2:
                    return uid
        
        # 第二步：如果标题中没有，从内容中提取
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                uid = match.group(1).upper()
                uid = re.sub(r'(\d{2,5}[A-Z]?)$', lambda m: '-' + m.group(1), uid) if '-' not in uid else uid
                prefix = uid.split('-')[0] if '-' in uid else uid[:3]
                if len(prefix) >= 2:
                    return uid
        
        return None


class FreshRSSClient(BaseHTTPClient):
    """FreshRSS API 客户端"""
    
    def __init__(self):
        super().__init__(settings.freshrss_base_url)
        self.auth_token: Optional[str] = None
        
    async def login(self) -> str:
        """
        登录并获取 Auth Token
        POST /accounts/ClientLogin
        """
        url = "/accounts/ClientLogin"
        data = {
            "Email": settings.freshrss_username,
            "Passwd": settings.freshrss_password,
        }
        
        response = await self.post(url, data=data)
        
        # 解析响应，提取 Auth token
        text = response.text
        for line in text.split("\n"):
            if line.startswith("Auth="):
                self.auth_token = line.replace("Auth=", "").strip()
                break
                
        if not self.auth_token:
            raise ValueError("Failed to get auth token from FreshRSS")
            
        logger.info(f"FreshRSS 登录成功")
        return self.auth_token
    
    async def get_starred_items(self) -> List[FreshRSSItem]:
        """
        获取 Starred items
        GET /reader/api/0/stream/contents/user/-/state/com.google/starred
        """
        if not self.auth_token:
            await self.login()
            
        url = "/reader/api/0/stream/contents/user/-/state/com.google/starred"
        headers = {
            "Authorization": f"GoogleLogin auth={self.auth_token}"
        }
        
        response = await self.get(url, headers=headers)
        data = response.json()
        
        items = data.get("items", [])
        logger.info(f"获取到 {len(items)} 个 Starred items")
        
        return [FreshRSSItem.from_api_response(item) for item in items]
    
    async def get_items_by_tag(self, tag: str) -> List[FreshRSSItem]:
        """
        获取带有特定标签的项目
        GET /reader/api/0/stream/contents/user/-/label/{tag}
        
        Args:
            tag: 标签名，如 "源站抓取失败"
            
        Returns:
            带有该标签的项目列表
        """
        if not self.auth_token:
            await self.login()
            
        url = f"/reader/api/0/stream/contents/user/-/label/{tag}"
        headers = {
            "Authorization": f"GoogleLogin auth={self.auth_token}"
        }
        
        try:
            response = await self.get(url, headers=headers)
            data = response.json()
            
            items = data.get("items", [])
            logger.info(f"获取到 {len(items)} 个带有标签 '{tag}' 的项目")
            
            return [FreshRSSItem.from_api_response(item) for item in items]
        except Exception as e:
            logger.warning(f"获取标签 '{tag}' 的项目失败: {e}")
            return []
    
    async def add_tag(self, item_id: str, tag: str) -> bool:
        """
        添加标签
        POST /reader/api/0/edit-tag
        
        Args:
            item_id: 完整条目 ID
            tag: 标签名，如 "已开始下载"
        """
        if not self.auth_token:
            await self.login()
            
        url = "/reader/api/0/edit-tag"
        headers = {
            "Authorization": f"GoogleLogin auth={self.auth_token}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = {
            "i": item_id,
            "a": f"user/-/label/{tag}",
        }
        
        response = await self.post(url, headers=headers, data=data)
        success = response.text.strip() == "OK"
        
        if success:
            logger.info(f"成功添加标签 '{tag}' 到条目 {item_id}")
        else:
            logger.warning(f"添加标签失败: {response.text}")
            
        return success
    
    async def remove_tag(self, item_id: str, tag: str) -> bool:
        """
        移除标签
        POST /reader/api/0/edit-tag
        """
        if not self.auth_token:
            await self.login()
            
        url = "/reader/api/0/edit-tag"
        headers = {
            "Authorization": f"GoogleLogin auth={self.auth_token}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = {
            "i": item_id,
            "r": f"user/-/label/{tag}",
        }
        
        response = await self.post(url, headers=headers, data=data)
        return response.text.strip() == "OK"
    
    async def unstar_item(self, item_id: str) -> bool:
        """
        取消星标
        POST /reader/api/0/edit-tag
        """
        if not self.auth_token:
            await self.login()
            
        url = "/reader/api/0/edit-tag"
        headers = {
            "Authorization": f"GoogleLogin auth={self.auth_token}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = {
            "i": item_id,
            "r": "user/-/state/com.google/starred",
        }
        
        response = await self.post(url, headers=headers, data=data)
        success = response.text.strip() == "OK"
        
        if success:
            logger.info(f"成功取消星标: {item_id}")
            
        return success
