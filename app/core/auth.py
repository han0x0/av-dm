"""
JWT 认证模块
"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from app.config import settings
from app.logger import logger

# JWT 配置
SECRET_KEY = getattr(settings, 'web_secret_key', 'your-secret-key-change-in-production')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7

# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer 认证
security = HTTPBearer(auto_error=False)


class TokenData(BaseModel):
    """Token 数据模型"""
    username: Optional[str] = None


class User(BaseModel):
    """用户模型"""
    username: str


# 简单密码验证（从环境变量获取）
import os
WEB_PASSWORD = os.getenv('WEB_PASSWORD', settings.web_password)

# 调试日志（启动时打印一次）
logger.info(f"Web UI 密码配置: {WEB_PASSWORD[:3]}*** (长度: {len(WEB_PASSWORD)})")


def verify_password(plain_password: str) -> bool:
    """
    验证密码
    
    简单明文比较，适合内网环境
    生产环境建议使用 bcrypt 加密
    """
    logger.debug(f"密码验证: 输入长度={len(plain_password)}, 配置长度={len(WEB_PASSWORD)}")
    return plain_password == WEB_PASSWORD


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    创建 JWT 访问令牌
    
    Args:
        data: 要编码的数据
        expires_delta: 过期时间增量
        
    Returns:
        JWT 令牌字符串
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    return encoded_jwt


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """
    获取当前用户（依赖注入用）
    
    Args:
        credentials: HTTP Bearer 凭据
        
    Returns:
        User 对象
        
    Raises:
        HTTPException: 认证失败时抛出 401
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的认证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not credentials:
        raise credentials_exception
    
    token = credentials.credentials
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        
        if username is None:
            raise credentials_exception
        
        token_data = TokenData(username=username)
        
    except JWTError as e:
        logger.warning(f"JWT 验证失败: {e}")
        raise credentials_exception
    
    user = User(username=token_data.username)
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    获取当前活跃用户
    
    可扩展为检查用户是否被禁用等
    """
    return current_user
