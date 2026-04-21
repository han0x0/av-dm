"""
Torrent 服务模块

功能：
1. 磁力链接 → .torrent 文件获取（在线缓存 + P2P 备选）
2. .torrent 文件缓存管理
3. 广告文件智能过滤
4. 文件列表解析

使用：
    from app.services.torrent_service import TorrentService
    
    service = TorrentService()
    result = await service.fetch_and_filter(magnet_url)
    # result.torrent_base64, result.files_to_disable, result.main_video
"""

import os
import re
import base64
import urllib.request
import tempfile
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set
from pathlib import Path

from app.config import settings
from app.logger import logger

# libtorrent 是可选依赖，如果不可用则降级为仅在线缓存模式
try:
    import libtorrent as lt
    LIBTORRENT_AVAILABLE = True
except ImportError:
    LIBTORRENT_AVAILABLE = False
    logger.warning("libtorrent 未安装，磁力链接 P2P 获取功能不可用")


# ===== 常量配置 =====

VIDEO_EXTENSIONS: Set[str] = {
    ".mp4", ".mkv", ".avi", ".wmv", ".mov", ".ts", ".m2ts", ".mts"
}

AD_EXTENSIONS: Set[str] = {
    ".url", ".html", ".htm", ".txt", ".apk", ".chm", ".zip", ".exe", ".mht"
}

MIN_VIDEO_SIZE_BYTES = 100 * 1024 * 1024  # 100MB

CACHE_SERVICES = [
    "https://itorrents.org/torrent/{info_hash}.torrent",
    "https://btcache.me/torrent/{info_hash}",
]


@dataclass
class TorrentFileInfo:
    """torrent 中的单个文件信息"""
    index: int
    path: str
    size: int
    ext: str = field(init=False)
    size_mb: float = field(init=False)
    
    def __post_init__(self):
        self.ext = os.path.splitext(self.path)[-1].lower()
        self.size_mb = round(self.size / (1024 * 1024), 2)


@dataclass
class FilterResult:
    """过滤结果"""
    torrent_base64: str
    info_hash: str
    name: str
    files: List[TorrentFileInfo]
    main_video: Optional[TorrentFileInfo] = None
    files_to_disable: List[int] = field(default_factory=list)
    cached: bool = False
    source: str = ""  # "cache" | "libtorrent" | "cache_fallback"


class TorrentCacheManager:
    """.torrent 文件缓存管理器"""
    
    def __init__(self, cache_dir: Optional[str] = None):
        self.cache_dir = Path(cache_dir or os.path.join("data", "torrents"))
        self._ensure_dir()
    
    def _ensure_dir(self):
        """确保缓存目录存在"""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def get_path(self, info_hash: str) -> Path:
        """获取缓存文件路径"""
        return self.cache_dir / f"{info_hash.lower()}.torrent"
    
    def is_cached(self, info_hash: str) -> bool:
        """检查是否已缓存"""
        return self.get_path(info_hash).exists()
    
    def load(self, info_hash: str) -> Optional[bytes]:
        """加载缓存的 .torrent 文件"""
        path = self.get_path(info_hash)
        if path.exists():
            try:
                with open(path, "rb") as f:
                    return f.read()
            except Exception as e:
                logger.warning(f"读取缓存 torrent 失败: {e}")
        return None
    
    def save(self, info_hash: str, data: bytes) -> bool:
        """保存 .torrent 文件到缓存"""
        try:
            self._ensure_dir()
            path = self.get_path(info_hash)
            with open(path, "wb") as f:
                f.write(data)
            logger.debug(f"Torrent 已缓存: {path}")
            return True
        except Exception as e:
            logger.warning(f"保存 torrent 缓存失败: {e}")
            return False


