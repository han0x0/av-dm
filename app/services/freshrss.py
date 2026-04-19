"""
FreshRSS API 客户端
基于 Google Reader API
"""

import re
import html
import urllib.parse
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime

import httpx
from app.services.base import BaseHTTPClient
from app.config import settings
from app.logger import logger


@dataclass
class MagnetInfo:
    """磁力链接信息"""
    magnet_url: str
    filename: str
    size_str: str
    size_mb: float
    date: datetime


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
        
        # 提取番号（先提取番号，以便后续用番号校验磁力链接）
        freshrss_item.uid = freshrss_item._extract_uid(freshrss_item.title, content)
        # 提取磁力链接（带番号校验，避免取到相关推荐中的错误番号）
        freshrss_item.magnet_url = freshrss_item._extract_magnet(
            content, validate_uid=freshrss_item.uid
        )
        
        return freshrss_item
    
    async def fetch_magnet_from_source(
        self, 
        rsshub_base_url: Optional[str] = None,
        timeout: int = 30
    ) -> Optional[str]:
        """
        从源站抓取磁力链接
        
        策略：
        1. 优先直接从 JavBus 页面抓取（通过 AJAX 接口获取准确的磁力链接）
        2. 如果 JavBus 失败，fallback 到 RSSHub
        
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
        
        if not self.uid:
            logger.debug(f"条目 {self.id_entry} 无番号，跳过源站抓取")
            return None
        
        # 步骤 1: 优先从 JavBus 直抓
        logger.info(f"尝试从 JavBus 抓取磁力链接: {self.uid}")
        magnet = await self._fetch_magnet_from_javbus(timeout=timeout)
        if magnet:
            self.magnet_url = magnet
            return magnet
        
        # 步骤 2: Fallback 到 RSSHub
        logger.info(f"JavBus 抓取失败，尝试从 RSSHub 抓取: {self.uid}")
        rsshub_url = self._build_rsshub_url(rsshub_base_url)
        if not rsshub_url:
            logger.debug(f"条目 {self.id_entry} 无法构造 RSSHub URL，跳过")
            return None
        
        logger.info(f"尝试从 RSSHub 抓取磁力链接: {rsshub_url}")
        
        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                response = await client.get(rsshub_url)
                response.raise_for_status()
                
                rss_content = response.text
                magnet = self._extract_magnet(rss_content, validate_uid=self.uid)
                
                if magnet:
                    logger.info(f"✅ 从 RSSHub 成功抓取磁力链接: {magnet[:60]}...")
                    self.magnet_url = magnet
                    return magnet
                else:
                    logger.warning(f"⚠️ RSSHub 内容中未找到匹配番号 {self.uid} 的磁力链接")
                    
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ 抓取 RSSHub 失败 (HTTP {e.response.status_code}): {rsshub_url}")
        except httpx.RequestError as e:
            logger.error(f"❌ 抓取 RSSHub 请求失败: {e}")
        except Exception as e:
            logger.error(f"❌ 抓取 RSSHub 异常: {e}")
        
        return None
    
    async def _fetch_magnet_from_javbus(self, timeout: int = 30) -> Optional[str]:
        """
        直接从 JavBus 抓取磁力链接
        
        流程：
        1. 访问 JavBus 番号页面获取 HTML（不跟随重定向，因为 JavBus 的 302
           响应体中已经包含 gid 等关键信息）
        2. 从 HTML 中提取 gid 和 uc
        3. 调用 AJAX 接口获取磁力链接表格
        4. 解析并返回匹配目标番号的磁力链接
        """
        if not self.uid:
            return None
        
        base_url = getattr(settings, 'javbus_base_url', 'https://www.javbus.com')
        base_url = base_url.rstrip('/') if base_url else 'https://www.javbus.com'
        javbus_url = f"{base_url}/ja/{self.uid}"
        
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
        }
        
        try:
            # 禁用 HTTP/2 和自动重定向：
            # - JavBus 在无 cookie 时会返回 302，但响应体中已包含 gid
            # - HTTP/2 下 Cloudflare 对 cookie 的处理可能与 HTTP/1.1 不同
            async with httpx.AsyncClient(
                timeout=timeout,
                follow_redirects=False,
                http2=False,
            ) as client:
                # 1. 获取页面 HTML（允许 302，因为 JavBus 的 302 响应体中有 gid）
                response = await client.get(javbus_url, headers=headers)
                if response.status_code >= 400:
                    logger.debug(
                        f"JavBus 页面返回 HTTP {response.status_code}: {self.uid}"
                    )
                    return None
                
                html_content = response.text
                
                # 2. 提取 gid 和 uc
                gid_match = re.search(r'var\s+gid\s*=\s*(\d+);', html_content)
                uc_match = re.search(r'var\s+uc\s*=\s*(\d+);', html_content)
                
                if not gid_match:
                    logger.debug(f"JavBus 页面未找到 gid: {self.uid}")
                    return None
                
                gid = gid_match.group(1)
                uc = uc_match.group(1) if uc_match else "0"
                
                # 3. 调用 AJAX 接口获取磁力链接
                ajax_url = (
                    f"{base_url}/ajax/uncledatoolsbyajax.php?"
                    f"gid={gid}&lang=ja&uc={uc}&floor=1"
                )
                ajax_headers = {
                    **headers,
                    "Referer": javbus_url,
                    "X-Requested-With": "XMLHttpRequest",
                }
                
                ajax_response = await client.get(ajax_url, headers=ajax_headers)
                ajax_response.raise_for_status()
                ajax_content = ajax_response.text
                
                # 4. 提取并校验磁力链接
                magnet = self._extract_magnet(ajax_content, validate_uid=self.uid)
                if magnet:
                    logger.info(f"✅ 从 JavBus 成功抓取磁力链接: {magnet[:60]}...")
                    return magnet
                
                logger.warning(
                    f"⚠️ JavBus 内容中未找到匹配番号 {self.uid} 的磁力链接"
                )
                
        except httpx.HTTPStatusError as e:
            logger.error(
                f"❌ 抓取 JavBus 失败 (HTTP {e.response.status_code}): {javbus_url}"
            )
        except httpx.RequestError as e:
            logger.error(f"❌ 抓取 JavBus 请求失败: {e}")
        except Exception as e:
            logger.error(f"❌ 抓取 JavBus 异常: {e}")
        
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
    
    def _parse_size_to_mb(self, size_str: str) -> float:
        """将文件大小字符串转换为 MB 数值"""
        size_str = size_str.strip().upper().replace(',', '').replace(' ', '')
        match = re.match(r'^(\d+\.?\d*)\s*(TB|GB|MB)?$', size_str)
        if not match:
            return 0.0
        
        val = float(match.group(1))
        unit = match.group(2) or 'MB'
        
        if unit == 'TB':
            return val * 1024 * 1024
        elif unit == 'GB':
            return val * 1024
        else:  # MB
            return val
    
    def _extract_all_magnets(self, content: str) -> List[MagnetInfo]:
        """
        从 HTML 内容中提取所有磁力链接及其元数据
        
        支持两种格式：
        1. RSS 中的完整表格：<table><tr>...</tr></table>
        2. JavBus AJAX 返回的行片段：<tr>...</tr>（无 table 包裹）
        """
        magnets: List[MagnetInfo] = []
        
        # 策略 1: 尝试从 <table> 中提取行（RSS 格式）
        table_match = re.search(r'<table[^>]*>(.*?)</table>', content, re.DOTALL | re.IGNORECASE)
        if table_match:
            rows = re.findall(r'<tr[^>]*>(.*?)</tr>', table_match.group(1), re.DOTALL | re.IGNORECASE)
        else:
            # 策略 2: 直接从 content 中提取 <tr> 行（JavBus AJAX 格式）
            rows = re.findall(r'<tr[^>]*>(.*?)</tr>', content, re.DOTALL | re.IGNORECASE)
        
        if not rows:
            return magnets
        
        for row in rows:
            # 跳过表头行
            if '<th' in row:
                continue
            
            # 提取 magnet 链接
            magnet_match = re.search(r'href="(magnet:\?xt=urn:btih:[^"]+)"', row, re.IGNORECASE)
            if not magnet_match:
                continue
            
            magnet_url = html.unescape(magnet_match.group(1))
            
            # 提取所有 <td> 的内容
            tds = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL | re.IGNORECASE)
            if len(tds) < 3:
                continue
            
            # 从 dn 参数提取文件名
            filename = ""
            dn_match = re.search(r'[&?]dn=([^&]+)', magnet_url)
            if dn_match:
                filename = urllib.parse.unquote(dn_match.group(1))
            
            # 提取大小和日期（去掉 HTML 标签）
            size_str = re.sub(r'<[^>]+>', '', tds[1]).strip()
            date_str = re.sub(r'<[^>]+>', '', tds[2]).strip()
            
            # 解析日期
            try:
                date = datetime.strptime(date_str, '%Y-%m-%d')
            except ValueError:
                continue
            
            # 解析大小
            size_mb = self._parse_size_to_mb(size_str)
            
            magnets.append(MagnetInfo(
                magnet_url=magnet_url,
                filename=filename,
                size_str=size_str,
                size_mb=size_mb,
                date=date,
            ))
        
        return magnets
    
    def _select_best_magnet(
        self,
        magnets: List[MagnetInfo],
        uid: str
    ) -> Optional[str]:
        """
        按规则选择最佳磁力链接
        
        规则：
        1. 优先：文件名含 -U / -AI / -UC / -uncensored（同一优先级）
           → 组内按日期升序 → 大小升序，选第一个
        2. 次优：文件名含 -C
           → 组内按日期升序 → 大小升序，选第一个
        3. 兜底：以上都没有
           → 按日期降序 → 大小升序，选第一个（最新且最小）
        """
        if not magnets:
            return None
        
        # 过滤出匹配目标番号的磁力
        valid_magnets = [m for m in magnets if self._magnet_matches_uid(m.magnet_url, uid)]
        
        if not valid_magnets:
            # 如果没有明确匹配的，退而求其次：不包含其他明确番号的
            valid_magnets = [m for m in magnets if not self._magnet_has_other_uid(m.magnet_url, uid)]
        
        if not valid_magnets:
            return None
        
        # 无码关键词正则（匹配 uncen, uncensored, uncensored leak 等）
        _uncensored_pattern = re.compile(r'(uncen(sor(ed)?)?([- _\s]*leak(ed)?)?)', re.I)
        
        # 定义优先级判断
        def is_priority_1(m: MagnetInfo) -> bool:
            """无码/破解/流出：优先级 1"""
            name_upper = m.filename.upper()
            # 检查后缀
            suffixes = ['-U', '-AI', '-UC', '-UNCENSORED', '-UNCEN', '-UNCENS', '-LEAK', '-LEAKED']
            if any(suffix in name_upper for suffix in suffixes):
                return True
            # 检查无码关键词
            if _uncensored_pattern.search(m.filename):
                return True
            return False
        
        def is_priority_2(m: MagnetInfo) -> bool:
            """中文字幕：优先级 2（排除已在 P1 中的）"""
            if is_priority_1(m):
                return False
            name_upper = m.filename.upper()
            return any(suffix in name_upper for suffix in ['-C', '-CH', '-CN'])
        
        # 分组
        p1 = [m for m in valid_magnets if is_priority_1(m)]
        p2 = [m for m in valid_magnets if is_priority_2(m)]
        p3 = [m for m in valid_magnets if m not in p1 and m not in p2]
        
        if p1:
            # 日期升序，大小升序
            p1.sort(key=lambda m: m.size_mb)
            p1.sort(key=lambda m: m.date)
            return p1[0].magnet_url
        elif p2:
            p2.sort(key=lambda m: m.size_mb)
            p2.sort(key=lambda m: m.date)
            return p2[0].magnet_url
        elif p3:
            # 兜底：日期降序，大小升序
            p3.sort(key=lambda m: m.size_mb)
            p3.sort(key=lambda m: m.date, reverse=True)
            return p3[0].magnet_url
        
        return None
    
    def _extract_magnet(
        self, content: str, validate_uid: Optional[str] = None
    ) -> Optional[str]:
        """
        从内容中提取磁力链接
        
        Args:
            content: HTML 或文本内容
            validate_uid: 目标番号，如果提供则做 dn 校验，
                         优先返回 dn 中包含目标番号的链接
        """
        # 彻底解码 HTML 实体（处理多次转义如 &amp;amp; -> &amp; -> &）
        while True:
            decoded = html.unescape(content)
            if decoded == content:
                break
            content = decoded
        
        # 新逻辑：如果提供了番号，先尝试从 HTML 表格中解析并选择最佳磁力
        if validate_uid:
            all_magnets = self._extract_all_magnets(content)
            if all_magnets:
                best = self._select_best_magnet(all_magnets, validate_uid)
                if best:
                    return best
        
        # Fallback: 原有的正则提取逻辑（用于非表格格式或表格解析失败的情况）
        magnet_pattern = r'magnet:\?xt=urn:btih:[a-zA-Z0-9]+[^"\s<>\'\)\\]*'
        matches = re.findall(magnet_pattern, content)
        if not matches:
            if 'magnet' in content.lower():
                logger.debug(
                    f"检测到'magnet'关键字但未匹配成功，内容片段: {content[:500]}"
                )
            return None
        
        # 去重并保持原始顺序
        seen = set()
        magnets = []
        for magnet in matches:
            magnet = html.unescape(magnet)
            if magnet not in seen:
                seen.add(magnet)
                magnets.append(magnet)
        
        if not validate_uid:
            return magnets[0]
        
        # 优先选择 dn 中包含目标番号的链接
        for magnet in magnets:
            if self._magnet_matches_uid(magnet, validate_uid):
                return magnet
        
        # 如果没有匹配的，检查是否有不含其他明确番号的链接
        # （避免下载到"相关推荐"中的其他影片）
        for magnet in magnets:
            if not self._magnet_has_other_uid(magnet, validate_uid):
                return magnet
        
        # 所有磁力链接都对应其他明确的番号，拒绝使用
        logger.warning(
            f"所有磁力链接均不匹配目标番号 {validate_uid}，可用链接: {magnets[:3]}"
        )
        return None
    
    def _magnet_matches_uid(self, magnet: str, uid: str) -> bool:
        """检查磁力链接的 dn 参数是否包含目标番号"""
        dn_match = re.search(r'[&?]dn=([^&]+)', magnet)
        if not dn_match:
            return False
        
        dn = urllib.parse.unquote(dn_match.group(1)).upper().replace('-', '')
        uid_norm = uid.upper().replace('-', '')
        return uid_norm in dn
    
    def _magnet_has_other_uid(self, magnet: str, uid: str) -> bool:
        """
        检查磁力链接的 dn 参数中是否包含**其他**明确的番号
        
        返回 True 表示 dn 中有番号但都不是目标番号（说明是其他影片）
        返回 False 表示 dn 中没有明确番号，或包含目标番号
        """
        dn_match = re.search(r'[&?]dn=([^&]+)', magnet)
        if not dn_match:
            return False
        
        dn = urllib.parse.unquote(dn_match.group(1))
        # 提取 dn 中所有可能的番号
        codes = re.findall(r'[A-Z]{2,6}-?\d{2,5}[A-Z]?', dn, re.IGNORECASE)
        if not codes:
            return False
        
        uid_norm = uid.upper().replace('-', '')
        for code in codes:
            if code.upper().replace('-', '') == uid_norm:
                return False
        
        # dn 中有番号，但都不匹配目标番号
        return True
    
    def _extract_uid(self, title: str, content: str) -> Optional[str]:
        """
        从标题和内容中提取番号
        
        策略：优先从标题提取，因为标题通常包含正确的番号，
        而内容 HTML 中可能包含其他类似番号的字符串（如推荐内容）
        
        支持的番号格式（参考 JavSP）：
        FC2, HEYDOUGA, GETCHU, GYUTTO, 259LUXU, MUGEN, IBW,
        普通番号, 东热系列, TMA, R18, 纯数字无码等
        """
        
        def _extract_from_text(text: str) -> Optional[str]:
            """从单个文本中提取番号"""
            norm = text.upper()
            
            # 1. FC2: FC2-123456, FC2PPV-123456
            match = re.search(r'FC2[^A-Z\d]{0,5}(PPV[^A-Z\d]{0,5})?(\d{5,7})', norm, re.I)
            if match:
                return 'FC2-' + match.group(2)
            
            # 2. HEYDOUGA: HEYDOUGA-1234-567
            match = re.search(r'(HEYDOUGA)[-_]*(\d{4})[-_]0?(\d{3,5})', norm, re.I)
            if match:
                return '-'.join(match.groups())
            
            # 3. GETCHU
            match = re.search(r'GETCHU[-_]*(\d+)', norm, re.I)
            if match:
                return 'GETCHU-' + match.group(1)
            
            # 4. GYUTTO
            match = re.search(r'GYUTTO[-_]*(\d+)', norm, re.I)
            if match:
                return 'GYUTTO-' + match.group(1)
            
            # 5. 259LUXU
            match = re.search(r'259LUXU[-_]*(\d+)', norm, re.I)
            if match:
                return '259LUXU-' + match.group(1)
            
            # 6. MUGEN: MKBD-S123, MK3D2DBD-01
            match = re.search(r'(MKB?D)[-_]*(S\d{2,3})|(MK3D2DBD|S2M|S2MBD)[-_]*(\d{2,3})', norm, re.I)
            if match:
                if match.group(1) is not None:
                    return match.group(1) + '-' + match.group(2)
                else:
                    return match.group(3) + '-' + match.group(4)
            
            # 7. IBW with z suffix
            match = re.search(r'(IBW)[-_](\d{2,5}z)', norm, re.I)
            if match:
                return match.group(1) + '-' + match.group(2)
            
            # 8. 数字前缀格式（如 200GANA-3370）
            match = re.search(r'(\d+[A-Z]{2,6}-?\d{2,5}[A-Z]?)', norm, re.I)
            if match:
                uid = match.group(1).upper()
                if '-' not in uid:
                    uid = re.sub(r'(\d{2,5}[A-Z]?)$', r'-\1', uid)
                return uid
            
            # 9. 普通番号（带分隔符）
            match = re.search(r'([A-Z]{2,10})[-_](\d{2,5})', norm, re.I)
            if match:
                return match.group(1) + '-' + match.group(2)
            
            # 10. 东热 RED/SKY/EX
            match = re.search(r'(RED[01]\d\d|SKY[0-3]\d\d|EX00[01]\d)', norm, re.I)
            if match:
                return match.group(1).upper()
            
            # 11. TMA
            match = re.search(r'(T[23]8[-_]\d{3})', norm)
            if match:
                return match.group(1).upper()
            
            # 12. 东热 N/K
            match = re.search(r'(N\d{4}|K\d{4})', norm, re.I)
            if match:
                return match.group(1).upper()
            
            # 13. R18
            match = re.search(r'(R18-?\d{3})', norm, re.I)
            if match:
                return match.group(1).upper()
            
            # 14. 纯数字（无码影片）
            match = re.search(r'(\d{6}[-_]\d{2,3})', norm)
            if match:
                return match.group(1)
            
            # 15. 普通番号（无分隔符，视为缺失横线）
            match = re.search(r'([A-Z]{2,})(\d{2,5})', norm, re.I)
            if match:
                return match.group(1) + '-' + match.group(2)
            
            return None
        
        # 第一步：优先从标题提取（更准确）
        uid = _extract_from_text(title)
        if uid:
            return uid
        
        # 第二步：如果标题中没有，从内容中提取
        uid = _extract_from_text(content)
        if uid:
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
