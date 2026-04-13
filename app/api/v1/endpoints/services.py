"""
服务连接测试 API
用于测试各个外部服务的连接状态
"""

import httpx
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.auth import get_current_active_user, User
from app.config_manager import config_manager
from app.services import FreshRSSClient, BitCometClient, JavSPClient, JellyfinClient

router = APIRouter()


class ServiceTestRequest(BaseModel):
    """服务测试请求"""
    url: str = Field(..., description="服务地址")
    username: str = Field(default="", description="用户名")
    password: str = Field(default="", description="密码")
    api_key: str = Field(default="", description="API Key")
    # BitComet 特有
    client_id: str = Field(default="", description="BitComet Client ID")
    authentication: str = Field(default="", description="BitComet Authentication")


class ServiceTestResponse(BaseModel):
    """服务测试响应"""
    success: bool
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)


async def test_freshrss(url: str, username: str, password: str) -> Dict[str, Any]:
    """测试 FreshRSS 连接
    
    FreshRSS 使用 Google Reader API，登录端点为 /api/greader.php/accounts/ClientLogin
    """
    try:
        base_url = url.rstrip('/')
        # FreshRSS API 基础路径是 /api/greader.php
        login_url = f"{base_url}/api/greader.php/accounts/ClientLogin"
        
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            response = await client.post(
                login_url,
                data={"Email": username, "Passwd": password}
            )
            
            if response.status_code == 200:
                text = response.text
                if "Auth=" in text:
                    auth_token = text.split("Auth=")[1].split("\n")[0].strip()
                    return {
                        "success": True,
                        "message": "连接成功",
                        "details": {"auth_token": auth_token[:20] + "..."}
                    }
                else:
                    return {
                        "success": False,
                        "message": "认证失败，请检查用户名和密码",
                        "details": {}
                    }
            else:
                return {
                    "success": False,
                    "message": f"HTTP 错误: {response.status_code}",
                    "details": {}
                }
    except httpx.ConnectError:
        return {
            "success": False,
            "message": "连接失败，请检查 URL 是否正确",
            "details": {}
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"测试失败: {str(e)}",
            "details": {}
        }


async def test_rsshub(url: str) -> Dict[str, Any]:
    """测试 RSSHub 连接"""
    try:
        base_url = url.rstrip('/')
        test_url = f"{base_url}/healthz"
        
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            response = await client.get(test_url)
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "message": "RSSHub 服务正常",
                    "details": {"status": response.text}
                }
            else:
                return {
                    "success": False,
                    "message": f"服务异常: HTTP {response.status_code}",
                    "details": {}
                }
    except httpx.ConnectError:
        return {
            "success": False,
            "message": "连接失败，请检查 URL 是否正确",
            "details": {}
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"测试失败: {str(e)}",
            "details": {}
        }


async def test_bitcomet(
    url: str, 
    username: str, 
    password: str,
    client_id: str = "",
    authentication: str = ""
) -> Dict[str, Any]:
    """测试 BitComet 连接"""
    try:
        base_url = url.rstrip('/')
        login_url = f"{base_url}/api/webui/login"
        
        # 准备认证数据
        auth_data = authentication or ""
        cid = client_id or "test-client-id"
        
        headers = {
            "client-type": "BitComet WebUI",
            "Content-Type": "application/json",
        }
        
        data = {
            "client_id": cid,
            "authentication": auth_data,
        }
        
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            response = await client.post(login_url, headers=headers, json=data)
            
            result = response.json()
            
            if response.status_code == 200:
                error_code = result.get("error_code", "")
                if error_code == "OK":
                    invite_token = result.get("invite_token", "")
                    return {
                        "success": True,
                        "message": "认证成功",
                        "details": {
                            "invite_token": invite_token[:20] + "..." if invite_token else ""
                        }
                    }
                elif error_code == "APP_ACCESS_DISABLED":
                    return {
                        "success": False,
                        "message": "BitComet 远程访问未启用，请在设置中开启",
                        "details": {}
                    }
                elif "invalid" in error_code.lower() or "auth" in error_code.lower():
                    return {
                        "success": False,
                        "message": "认证失败，请检查 authentication 字段",
                        "details": {"error_code": error_code}
                    }
                else:
                    return {
                        "success": False,
                        "message": f"认证失败: {error_code}",
                        "details": result
                    }
            else:
                return {
                    "success": False,
                    "message": f"HTTP 错误: {response.status_code}",
                    "details": {}
                }
    except httpx.ConnectError:
        return {
            "success": False,
            "message": "连接失败，请检查 URL 是否正确",
            "details": {}
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"测试失败: {str(e)}",
            "details": {}
        }


async def test_javsp(url: str, username: str, password: str) -> Dict[str, Any]:
    """测试 JavSP-Web 连接"""
    try:
        base_url = url.rstrip('/')
        login_url = f"{base_url}/api/auth/login"
        
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            response = await client.post(
                login_url,
                json={"username": username, "password": password}
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("username") == username:
                    return {
                        "success": True,
                        "message": "登录成功",
                        "details": {"user": result.get("username")}
                    }
                else:
                    return {
                        "success": False,
                        "message": "登录失败，请检查用户名和密码",
                        "details": {}
                    }
            elif response.status_code == 401:
                return {
                    "success": False,
                    "message": "认证失败，请检查用户名和密码",
                    "details": {}
                }
            else:
                return {
                    "success": False,
                    "message": f"HTTP 错误: {response.status_code}",
                    "details": {}
                }
    except httpx.ConnectError:
        return {
            "success": False,
            "message": "连接失败，请检查 URL 是否正确",
            "details": {}
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"测试失败: {str(e)}",
            "details": {}
        }


async def test_jellyfin(url: str, api_key: str) -> Dict[str, Any]:
    """测试 Jellyfin 连接"""
    try:
        base_url = url.rstrip('/')
        test_url = f"{base_url}/System/Info"
        
        headers = {
            "X-Emby-Token": api_key,
        }
        
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            response = await client.get(test_url, headers=headers)
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "success": True,
                    "message": "连接成功",
                    "details": {
                        "server_name": result.get("ServerName", ""),
                        "version": result.get("Version", "")
                    }
                }
            elif response.status_code == 401:
                return {
                    "success": False,
                    "message": "API Key 无效",
                    "details": {}
                }
            else:
                return {
                    "success": False,
                    "message": f"HTTP 错误: {response.status_code}",
                    "details": {}
                }
    except httpx.ConnectError:
        return {
            "success": False,
            "message": "连接失败，请检查 URL 是否正确",
            "details": {}
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"测试失败: {str(e)}",
            "details": {}
        }


