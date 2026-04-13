"""
认证相关 Schema
"""

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """登录请求"""
    password: str = Field(..., description="密码", min_length=1)


class LoginResponse(BaseModel):
    """登录响应"""
    success: bool = Field(..., description="是否成功")
    access_token: str = Field(..., description="访问令牌")
    token_type: str = Field(default="bearer", description="令牌类型")
    message: str = Field(..., description="提示信息")


class UserInfo(BaseModel):
    """用户信息"""
    username: str = Field(..., description="用户名")
    is_authenticated: bool = Field(True, description="是否已认证")


class LogoutResponse(BaseModel):
    """登出响应"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="提示信息")
