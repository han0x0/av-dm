"""
认证相关 API
"""

from datetime import timedelta
from fastapi import APIRouter, HTTPException, status, Depends

from app.core.auth import (
    verify_password,
    create_access_token,
    get_current_active_user,
    User,
)
from app.api.v1.schemas import LoginRequest, LoginResponse, LogoutResponse, UserInfo
from app.logger import logger

router = APIRouter()


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    用户登录
    
    验证密码并返回 JWT 令牌
    """
    logger.info(f"收到登录请求，密码长度: {len(request.password)}")
    
    if not verify_password(request.password):
        logger.warning(f"登录失败: 密码错误 (输入长度: {len(request.password)})")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="密码错误",
        )
    
    # 创建访问令牌
    access_token = create_access_token(
        data={"sub": "admin"},
        expires_delta=timedelta(days=7)
    )
    
    logger.info("用户登录成功")
    
    return LoginResponse(
        success=True,
        access_token=access_token,
        token_type="bearer",
        message="登录成功"
    )


@router.post("/logout", response_model=LogoutResponse)
async def logout(current_user: User = Depends(get_current_active_user)):
    """
    用户登出
    
    客户端需自行清除令牌，服务端仅记录日志
    """
    logger.info(f"用户登出: {current_user.username}")
    
    return LogoutResponse(
        success=True,
        message="登出成功"
    )


@router.get("/me", response_model=UserInfo)
async def get_me(current_user: User = Depends(get_current_active_user)):
    """
    获取当前用户信息
    """
    return UserInfo(
        username=current_user.username,
        is_authenticated=True
    )