@router.post("/test/freshrss", response_model=ServiceTestResponse)
async def test_freshrss_endpoint(
    request: ServiceTestRequest,
    current_user: User = Depends(get_current_active_user),
):
    """测试 FreshRSS 连接
    
    如果密码为空，使用已保存的配置进行测试
    """
    config = config_manager.get()
    
    # 使用请求中的值，如果为空则使用已保存的配置
    url = request.url or config.get("freshrss_url", "")
    username = request.username or config.get("freshrss_username", "")
    password = request.password or config.get("freshrss_password", "")
    
    if not url or not username:
        return ServiceTestResponse(
            success=False,
            message="URL 和用户名不能为空",
            details={}
        )
    
    result = await test_freshrss(url, username, password)
    return ServiceTestResponse(**result)


@router.post("/test/rsshub", response_model=ServiceTestResponse)
async def test_rsshub_endpoint(
    request: ServiceTestRequest,
    current_user: User = Depends(get_current_active_user),
):
    """测试 RSSHub 连接"""
    result = await test_rsshub(request.url)
    return ServiceTestResponse(**result)


@router.post("/test/bitcomet", response_model=ServiceTestResponse)
async def test_bitcomet_endpoint(
    request: ServiceTestRequest,
    current_user: User = Depends(get_current_active_user),
):
    """测试 BitComet 连接
    
    如果 authentication 为空，使用已保存的配置进行测试
    """
    config = config_manager.get()
    
    # 使用请求中的值，如果为空则使用已保存的配置
    url = request.url or config.get("bitcomet_url", "")
    username = request.username or config.get("bitcomet_username", "")
    client_id = request.client_id or config.get("bitcomet_client_id", "")
    authentication = request.authentication or config.get("bitcomet_authentication", "")
    
    if not url:
        return ServiceTestResponse(
            success=False,
            message="URL 不能为空",
            details={}
        )
    
    result = await test_bitcomet(
        url, 
        username, 
        "",  # BitComet 使用 authentication 而不是 password
        client_id,
        authentication
    )
    return ServiceTestResponse(**result)


@router.post("/test/javsp", response_model=ServiceTestResponse)
async def test_javsp_endpoint(
    request: ServiceTestRequest,
    current_user: User = Depends(get_current_active_user),
):
    """测试 JavSP-Web 连接
    
    如果密码为空，使用已保存的配置进行测试
    """
    config = config_manager.get()
    
    # 使用请求中的值，如果为空则使用已保存的配置
    url = request.url or config.get("javsp_url", "")
    username = request.username or config.get("javsp_username", "")
    password = request.password or config.get("javsp_password", "")
    
    if not url or not username:
        return ServiceTestResponse(
            success=False,
            message="URL 和用户名不能为空",
            details={}
        )
    
    result = await test_javsp(url, username, password)
    return ServiceTestResponse(**result)


@router.post("/test/jellyfin", response_model=ServiceTestResponse)
async def test_jellyfin_endpoint(
    request: ServiceTestRequest,
    current_user: User = Depends(get_current_active_user),
):
    """测试 Jellyfin 连接
    
    如果 API Key 为空，使用已保存的配置进行测试
    """
    config = config_manager.get()
    
    # 使用请求中的值，如果为空则使用已保存的配置
    url = request.url or config.get("jellyfin_url", "")
    api_key = request.api_key or config.get("jellyfin_api_key", "")
    
    if not url:
        return ServiceTestResponse(
            success=False,
            message="URL 不能为空",
            details={}
        )
    
    result = await test_jellyfin(url, api_key)
    return ServiceTestResponse(**result)


@router.get("/status", response_model=Dict[str, Any])
async def get_services_status(
    current_user: User = Depends(get_current_active_user),
):
    """获取所有服务的配置状态（是否已配置）"""
    config = config_manager.get()
    
    return {
        "freshrss": {
            "configured": bool(config.get("freshrss_url") and config.get("freshrss_username")),
            "url": config.get("freshrss_url", ""),
            "username": config.get("freshrss_username", ""),
        },
        "rsshub": {
            "configured": bool(config.get("rsshub_base_url")),
            "url": config.get("rsshub_base_url", ""),
        },
        "bitcomet": {
            "configured": bool(config.get("bitcomet_url") and config.get("bitcomet_username")),
            "url": config.get("bitcomet_url", ""),
            "username": config.get("bitcomet_username", ""),
            "has_auth": bool(config.get("bitcomet_authentication")),
        },
        "javsp": {
            "configured": bool(config.get("javsp_url") and config.get("javsp_username")),
            "url": config.get("javsp_url", ""),
            "username": config.get("javsp_username", ""),
        },
        "jellyfin": {
            "configured": bool(config.get("jellyfin_url") and config.get("jellyfin_api_key")),
            "url": config.get("jellyfin_url", ""),
            "has_api_key": bool(config.get("jellyfin_api_key")),
        },
    }
