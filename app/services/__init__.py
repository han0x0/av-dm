"""
服务层 - 封装各外部系统的 API 调用
"""

from app.services.freshrss import FreshRSSClient
from app.services.bitcomet import BitCometClient
from app.services.javsp import JavSPClient
from app.services.jellyfin import JellyfinClient

__all__ = ["FreshRSSClient", "BitCometClient", "JavSPClient", "JellyfinClient"]
