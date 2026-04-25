"""
Workflow 2: 状态监控 & JavSP 整理

监控 BitComet 下载状态，满足条件后自动提交 JavSP 刮削
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from app.services import BitCometClient, JavSPClient, FreshRSSClient
from app.services.javsp import find_actual_media_folder, get_safe_folder_path
from app.database import get_db_session, DownloadRecord
from app.config import settings
from app.logger import logger, log_workflow_start, log_workflow_end, log_task_completed, log_javsp_submitted


class MonitorWorkflow:
    """监控工作流"""
    
    # FreshRSS 标签常量
    TAG_COMPLETED = "下载完成"
    TAG_STARTED = "已开始下载"  # 需要移除的标签
    
    def __init__(self):
        self.bitcomet = BitCometClient()
        self.javsp = JavSPClient()
        self.freshrss = FreshRSSClient()
        
    async def __aenter__(self):
        await self.bitcomet.connect()
        await self.javsp.connect()
        await self.freshrss.connect()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.bitcomet.close()
        await self.javsp.close()
        await self.freshrss.close()
    
    async def run(self) -> dict:
        """
        执行完整工作流
        
        Returns:
            执行统计信息
        """
        stats = {
            "checked": 0,
            "completed": 0,
            "javsp_submitted": 0,
            "javsp_failed": 0,
            "not_found": 0,
            "error": 0,
            "timeout": 0,  # 新增：超时任务数
        }
        
        log_workflow_start("W2-状态监控")
        
        db = get_db_session()
        try:
            # 0. 首先检查并处理超时任务（在获取任务列表前）
            await self._check_timeout_records(db, stats)
            
            # 1. 查询 status='running' 的记录（不包括 timeout 状态）
            running_records = db.query(DownloadRecord).filter(
                DownloadRecord.status == "running"
            ).all()
            
            if not running_records:
                logger.info("无运行中任务")
                log_workflow_end("W2-状态监控", stats)
                return stats
            
            logger.info(f"📊 监控: {len(running_records)}个任务")
            
            # 2. BitComet 登录并获取任务列表
            await self.bitcomet.login()
            bitcomet_tasks = await self.bitcomet.get_task_list()
            
            # 构建 task_guid -> task 映射
            task_map = {}
            for task in bitcomet_tasks:
                if task.task_guid:
                    task_map[task.task_guid] = task
                task_map[f"id:{task.task_id}"] = task
            
            logger.debug(f"BitComet任务: {len(bitcomet_tasks)}个")
            
            # 3. 循环处理每条记录
            for record in running_records:
                await self._process_record(record, task_map, db, stats)
                
        finally:
            db.close()
            
        log_workflow_end("W2-状态监控", stats)
        logger.info("=" * 50)
        
        return stats
    
    async def _check_timeout_records(self, db: Session, stats: dict):
        """
        检查并处理超时任务
        
        条件：
        - status == "running"
        - created_at 超过 download_timeout_hours（默认48小时）
        - 且未完成
        
        处理：
        - 停止 BitComet 任务
        - status 改为 "timeout"
        - 记录 timeout_at 时间
        """
        timeout_threshold = datetime.utcnow() - timedelta(hours=settings.download_timeout_hours)
        
        # 查询超时的任务
        timeout_records = db.query(DownloadRecord).filter(
            DownloadRecord.status == "running",
            DownloadRecord.created_at < timeout_threshold
        ).all()
        
        if not timeout_records:
            return
        
        logger.info(f"⏰ 发现 {len(timeout_records)} 个超时任务(>{settings.download_timeout_hours}小时)")
        
        # 登录 BitComet
        try:
            await self.bitcomet.login()
        except Exception as e:
            logger.error(f"BitComet 登录失败，无法停止超时任务: {e}")
            return
        
        for record in timeout_records:
            content_id = record.content_id
            try:
                # 停止 BitComet 任务
                if record.bitcomet_task_id:
                    try:
                        await self.bitcomet.stop_task(int(record.bitcomet_task_id))
                        logger.debug(f"已停止 BitComet 任务: {content_id}")
                    except Exception as e:
                        logger.debug(f"停止任务失败（可能已停止）: {content_id} - {e}")
                
                # 更新状态为 timeout
                record.status = "timeout"
                record.timeout_at = datetime.utcnow()
                db.commit()
                
                stats["timeout"] += 1
                logger.info(f"⏹️ 任务超时: {content_id}")
                
            except Exception as e:
                logger.error(f"处理超时任务失败 {content_id}: {e}")
                db.rollback()
                stats["error"] += 1
    
    async def _process_record(
        self, 
        record: DownloadRecord, 
        task_map: Dict[str, Any], 
        db: Session, 
        stats: dict
    ):
        """处理单条记录 - 使用 task_guid 匹配（更稳定）"""
        stats["checked"] += 1
        
        # 优先使用 task_guid 匹配，其次是 task_id
        task = None
        if record.bitcomet_task_guid:
            task = task_map.get(record.bitcomet_task_guid)
        
        # 如果 guid 没匹配到，尝试用 task_id
        if not task and record.bitcomet_task_id:
            task_id = int(record.bitcomet_task_id)
            task = task_map.get(f"id:{task_id}")
        
        # 检查任务是否存在
        if not task:
            if record.bitcomet_task_id:
                task = await self.bitcomet.get_task_summary(int(record.bitcomet_task_id))
            
            if not task:
                logger.warning(f"⚠️ 任务丢失: {record.content_id}")
                record.status = "error"
                db.commit()
                stats["not_found"] += 1
                return
        
        # ========== 更新任务详情到数据库 ==========
        logger.debug(f"{record.content_id}: {task.progress_percent:.0f}% | 分享率{task.share_ratio}")
        
        # 更新 BitComet 任务信息
        record.bitcomet_task_id = str(task.task_id)
        record.bitcomet_task_guid = task.task_guid
        record.task_type = task.task_type
        record.download_rate = task.download_rate
        record.upload_rate = task.upload_rate
        record.share_ratio = float(task.share_ratio) if task.share_ratio else None
        record.health = task.health
        record.file_count = task.file_count
        record.error_code = task.error_code
        record.error_message = task.error_message
        record.progress = task.permillage  # 保存进度 (千分比)
        
        # 计算已下载大小
        record.file_size = task.total_size
        
        # 检查是否已完成下载
        if not task.is_completed:
            # 未完成，更新数据库并跳过
            db.commit()
            logger.debug(f"⏳ 任务 {record.content_id} 未完成，继续监控")
            return
        
        # 下载完成，检查提交条件
        should_submit_javsp = self._check_submit_condition(record, task)
        
        if should_submit_javsp:
            await self._submit_to_javsp(record, task, db, stats)
        else:
            logger.debug(f"任务 {record.content_id} 不满足 JavSP 提交条件")
    
    def _check_submit_condition(self, record: DownloadRecord, task) -> bool:
        """
        检查是否满足提交 JavSP 的条件
        
        条件:
        1. permillage == 1000 AND share_ratio > settings.javsp_submit_share_ratio
        2. OR permillage == 1000 AND created_at > settings.javsp_submit_hours
        """
        content_id = record.content_id
        
        # 条件 1: 分享率超过阈值
        share_ratio_threshold = settings.javsp_submit_share_ratio
        if task.share_ratio and task.share_ratio > share_ratio_threshold:
            logger.info(f"✓ {content_id}: 分享率{task.share_ratio:.1f}>{share_ratio_threshold}")
            return True
        
        # 条件 2: 创建时间超过阈值
        hours_threshold = settings.javsp_submit_hours
        hours_diff = (datetime.utcnow() - record.created_at).total_seconds() / 3600
        if hours_diff > hours_threshold:
            logger.info(f"✓ {content_id}: 已创建{hours_diff:.1f}小时>{hours_threshold}小时")
            return True
        
        logger.debug(f"⏳ {content_id}: 分享率{task.share_ratio:.1f}(需>{share_ratio_threshold}), 已创建{hours_diff:.1f}小时(需>{hours_threshold}小时)")
        return False
    
    async def _submit_to_javsp(
        self, 
        record: DownloadRecord, 
        task, 
        db: Session, 
        stats: dict
    ):
        """提交到 JavSP 刮削"""
        content_id = record.content_id
        logger.info(f"准备提交 JavSP 刮削: {content_id}")
        
        try:
            # 更新状态为 completed
            record.status = "completed"
            
            # 更新 BitComet 任务信息（保存 guid 和其他详情）
            if task:
                record.bitcomet_task_guid = task.task_guid
                record.task_type = task.task_type
                record.file_count = task.file_count
                record.health = task.health
            
            db.commit()
            stats["completed"] += 1
            
            # 给 FreshRSS 条目打"下载完成"标签，并移除"已开始下载"标签
            if record.freshrss_item_id:
                try:
                    await self.freshrss.login()
                    await self.freshrss.add_tag(record.freshrss_item_id, self.TAG_COMPLETED)
                    await self.freshrss.remove_tag(record.freshrss_item_id, self.TAG_STARTED)
                except Exception as e:
                    logger.debug(f"标签操作异常: {e}")
            
            log_task_completed(content_id)
            
            # 停止 BitComet 任务（在提交 JavSP 前）
            if task and record.bitcomet_task_id:
                try:
                    await self.bitcomet.stop_task(int(record.bitcomet_task_id))
                except Exception as e:
                    logger.debug(f"停止任务失败: {e}")
            
            # 登录 JavSP
            await self.javsp.login()
            
            # 动态探测实际媒体目录
            base_folder = record.save_folder or f"{settings.bitcomet_download_path}/{content_id}"
            # 使用 task_name 辅助匹配，提高精确度（防止 fallback 到其他任务的文件夹）
            task_name = task.task_name if task else ""
            actual_folder = find_actual_media_folder(base_folder, content_id=content_id, task_name=task_name)
            
            # 如果返回的是 base_path 且没有直接视频文件，说明真的找不到文件夹
            if actual_folder == base_folder:
                import os
                has_video = False
                video_exts = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.ts', '.m2ts'}
                try:
                    for f in os.listdir(base_folder):
                        if os.path.isfile(os.path.join(base_folder, f)) and os.path.splitext(f)[1].lower() in video_exts:
                            has_video = True
                            break
                except Exception:
                    pass
                if not has_video:
                    raise Exception(f"未找到任务文件夹: {content_id} (task_name={task_name})")
            
            # 处理长文件夹名：创建短路径软链接
            safe_folder, symlink_created = get_safe_folder_path(actual_folder, content_id)
            
            # 路径转换
            input_dir = safe_folder.replace(
                settings.bitcomet_download_path,
                settings.javsp_input_path
            )
            
            record.file_path = input_dir
            db.commit()
            
            # 检查文件夹内容
            scan_result = await self.javsp.scan_folder(input_dir)
            file_count = scan_result.get("count", 0)
            
            if file_count == 0:
                raise Exception(f"文件夹为空: {content_id}")
            
            # 提交刮削任务
            javsp_task = await self.javsp.create_task(input_dir, profile="default")
            
            # 清理软链接（如果创建了）
            if symlink_created:
                try:
                    import os
                    link_path = os.path.join("/tmp/javsp_links", content_id)
                    if os.path.islink(link_path):
                        os.unlink(link_path)
                        logger.debug(f"清理软链接: {link_path}")
                except Exception:
                    pass
            
            if javsp_task:
                record.javsp_task_id = javsp_task.task_id
                db.commit()
                log_javsp_submitted(content_id)
                stats["javsp_submitted"] += 1
            else:
                raise Exception("JavSP 返回空任务")
                
        except Exception as e:
            logger.error(f"✗ {content_id}: {str(e)[:50]}")
            
            record.javsp_retry_count += 1
            
            if record.javsp_retry_count >= settings.max_retry_count:
                record.status = "javsp_error"
                logger.warning(f"⚠️ {content_id}: JavSP提交失败{settings.max_retry_count}次")
                
            db.commit()
            stats["javsp_failed"] += 1
