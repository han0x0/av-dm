"""
Workflow 3 & 4: 硬盘空间管理 & 整理完成检测

- Workflow 3: 限制 Jellyfin 媒体库影片数量，删除最旧的条目
- Workflow 4: 检测 JavSP-web 整理完成，删除 BitComet 任务清理残留
- Workflow 4b: 处理 timeout 任务（用户在迅雷等软件下载完成后，提交 JavSP 整理）
"""

import os
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session

from app.services import BitCometClient, JavSPClient, JellyfinClient
from app.services.javsp import find_actual_media_folder, get_safe_folder_path
from app.database import get_db_session, DownloadRecord
from app.config import settings
from app.logger import logger, log_workflow_start, log_workflow_end, log_cleanup_deleted


class CleanupWorkflow:
    """清理工作流"""
    
    def __init__(self):
        self.bitcomet = BitCometClient()
        self.javsp = JavSPClient()
        self.jellyfin = JellyfinClient()
        
    async def __aenter__(self):
        await self.bitcomet.connect()
        await self.javsp.connect()
        await self.jellyfin.connect()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.bitcomet.close()
        await self.javsp.close()
        await self.jellyfin.close()
    
    async def run(self) -> dict:
        """
        执行完整清理工作流
        
        Returns:
            执行统计信息
        """
        stats = {
            "jellyfin_deleted": 0,
            "db_deleted": 0,
            "bitcomet_deleted": 0,
            "folders_checked": 0,
            "errors": 0,
            "timeout_submitted": 0,  # 新增：timeout 任务提交 JavSP 数
            "timeout_completed": 0,  # 新增：timeout 任务整理完成数
        }
        
        logger.info("=" * 50)
        logger.info("开始执行 Workflow 3 & 4: 空间管理与清理")
        logger.info("=" * 50)
        
        # Workflow 3: Jellyfin 空间管理
        await self._cleanup_jellyfin(stats)
        
        # Workflow 4b: 处理 timeout 任务（先处理，再处理正常的 completed）
        await self._process_timeout_tasks(stats)
        
        # Workflow 4: JavSP-web 整理检测
        await self._check_javsp_completed(stats)
        
        logger.info("=" * 50)
        logger.info(f"清理工作流执行完成: {stats}")
        logger.info("=" * 50)
        
        return stats
    
    # ============================================
    # Workflow 3: Jellyfin 空间管理
    # ============================================
    
    async def _cleanup_jellyfin(self, stats: dict):
        """
        清理 Jellyfin 媒体库，保持影片数量不超过限制
        删除最早的条目，同时删除数据库记录
        """
        logger.info("执行 Workflow 3: Jellyfin 空间管理")
        
        try:
            # 1. 获取 Jellyfin 影片数量
            movie_count = await self.jellyfin.get_movie_count()
            logger.info(f"Jellyfin 当前影片数量: {movie_count}")
            
            # 2. 判断是否需要删除
            if movie_count <= settings.max_completed_downloads:
                logger.info(f"影片数量 {movie_count} <= 限制 {settings.max_completed_downloads}，无需清理")
                return
            
            # 3. 计算需删除数量
            delete_count = movie_count - settings.max_completed_downloads
            logger.info(f"需要删除 {delete_count} 个最早添加的影片")
            
            # 4. 获取最早的 N 个影片
            oldest_items = await self.jellyfin.get_oldest_movies(delete_count)
            
            if not oldest_items:
                logger.warning("未找到可删除的影片")
                return
            
            # 5. 循环删除
            db = get_db_session()
            try:
                for item in oldest_items:
                    await self._delete_jellyfin_item(item, db, stats)
            finally:
                db.close()
                
        except Exception as e:
            logger.exception(f"Jellyfin 空间管理失败: {e}")
            stats["errors"] += 1
    
    async def _delete_jellyfin_item(
        self, 
        item, 
        db: Session, 
        stats: dict
    ):
        """删除单个 Jellyfin 条目及对应数据库记录"""
        item_name = item.name
        item_id = item.id
        
        logger.info(f"删除 Jellyfin 条目: {item_name} ({item_id})")
        
        try:
            # 1. 从数据库查找对应记录（通过番号匹配）
            # 从路径中提取番号，或尝试从名称匹配
            record = await self._find_record_by_jellyfin_item(item, db)
            
            # 2. 删除 Jellyfin 条目
            success = await self.jellyfin.delete_item(item_id)
            if not success:
                logger.warning(f"删除 Jellyfin 条目失败: {item_name}")
                stats["errors"] += 1
                return
            
            stats["jellyfin_deleted"] += 1
            
            # 3. 删除数据库记录
            if record:
                db.delete(record)
                db.commit()
                stats["db_deleted"] += 1
                logger.info(f"已删除数据库记录: {record.content_id}")
            else:
                logger.debug(f"未找到对应的数据库记录: {item_name}")
                
        except Exception as e:
            logger.exception(f"删除 Jellyfin 条目失败 {item_name}: {e}")
            db.rollback()
            stats["errors"] += 1
    
    async def _find_record_by_jellyfin_item(self, item, db: Session) -> Optional[DownloadRecord]:
        """
        根据 Jellyfin 条目查找对应的数据库记录
        
        匹配策略：
        1. 从路径中提取番号（如 /path/BEAF-206/xxx.mp4）
        2. 从名称中匹配番号
        """
        import re
        
        # 尝试从路径中提取番号
        path = item.path
        name = item.name
        
        # 常见番号格式：XXX-123, XXX-123A, ABC123, etc.
        pattern = r'(\d*[A-Z]{2,6})[-_]?([0-9]{2,5})([A-Z]?)'
        
        # 先从路径匹配
        matches = re.findall(pattern, path.upper())
        for match in matches:
            content_id = f"{match[0]}-{match[1]}{match[2]}".rstrip('-')
            record = db.query(DownloadRecord).filter(
                DownloadRecord.content_id.ilike(content_id)
            ).first()
            if record:
                return record
        
        # 再从名称匹配
        matches = re.findall(pattern, name.upper())
        for match in matches:
            content_id = f"{match[0]}-{match[1]}{match[2]}".rstrip('-')
            record = db.query(DownloadRecord).filter(
                DownloadRecord.content_id.ilike(content_id)
            ).first()
            if record:
                return record
        
        return None
    
    # ============================================
    # Workflow 4b: 处理 timeout 任务
    # ============================================
    
    async def _process_timeout_tasks(self, stats: dict):
        """
        处理 timeout 任务
        
        场景：
        - 任务在 BitComet 中超时（>48小时未完成）
        - 用户在迅雷等其他软件中手动下载了同样的磁力链接
        - 文件夹中存在可整理的视频文件
        
        流程：
        1. 查询 status='timeout' 的记录
        2. 检查文件夹是否有可整理的视频文件
        3. 如果有 → 提交 JavSP 刮削，状态改为 'timeout_javsp_pending'
        4. 如果状态已是 'timeout_javsp_pending' → 检测是否整理完成
           - 完成 → 删除 BitComet 任务和文件夹
        """
        log_workflow_start("W4b-超时任务处理")
        
        db = get_db_session()
        try:
            # 1. 处理 status='timeout' 的任务（提交 JavSP）
            timeout_records = db.query(DownloadRecord).filter(
                DownloadRecord.status == "timeout"
            ).all()
            
            if timeout_records:
                logger.info(f"发现 {len(timeout_records)} 个 timeout 任务待处理")
                await self.javsp.login()
                
                for record in timeout_records:
                    await self._process_timeout_submit(record, db, stats)
            
            # 2. 处理 status='timeout_javsp_pending' 的任务（检测整理完成）
            pending_records = db.query(DownloadRecord).filter(
                DownloadRecord.status == "timeout_javsp_pending"
            ).all()
            
            if pending_records:
                logger.info(f"发现 {len(pending_records)} 个 timeout_javsp_pending 任务待检测")
                await self.javsp.login()
                await self.bitcomet.login()
                
                for record in pending_records:
                    await self._process_timeout_check(record, db, stats)
                    
        finally:
            db.close()
    
    async def _process_timeout_submit(
        self,
        record: DownloadRecord,
        db: Session,
        stats: dict
    ):
        """提交 timeout 任务到 JavSP"""
        content_id = record.content_id
        symlink_created = False
        
        try:
            # 构建文件夹路径
            base_folder = record.save_folder or f"{settings.bitcomet_download_path}/{content_id}"
            actual_folder = find_actual_media_folder(base_folder, content_id=content_id)
            
            # 处理长文件夹名：创建短路径软链接
            safe_folder, symlink_created = get_safe_folder_path(actual_folder, content_id)
            
            folder_path = safe_folder.replace(
                settings.bitcomet_download_path,
                settings.javsp_input_path
            )
            
            # 检查文件夹是否有可整理的视频文件
            scan_result = await self.javsp.scan_folder(folder_path)
            file_count = scan_result.get("count", 0)
            
            if file_count == 0:
                logger.debug(f"文件夹为空，跳过: {content_id}")
                return
            
            logger.info(f"🎯 发现可整理文件({file_count}个): {content_id}")
            
            # 提交 JavSP 刮削任务
            javsp_task = await self.javsp.create_task(folder_path, profile="default")
            
            if javsp_task:
                record.javsp_task_id = javsp_task.task_id
                record.status = "timeout_javsp_pending"
                db.commit()
                
                stats["timeout_submitted"] += 1
                logger.info(f"✓ 已提交 JavSP: {content_id}")
            else:
                logger.warning(f"JavSP 返回空任务: {content_id}")
                
        except Exception as e:
            logger.error(f"✗ {content_id}: {str(e)[:50]}")
            stats["errors"] += 1
        finally:
            # 清理软链接（如果创建了）
            if symlink_created:
                try:
                    link_path = os.path.join("/tmp/javsp_links", content_id)
                    if os.path.islink(link_path):
                        os.unlink(link_path)
                        logger.debug(f"清理软链接: {link_path}")
                except Exception:
                    pass
    
    async def _process_timeout_check(
        self,
        record: DownloadRecord,
        db: Session,
        stats: dict
    ):
        """检查 timeout_javsp_pending 任务是否整理完成"""
        content_id = record.content_id
        
        try:
            # 构建文件夹路径
            base_folder = record.save_folder or f"{settings.bitcomet_download_path}/{content_id}"
            actual_folder = find_actual_media_folder(base_folder, content_id=content_id)
            folder_path = actual_folder.replace(
                settings.bitcomet_download_path,
                settings.javsp_input_path
            )
            
            # 检查是否已整理完成
            is_processed = await self._check_javsp_processed(content_id, folder_path)
            
            if is_processed:
                logger.info(f"✓ 整理完成: {content_id}")
                
                # 删除 BitComet 任务（delete_all 会清理残留文件夹）
                await self._delete_bitcomet_task(record, db, stats)
                
                # 更新状态
                record.javsp_checked = True
                record.folder_cleaned = True
                db.commit()
                
                stats["timeout_completed"] += 1
                log_cleanup_deleted(content_id)
            else:
                logger.debug(f"未整理完成: {content_id}")
                
        except Exception as e:
            logger.error(f"✗ {content_id}: {str(e)[:50]}")
            stats["errors"] += 1
    
    # ============================================
    # Workflow 4: JavSP-web 整理完成检测
    # ============================================
    
    async def _check_javsp_completed(self, stats: dict):
        """
        检测 JavSP-web 整理完成的任务
        删除 BitComet 任务（delete_all 会清理残留文件夹）
        """
        log_workflow_start("W4-整理检测")
        
        db = get_db_session()
        try:
            # 1. 查询待检测任务
            pending_records = db.query(DownloadRecord).filter(
                DownloadRecord.status == "completed",
                DownloadRecord.javsp_checked == False
            ).order_by(
                DownloadRecord.created_at.asc()
            ).limit(10).all()
            
            if not pending_records:
                logger.debug("无待检测任务")
                return
            
            logger.info(f"🔍 检测: {len(pending_records)}个任务")
            
            # 2. 登录 JavSP 和 BitComet
            await self.javsp.login()
            await self.bitcomet.login()
            
            # 3. 循环处理每个任务
            for record in pending_records:
                await self._check_single_task(record, db, stats)
                
        finally:
            db.close()
    
    async def _check_single_task(
        self, 
        record: DownloadRecord, 
        db: Session, 
        stats: dict
    ):
        """检查单个任务是否已整理完成"""
        content_id = record.content_id
        base_folder = record.save_folder or f"{settings.bitcomet_download_path}/{content_id}"
        actual_folder = find_actual_media_folder(base_folder, content_id=content_id)
        folder_path = actual_folder.replace(
            settings.bitcomet_download_path,
            settings.javsp_input_path
        )
        
        logger.debug(f"检查任务: {content_id}")
        
        try:
            # 扫描文件夹判断是否已整理完成
            # 通过 JavSP-web API 检查文件夹状态
            is_processed = await self._check_javsp_processed(content_id, folder_path)
            
            if is_processed:
                log_cleanup_deleted(content_id)
                
                # 删除 BitComet 任务
                await self._delete_bitcomet_task(record, db, stats)
                
                # 更新数据库状态
                record.javsp_checked = True
                record.folder_cleaned = True
                db.commit()
                
                stats["folders_checked"] += 1
            else:
                logger.debug(f"未整理: {content_id}")
                await self._retry_javsp_task(record, db)
                
        except Exception as e:
            logger.error(f"✗ {content_id}: {str(e)[:50]}")
            stats["errors"] += 1
    
    def _has_related_video_files(self, folder_path: str, content_id: str) -> bool:
        """
        检查文件夹中是否还有与番号相关的视频文件
        
        双重检测机制：
        方式1：去掉"-"完全匹配（如 KNB-406 匹配 KNB406、KNB-406-CD1）
        方式2："-"前后分开匹配（如 KNB-406 需要同时匹配 KNB 和 406）
        
        只要满足任一方式即认为是相关文件
        
        用于判断 JavSP 是否已完成整理（目标视频文件已被移走）
        """
        if not os.path.isdir(folder_path):
            return False
        
        video_exts = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.ts', '.m2ts'}
        
        # 准备番号的两种匹配形式
        content_id_upper = content_id.upper()
        # 方式1：去掉横线
        content_id_no_dash = content_id_upper.replace('-', '')
        # 方式2：分割成部分（如 KNB-406 → ['KNB', '406']）
        content_id_parts = content_id_upper.split('-') if '-' in content_id_upper else [content_id_upper]
        
        try:
            for name in os.listdir(folder_path):
                full_path = os.path.join(folder_path, name)
                if os.path.isfile(full_path):
                    ext = os.path.splitext(name)[1].lower()
                    if ext in video_exts:
                        name_upper = name.upper()
                        
                        # 方式1：去掉横线匹配
                        name_no_dash = name_upper.replace('-', '').replace('_', '').replace(' ', '')
                        if content_id_no_dash in name_no_dash:
                            logger.debug(f"方式1匹配成功 ({content_id}): {name}")
                            return True
                        
                        # 方式2：分割部分匹配（所有部分都必须在文件名中找到）
                        name_no_ext = os.path.splitext(name_upper)[0]
                        all_parts_found = all(part in name_no_ext for part in content_id_parts)
                        if all_parts_found:
                            logger.debug(f"方式2匹配成功 ({content_id}): {name}")
                            return True
                        
        except Exception as e:
            logger.debug(f"检查视频文件失败: {e}")
        
        return False
    
    async def _check_javsp_processed(self, content_id: str, folder_path: str) -> bool:
        """
        检查 JavSP-web 是否已处理该文件夹
        
        策略（三种方式结合）：
        1. 基于番号反向检测：如果文件夹中没有包含番号的视频文件 → 已整理完成
        2. scan_folder 检查：count==0 表示文件夹已空/被删除
        3. 备用：查询历史记录确认是否成功处理
        """
        try:
            # 方式1: 基于番号的反向检测（最准确）
            has_related_videos = self._has_related_video_files(folder_path, content_id)
            
            if not has_related_videos:
                # 没有相关视频文件，说明 JavSP 已整理完成
                # （可能有残留的字幕文件 .txt 或其他无关文件）
                logger.debug(f"文件夹中无相关视频文件，JavSP 整理完成: {content_id}")
                return True
            else:
                logger.debug(f"文件夹中仍有相关视频文件，未整理: {content_id}")
                return False
            
        except Exception as e:
            logger.debug(f"番号反向检测失败，使用备用方案: {e}")
        
        # 方式2: scan_folder 检查文件夹状态（备用）
        try:
            scan_result = await self.javsp.scan_folder(folder_path)
            file_count = scan_result.get("count", -1)
            
            if file_count == 0:
                logger.debug(f"文件夹已空，JavSP 整理完成: {content_id}")
                return True
            elif file_count > 0:
                logger.debug(f"文件夹仍有 {file_count} 个文件，未整理: {content_id}")
                return False
        except Exception as e:
            logger.debug(f"scan_folder 检查失败，使用历史记录备用: {e}")
        
        # 方式3: 在历史记录中查找（最后备用）
        try:
            history_item = await self.javsp.find_in_history(content_id)
            
            if history_item:
                if history_item.cover_download_success or history_item.fanart_download_success:
                    logger.debug(f"JavSP-web 历史记录中找到 {content_id}，已处理成功")
                    return True
        except Exception as e:
            logger.warning(f"检查 JavSP-web 处理状态失败: {e}")
        
        return False
    
    async def _delete_bitcomet_task(
        self, 
        record: DownloadRecord, 
        db: Session,
        stats: dict
    ):
        """删除 BitComet 任务（delete_all 会清理残留文件夹）"""
        content_id = record.content_id
        
        try:
            deleted = False
            
            # 优先使用 task_guid 查找并删除
            if record.bitcomet_task_guid:
                try:
                    tasks = await self.bitcomet.get_task_list()
                    for task in tasks:
                        if task.task_guid == record.bitcomet_task_guid:
                            await self.bitcomet.delete_task(
                                task.task_id,
                                action="delete_all"
                            )
                            deleted = True
                            break
                except Exception as e:
                    logger.debug(f"删除任务失败: {e}")
            
            # 如果 guid 方式失败，尝试用 task_id
            if not deleted and record.bitcomet_task_id:
                try:
                    await self.bitcomet.delete_task(
                        int(record.bitcomet_task_id),
                        action="delete_all"
                    )
                    deleted = True
                except Exception as e:
                    logger.debug(f"删除任务失败: {e}")
            
            if deleted:
                stats["bitcomet_deleted"] += 1
                logger.debug(f"删除任务: {content_id}")
            else:
                logger.debug(f"未找到任务: {content_id}")
                
        except Exception as e:
            logger.warning(f"删除任务失败 {content_id}: {e}")
    
    async def _retry_javsp_task(self, record: DownloadRecord, db: Session):
        """重试创建 JavSP 刮削任务"""
        content_id = record.content_id
        base_folder = record.save_folder or f"{settings.bitcomet_download_path}/{content_id}"
        actual_folder = find_actual_media_folder(base_folder, content_id=content_id)
        folder_path = actual_folder.replace(
            settings.bitcomet_download_path,
            settings.javsp_input_path
        )
        
        # 如果重试次数少且没有任务ID，创建新任务
        if record.javsp_retry_count < settings.max_retry_count and not record.javsp_task_id:
            logger.info(f"尝试创建 JavSP 刮削任务: {content_id}")
            try:
                javsp_task = await self.javsp.create_task(folder_path, profile="default")
                if javsp_task:
                    record.javsp_task_id = javsp_task.task_id
                    record.javsp_retry_count += 1
                    db.commit()
                    logger.info(f"成功创建 JavSP 任务: {javsp_task.task_id}")
            except Exception as e:
                logger.warning(f"创建 JavSP 任务失败: {e}")
                record.javsp_retry_count += 1
                db.commit()
        elif record.javsp_retry_count >= settings.max_retry_count:
            logger.warning(f"JavSP 任务重试次数已达上限: {content_id}")
            record.status = "javsp_error"
            db.commit()