class TorrentFileFilter:
    """广告文件过滤器"""
    
    @staticmethod
    def filter(files: List[TorrentFileInfo]) -> List[int]:
        """
        返回需要禁用的文件索引列表
        
        规则：
        1. 非视频扩展名 → 禁用
        2. 视频扩展名但 < 100MB → 禁用（广告小视频）
        3. 视频扩展名且 >= 100MB → 保留（主视频/VR分卷）
        """
        to_disable = []
        
        for f in files:
            should_keep = False
            
            # 规则1: 必须是视频格式
            if f.ext in VIDEO_EXTENSIONS:
                # 规则2: 必须 >= 100MB
                if f.size >= MIN_VIDEO_SIZE_BYTES:
                    should_keep = True
            
            if not should_keep:
                to_disable.append(f.index)
                logger.debug(f"[过滤] 禁用文件 [{f.index}] {f.path} ({f.size_mb} MB, ext={f.ext})")
        
        return to_disable
    
    @staticmethod
    def find_main_video(files: List[TorrentFileInfo]) -> Optional[TorrentFileInfo]:
        """找出主视频文件（最大的视频文件）"""
        video_files = [f for f in files if f.ext in VIDEO_EXTENSIONS and f.size >= MIN_VIDEO_SIZE_BYTES]
        if not video_files:
            return None
        return max(video_files, key=lambda f: f.size)


class MagnetMetadataFetcher:
    """磁力链接 metadata 获取器"""
    
    def __init__(self, timeout: int = 60):
        self.timeout = timeout
        self.session = None
    
    def _init_session(self):
        """初始化 libtorrent session"""
        if not LIBTORRENT_AVAILABLE:
            raise RuntimeError("libtorrent 未安装")
        self.session = lt.session()
        logger.debug("[libtorrent] Session 初始化完成")
    
    @staticmethod
    def extract_info_hash(magnet_url: str) -> Optional[str]:
        """从磁力链接提取 info_hash"""
        match = re.search(r"btih:([a-fA-F0-9]{40})", magnet_url)
        if match:
            return match.group(1).lower()
        return None
    
    @staticmethod
    def _try_online_cache(info_hash: str) -> Optional[bytes]:
        """尝试从在线缓存服务获取 .torrent"""
        info_hash = info_hash.lower()
        
        for url_template in CACHE_SERVICES:
            url = url_template.format(info_hash=info_hash)
            try:
                logger.debug(f"[缓存] 尝试: {url}")
                req = urllib.request.Request(
                    url,
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
                )
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = resp.read()
                    if len(data) > 100:
                        logger.info(f"[缓存] 成功获取 ({len(data)} bytes): {url}")
                        return data
            except Exception as e:
                logger.debug(f"[缓存] 失败: {url} - {e}")
                continue
        
        return None
    
    def _fetch_via_libtorrent(self, magnet_url: str) -> Optional[bytes]:
        """通过 P2P 网络获取 metadata"""
        if not LIBTORRENT_AVAILABLE:
            return None
        
        if self.session is None:
            self._init_session()
        
        temp_dir = tempfile.mkdtemp(prefix="magnet_")
        
        try:
            params = lt.parse_magnet_uri(magnet_url)
        except Exception as e:
            logger.warning(f"解析磁力链接失败: {e}")
            return None
        
        params.save_path = temp_dir
        params.storage_mode = lt.storage_mode_t.storage_mode_allocate
        params.flags |= lt.torrent_flags.paused
        
        try:
            handle = self.session.add_torrent(params)
        except Exception as e:
            logger.warning(f"添加 torrent 失败: {e}")
            return None
        
        info_hash = str(handle.info_hash())
        logger.info(f"[libtorrent] 等待 metadata: {info_hash}")
        
        import time
        start_time = time.time()
        last_peers = -1
        
        try:
            while not handle.status().has_metadata:
                elapsed = time.time() - start_time
                if elapsed > self.timeout:
                    logger.warning(f"[libtorrent] 获取 metadata 超时 ({self.timeout}s)")
                    self.session.remove_torrent(handle)
                    return None
                
                status = handle.status()
                if status.num_peers != last_peers:
                    logger.debug(f"[libtorrent] peers: {status.num_peers}, state: {status.state}")
                    last_peers = status.num_peers
                
                time.sleep(1)
        except Exception as e:
            logger.warning(f"[libtorrent] 等待 metadata 异常: {e}")
            self.session.remove_torrent(handle)
            return None
        
        elapsed = time.time() - start_time
        logger.info(f"[libtorrent] Metadata 获取成功！耗时 {elapsed:.1f}s")
        
        try:
            torrent_info = handle.torrent_file()
            ct = lt.create_torrent(torrent_info)
            torrent_data = lt.bencode(ct.generate())
            
            # 设置优先级为0，停止下载
            priorities = [0] * torrent_info.num_files()
            handle.prioritize_files(priorities)
            
            self.session.remove_torrent(handle, option=lt.session.delete_files)
            return torrent_data
        except Exception as e:
            logger.warning(f"[libtorrent] 生成 torrent 文件失败: {e}")
            self.session.remove_torrent(handle)
            return None
    
    def close(self):
        """关闭 session"""
        if self.session:
            self.session.pause()
            self.session = None
    
    def fetch(self, magnet_url: str, use_cache_first: bool = True) -> tuple:
        """
        获取 .torrent 文件数据
        
        Returns:
            (bytes, str): (torrent数据, 来源), 失败时返回 (None, "")
        """
        info_hash = self.extract_info_hash(magnet_url)
        if not info_hash:
            logger.warning(f"无法从磁力链接提取 info_hash: {magnet_url[:80]}")
            return None, ""
        
        # 尝试1: 在线缓存
        if use_cache_first:
            data = self._try_online_cache(info_hash)
            if data:
                return data, "cache"
        
        # 尝试2: libtorrent P2P
        data = self._fetch_via_libtorrent(magnet_url)
        if data:
            return data, "libtorrent"
        
        # 尝试3: 再次尝试缓存（如果之前没试）
        if not use_cache_first:
            data = self._try_online_cache(info_hash)
            if data:
                return data, "cache_fallback"
        
        logger.warning(f"所有获取方式均失败: {magnet_url[:80]}")
        return None, ""


