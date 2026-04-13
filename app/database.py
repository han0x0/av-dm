"""
数据库配置和模型定义
使用 SQLAlchemy 2.0 风格
"""

from datetime import datetime
from typing import Optional, List

from sqlalchemy import create_engine, String, Integer, Boolean, DateTime, Float, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker, Session

from app.config import settings
from app.logger import logger


class Base(DeclarativeBase):
    """SQLAlchemy 基础类"""
    pass


class DownloadRecord(Base):
    """
    下载记录表
    对应原 DataTable AV-Downloads
    """
    __tablename__ = "download_records"
    
    # 主键
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # 内容信息
    content_id: Mapped[str] = mapped_column(String(50), index=True, comment="番号，如 300MIUM-1334")
    content_title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, comment="完整标题")
    magnet_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True, comment="磁力链接")
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="文件大小(bytes)")
    
    # FreshRSS 关联
    freshrss_item_id: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, comment="FreshRSS 条目完整ID")
    id_entry: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="FreshRSS 内部ID")
    
    # BitComet 关联
    bitcomet_task_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True, comment="BitComet 任务ID(动态)")
    bitcomet_task_guid: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True, unique=True, comment="BitComet 任务GUID(不变)")
    
    # BitComet 任务详情（用于监控和诊断）
    task_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, comment="任务类型: BT/HTTP等")
    download_rate: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="下载速度(B/s)")
    upload_rate: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="上传速度(B/s)")
    error_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="错误码")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="错误信息")
    health: Mapped[Optional[str]] = mapped_column(String(10), nullable=True, comment="健康度")
    file_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="文件数")
    share_ratio: Mapped[Optional[float]] = mapped_column(nullable=True, comment="分享率")
    progress: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="进度(千分比)")  # 1000 = 100%
    
    # 状态管理
    status: Mapped[str] = mapped_column(
        String(30), 
        default="pending", 
        index=True,
        comment="状态: pending/running/completed/error/javsp_error/duplicate_cancelled/timeout/timeout_javsp_pending"
    )
    file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, comment="下载文件路径")
    save_folder: Mapped[Optional[str]] = mapped_column(
        String(500), 
        nullable=True, 
        comment="BitComet下载根目录，固定为 {download_path}/{content_id}"
    )
    tags: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, comment="标签记录")
    
    # JavSP 相关
    javsp_task_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="JavSP 刮削任务ID")
    javsp_checked: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否已检测整理状态")
    folder_cleaned: Mapped[bool] = mapped_column(Boolean, default=False, comment="原下载文件夹是否已清理")
    javsp_retry_count: Mapped[int] = mapped_column(Integer, default=0, comment="JavSP 刮削重试次数")
    
    # 超时相关
    timeout_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment="超时标记时间")
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow,
        comment="更新时间"
    )
    
    def __repr__(self) -> str:
        return f"<DownloadRecord(id={self.id}, content_id='{self.content_id}', status='{self.status}')>"


# 数据库引擎
# 数据库引擎配置
# 连接池设置：pool_size=20, max_overflow=30, pool_timeout=60
engine = create_engine(
    settings.database_url,
    echo=settings.debug,  # 调试模式下输出 SQL
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
    pool_size=20,  # 连接池大小
    max_overflow=30,  # 溢出连接数
    pool_timeout=60,  # 获取连接超时时间（秒）
    pool_recycle=3600,  # 连接回收时间（1小时），防止连接过期
    pool_pre_ping=True,  # 使用前检查连接是否有效
)

# 会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """初始化数据库，创建所有表"""
    Base.metadata.create_all(bind=engine)
    logger.info("数据库初始化完成")


def get_db() -> Session:
    """获取数据库会话（生成器模式，用于依赖注入）"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_session() -> Session:
    """直接获取数据库会话"""
    return SessionLocal()
