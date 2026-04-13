"""
HTTP 客户端基类
封装通用的 HTTP 请求逻辑
"""

import httpx
from abc import ABC
from typing import Optional, Dict, Any
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings
from app.logger import logger


class BaseHTTPClient(ABC):
    """HTTP 客户端基类"""
    
    def __init__(self, base_url: str, timeout: int = 30):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.client: Optional[httpx.AsyncClient] = None
        
    async def __aenter__(self):
        await self.connect()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
        
    async def connect(self):
        """建立连接"""
        self.client = httpx.AsyncClient(
            timeout=self.timeout,
            http2=True,
            follow_redirects=True,
        )
        
    async def close(self):
        """关闭连接"""
        if self.client:
            await self.client.aclose()
            self.client = None
            
    async def request(
        self,
        method: str,
        path: str,
        **kwargs
    ) -> httpx.Response:
        """发送 HTTP 请求"""
        if not self.client:
            await self.connect()
            
        url = f"{self.base_url}{path}"
        
        try:
            response = await self.client.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP 错误: {e.response.status_code} - {e.response.text}")
            raise
        except httpx.RequestError as e:
            logger.error(f"请求错误: {e}")
            raise
            
    async def get(self, path: str, **kwargs) -> httpx.Response:
        """GET 请求"""
        return await self.request("GET", path, **kwargs)
        
    async def post(self, path: str, **kwargs) -> httpx.Response:
        """POST 请求"""
        return await self.request("POST", path, **kwargs)
        
    async def put(self, path: str, **kwargs) -> httpx.Response:
        """PUT 请求"""
        return await self.request("PUT", path, **kwargs)
        
    async def delete(self, path: str, **kwargs) -> httpx.Response:
        """DELETE 请求"""
        return await self.request("DELETE", path, **kwargs)