class TorrentService:
    """
    Torrent 服务统一入口
    
    封装了缓存、获取、过滤的完整流程
    """
    
    def __init__(self):
        self.cache = TorrentCacheManager()
        self.fetcher = MagnetMetadataFetcher(timeout=60)
        self.filter = TorrentFileFilter()
    
    def _parse_torrent(self, torrent_data: bytes) -> FilterResult:
        """解析 .torrent 文件"""
        if not LIBTORRENT_AVAILABLE:
            raise RuntimeError("libtorrent 未安装，无法解析 torrent 文件")
        
        info = lt.torrent_info(lt.bdecode(torrent_data))
        name = info.name()
        info_hash = str(info.info_hash())
        
        files = []
        for i in range(info.num_files()):
            files.append(TorrentFileInfo(
                index=i,
                path=info.files().file_path(i),
                size=info.files().file_size(i),
            ))
        
        files_to_disable = self.filter.filter(files)
        main_video = self.filter.find_main_video(files)
        
        return FilterResult(
            torrent_base64=base64.b64encode(torrent_data).decode('utf-8'),
            info_hash=info_hash,
            name=name,
            files=files,
            main_video=main_video,
            files_to_disable=files_to_disable,
        )
    
    async def fetch_and_filter(self, magnet_url: str) -> Optional[FilterResult]:
        """
        完整流程：获取 .torrent → 解析 → 过滤广告
        
        Returns:
            FilterResult: 包含过滤结果，或 None（获取失败）
        """
        info_hash = self.fetcher.extract_info_hash(magnet_url)
        if not info_hash:
            logger.warning(f"无效的磁力链接: {magnet_url[:80]}")
            return None
        
        # 1. 检查本地缓存
        torrent_data = self.cache.load(info_hash)
        if torrent_data:
            logger.info(f"[TorrentService] 命中本地缓存: {info_hash}")
            result = self._parse_torrent(torrent_data)
            result.cached = True
            result.source = "local_cache"
            return result
        
        # 2. 在线获取
        logger.info(f"[TorrentService] 获取 .torrent: {info_hash}")
        torrent_data, source = self.fetcher.fetch(magnet_url, use_cache_first=True)
        
        if not torrent_data:
            logger.warning(f"[TorrentService] 获取失败: {info_hash}")
            return None
        
        # 3. 保存缓存
        self.cache.save(info_hash, torrent_data)
        
        # 4. 解析并过滤
        result = self._parse_torrent(torrent_data)
        result.source = source
        
        # 统计信息
        total_files = len(result.files)
        disable_count = len(result.files_to_disable)
        keep_count = total_files - disable_count
        
        logger.info(
            f"[TorrentService] 过滤完成: {result.name}, "
            f"总计 {total_files} 个文件, 保留 {keep_count} 个, 禁用 {disable_count} 个"
        )
        
        if result.main_video:
            logger.info(f"[TorrentService] 主视频: {result.main_video.path} ({result.main_video.size_mb} MB)")
        
        return result
    
    def close(self):
        """清理资源"""
        self.fetcher.close()
