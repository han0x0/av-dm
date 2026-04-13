"""
日志配置
使用 Loguru 实现分层日志输出

三层日志系统：
1. 控制台（Container Manager 视图）
   - INFO: 简洁，用户一眼看懂
   - DEBUG: 详细调试信息
   
2. 日志文件
   - 始终详细，包含模块/行号，供查错
"""

import os
import sys
from pathlib import Path
from loguru import logger as _logger


# 自定义日志级别名称映射
LEVEL_NAMES = {
    "TRACE": "追踪",
    "DEBUG": "调试",
    "INFO": "信息",
    "SUCCESS": "成功",
    "WARNING": "警告",
    "ERROR": "错误",
    "CRITICAL": "严重",
}


def setup_logger():
    """配置日志系统"""
    
    # 从环境变量获取日志级别，默认为 INFO
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    log_file = os.getenv("LOG_FILE", "logs/app.log")
    
    # 移除默认处理器
    _logger.remove()
    
    # ========== 控制台输出（Container Manager 视图）==========
    if log_level == "DEBUG":
        # DEBUG模式：详细输出
        console_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        )
    else:
        # INFO模式：简洁输出，一眼看懂
        # 只显示关键信息：时间 | 状态 | 操作
        console_format = (
            "<green>{time:HH:mm:ss}</green> | "
            "<level>{level.icon}</level> "
            "<level>{message}</level>"
        )
    
    _logger.add(
        sys.stdout,
        level=log_level,
        format=console_format,
        colorize=True,
        filter=lambda record: record["level"].name in ["INFO", "SUCCESS", "WARNING", "ERROR", "CRITICAL"] 
                             or log_level == "DEBUG",
    )
    
    # ========== 日志文件（始终详细，供查错）==========
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    _logger.add(
        log_file,
        level="DEBUG",  # 文件始终记录 DEBUG 及以上级别
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
        rotation="10 MB",
        retention="30 days",
        encoding="utf-8",
        backtrace=True,
        diagnose=True,
    )
    
    return _logger


# 全局日志实例
logger = setup_logger()


# 快捷方法，用于输出简洁的用户友好日志
def log_workflow_start(name: str):
    """记录工作流开始"""
    logger.info(f"▶️  {name}")


def log_workflow_end(name: str, stats: dict):
    """记录工作流结束"""
    # 将 stats 转换为简洁字符串
    parts = []
    for key, value in stats.items():
        if value > 0:
            parts.append(f"{key}={value}")
    stats_str = ", ".join(parts) if parts else "无"
    logger.info(f"✅ {name} 完成 | {stats_str}")


def log_task_started(content_id: str):
    """记录任务开始下载"""
    logger.info(f"⬇️  开始下载: {content_id}")


def log_task_completed(content_id: str):
    """记录任务下载完成"""
    logger.success(f"✓ 下载完成: {content_id}")


def log_task_error(content_id: str, error: str):
    """记录任务错误"""
    logger.error(f"✗ {content_id}: {error}")


def log_javsp_submitted(content_id: str):
    """记录 JavSP 提交"""
    logger.info(f"📁 提交刮削: {content_id}")


def log_javsp_completed(content_id: str):
    """记录 JavSP 完成"""
    logger.success(f"✓ 刮削完成: {content_id}")


def log_cleanup_deleted(content_id: str):
    """记录清理删除"""
    logger.info(f"🗑️  清理完成: {content_id}")
